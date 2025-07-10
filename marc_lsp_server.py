#!/usr/bin/env python3
"""
MARC LSP Server

Language Server Protocol implementation for MARC MRK files.
Provides hover documentation, completion, and validation.
"""

import logging
import re
from typing import List, Optional, Union

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from mrk_parser import MrkParser, FieldType
from marc_adapter import marc_adapter
from marc_fixed_fields import marc_fixed_fields
from marc_lookup import marc_lookup


class MarcLspServer(LanguageServer):
    """LSP Server for MARC MRK files."""
    
    def __init__(self):
        super().__init__("marc-lsp-server", "v0.1.0")
        self.parser = MrkParser()
        

# Create server instance
server = MarcLspServer()



@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(params: lsp.HoverParams) -> Optional[lsp.Hover]:
    """Provide hover documentation for MARC tags and subfields."""
    document = server.workspace.get_text_document(params.text_document.uri)
    content = document.source
    lines = content.split('\n')
    
    line_idx = params.position.line
    char_idx = params.position.character
    
    if line_idx >= len(lines):
        return None
        
    line = lines[line_idx]
    if not line.strip() or not line.startswith('='):
        return None
    
    # Parse the line to get field information
    field = server.parser.parse_line(line, line_idx + 1)
    if not field:
        return None
    
    hover_result = get_hover_info_with_range(line, field, char_idx, line_idx)
    if not hover_result:
        return None
    
    hover_info, hover_range = hover_result
    
    # Some LSP clients don't support hover ranges well, so make it optional
    hover_response = lsp.Hover(
        contents=lsp.MarkupContent(
            kind=lsp.MarkupKind.Markdown,
            value=hover_info
        )
    )
    
    # Only add range if it's meaningful (not the entire line)
    if (hover_range.end.character - hover_range.start.character) < len(line):
        hover_response.range = hover_range
    
    return hover_response


def get_hover_info_with_range(line: str, field, char_idx: int, line_idx: int) -> Optional[tuple]:
    """Generate hover information and range for a specific position in a MARC line."""
    
    # Check if this is a fixed field and hovering over content
    if marc_fixed_fields.is_fixed_field(field.tag):
        fixed_result = get_fixed_field_hover_info_with_range(line, field, char_idx, line_idx)
        if fixed_result:
            return fixed_result
    
    # Check if hovering over indicators to get precise range
    if field.field_type == FieldType.DATA:
        indicator_result = get_indicator_hover_info_with_range(line, field, char_idx, line_idx)
        if indicator_result:
            return indicator_result
    
    # Check if hovering over subfield content to get precise range
    if field.field_type == FieldType.DATA and field.subfields:
        subfield_result = get_subfield_hover_info_with_range(line, field, char_idx, line_idx)
        if subfield_result:
            return subfield_result
    
    # For other cases, use the original logic with default range
    hover_info = get_hover_info(line, field, char_idx)
    if hover_info:
        # Default range - highlight entire line
        default_range = lsp.Range(
            start=lsp.Position(line=line_idx, character=0),
            end=lsp.Position(line=line_idx, character=len(line))
        )
        return hover_info, default_range
    
    return None


def get_indicator_hover_info_with_range(line: str, field, char_idx: int, line_idx: int) -> Optional[tuple]:
    """Get hover information and range for indicators."""
    
    # Match any characters in indicator positions after =XXX and space(s)
    # Typically format is =XXX  II where there are 2 spaces before indicators
    ind_match = re.search(r'=(\d{3})\s+(.)(.)(?=\$)', line)
    if ind_match:
        ind1_pos = ind_match.start(2)  # Position of first indicator
        ind2_pos = ind_match.start(3)  # Position of second indicator
        
        # Try dynamic lookup first
        tag_def = marc_adapter.get_tag_definition(field.tag)
        if not tag_def:
            tag_def = marc_lookup.get_tag_info(field.tag)
        
        if char_idx == ind1_pos:  # First indicator
            if tag_def and tag_def.indicators and "1" in tag_def.indicators:
                ind_value = field.indicator1 or " "
                ind_desc = tag_def.indicators["1"].get(ind_value, "Unknown value")
                info = f"**Indicator 1:** `{ind_value}`\n\n{ind_desc}"
                
                # Add LOC URL
                loc_url = marc_lookup._get_tag_url(field.tag)
                if loc_url:
                    info += f"\n\n[View full documentation on Library of Congress]({loc_url})"
            else:
                info = f"**Indicator 1:** `{field.indicator1 or ' '}`"
            
            # Create range for just the single indicator character
            hover_range = lsp.Range(
                start=lsp.Position(line=line_idx, character=ind1_pos),
                end=lsp.Position(line=line_idx, character=ind1_pos + 1)
            )
            
            return info, hover_range
                
        elif char_idx == ind2_pos:  # Second indicator
            if tag_def and tag_def.indicators and "2" in tag_def.indicators:
                ind_value = field.indicator2 or " "
                ind_desc = tag_def.indicators["2"].get(ind_value, "Unknown value")
                info = f"**Indicator 2:** `{ind_value}`\n\n{ind_desc}"
                
                # Add LOC URL
                loc_url = marc_lookup._get_tag_url(field.tag)
                if loc_url:
                    info += f"\n\n[View full documentation on Library of Congress]({loc_url})"
            else:
                info = f"**Indicator 2:** `{field.indicator2 or ' '}`"
            
            # Create range for just the single indicator character
            hover_range = lsp.Range(
                start=lsp.Position(line=line_idx, character=ind2_pos),
                end=lsp.Position(line=line_idx, character=ind2_pos + 1)
            )
            
            return info, hover_range
    
    return None


def get_subfield_hover_info_with_range(line: str, field, char_idx: int, line_idx: int) -> Optional[tuple]:
    """Get hover information and range for subfields."""
    
    # Build positions by walking through subfields sequentially
    current_pos = 0
    for subfield in field.subfields:
        # Find the next occurrence of this subfield code starting from current_pos
        subfield_pattern = f'\\${re.escape(subfield.code)}'
        match = re.search(subfield_pattern, line[current_pos:])
        if match:
            # Adjust position to be relative to the full line
            start_pos = current_pos + match.start()
            content_start = current_pos + match.end()
            content_end = content_start + len(subfield.content)
            
            # Move current_pos past this subfield for next search
            current_pos = content_end
            
            # Check if cursor is within this subfield (including the $code part)
            if start_pos <= char_idx <= content_end:
                # Get subfield definition - try local adapter first
                subfield_def = marc_adapter.get_subfield_definition(field.tag, subfield.code)
                
                if subfield_def:
                    info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                    info += f"{subfield_def.description}\n\n"
                    if subfield_def.repeatable:
                        info += "*Repeatable subfield*\n\n"
                    info += f"**Content:** {subfield.content}\n\n"
                    
                    # Add LOC URL
                    loc_url = marc_lookup._get_tag_url(field.tag)
                    if loc_url:
                        info += f"[View full documentation on Library of Congress]({loc_url})"
                    
                    # Create range for the entire subfield (from $code to end of content)
                    hover_range = lsp.Range(
                        start=lsp.Position(line=line_idx, character=start_pos),
                        end=lsp.Position(line=line_idx, character=content_end)
                    )
                    
                    return info, hover_range
                else:
                    # Try dynamic lookup
                    tag_def = marc_lookup.get_tag_info(field.tag)
                    if tag_def and tag_def.subfields.get(subfield.code):
                        subfield_def = tag_def.subfields[subfield.code]
                        info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                        info += f"{subfield_def.description}\n\n"
                        if subfield_def.repeatable:
                            info += "*Repeatable subfield*\n\n"
                        info += f"**Content:** {subfield.content}\n\n"
                        
                        # Add LOC URL
                        loc_url = marc_lookup._get_tag_url(field.tag)
                        if loc_url:
                            info += f"[View full documentation on Library of Congress]({loc_url})"
                        
                        # Create range for the entire subfield (from $code to end of content)
                        hover_range = lsp.Range(
                            start=lsp.Position(line=line_idx, character=start_pos),
                            end=lsp.Position(line=line_idx, character=content_end)
                        )
                        
                        return info, hover_range
                    else:
                        # Unknown subfield
                        info = f"**${subfield.code}** - Unknown subfield for tag {field.tag}"
                        hover_range = lsp.Range(
                            start=lsp.Position(line=line_idx, character=start_pos),
                            end=lsp.Position(line=line_idx, character=content_end)
                        )
                        return info, hover_range
    
    return None


def get_hover_info(line: str, field, char_idx: int) -> Optional[str]:
    """Generate hover information for a specific position in a MARC line."""
    
    # Check if this is a fixed field and hovering over content
    if marc_fixed_fields.is_fixed_field(field.tag):
        fixed_info = get_fixed_field_hover_info(line, field, char_idx)
        if fixed_info:
            return fixed_info
    
    # Check if hovering over tag
    if 0 <= char_idx <= 4:  # =XXX position
        # Try local adapter first for immediate response
        tag_def = marc_adapter.get_tag_definition(field.tag)
        if tag_def:
            info = f"**{tag_def.tag} - {tag_def.name}**\n\n"
            info += f"{tag_def.description}\n\n"
            
            if tag_def.repeatable:
                info += "*Repeatable field*\n\n"
            
            # Add indicator information for data fields
            if field.field_type == FieldType.DATA and tag_def.indicators:
                info += "**Indicators:**\n\n"
                for ind_num, ind_values in tag_def.indicators.items():
                    info += f"Indicator {ind_num}:\n"
                    for value, description in ind_values.items():
                        info += f"- `{value}`: {description}\n"
                    info += "\n"
            
            # Add subfield information
            if tag_def.subfields:
                info += "**Subfields:**\n\n"
                for code, subfield_def in sorted(tag_def.subfields.items()):
                    repeatable = " (R)" if subfield_def.repeatable else ""
                    info += f"- `${code}`: {subfield_def.name}{repeatable}\n"
                    if subfield_def.description != subfield_def.name:
                        info += f"  {subfield_def.description}\n"
            
            # Add LOC URL
            loc_url = marc_lookup._get_tag_url(field.tag)
            if loc_url:
                info += f"\n[View full documentation on Library of Congress]({loc_url})"
            
            return info
        else:
            # Try dynamic lookup
            tag_def = marc_lookup.get_tag_info(field.tag)
            if tag_def:
                info = f"**{tag_def.tag} - {tag_def.name}**\n\n"
                info += f"{tag_def.description}\n\n"
                
                if tag_def.repeatable:
                    info += "*Repeatable field*\n\n"
                
                # Add indicator information for data fields
                if field.field_type == FieldType.DATA and tag_def.indicators:
                    info += "**Indicators:**\n\n"
                    for ind_num, ind_values in tag_def.indicators.items():
                        info += f"Indicator {ind_num}:\n"
                        for value, description in ind_values.items():
                            info += f"- `{value}`: {description}\n"
                        info += "\n"
                
                # Add subfield information
                if tag_def.subfields:
                    info += "**Subfields:**\n\n"
                    for code, subfield_def in sorted(tag_def.subfields.items()):
                        repeatable = " (R)" if subfield_def.repeatable else ""
                        info += f"- `${code}`: {subfield_def.name}{repeatable}\n"
                        if subfield_def.description != subfield_def.name:
                            info += f"  {subfield_def.description}\n"
                
                # Add LOC URL
                loc_url = marc_lookup._get_tag_url(field.tag)
                if loc_url:
                    info += f"\n[View full documentation on Library of Congress]({loc_url})"
                
                return info
            else:
                return f"**{field.tag}** - Unknown MARC tag"
    
    # Check if hovering over subfield
    if field.field_type == FieldType.DATA and field.subfields:
        for subfield in field.subfields:
            # Find subfield position in line  
            subfield_pattern = f'\\${re.escape(subfield.code)}'
            for match in re.finditer(subfield_pattern, line):
                start_pos = match.start()
                end_pos = match.end() + len(subfield.content)
                
                if start_pos <= char_idx <= end_pos:
                    # Get subfield definition - try local adapter first
                    subfield_def = marc_adapter.get_subfield_definition(field.tag, subfield.code)
                    if subfield_def:
                        info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                        info += f"{subfield_def.description}\n\n"
                        if subfield_def.repeatable:
                            info += "*Repeatable subfield*\n\n"
                        info += f"**Content:** {subfield.content}\n\n"
                        
                        # Add LOC URL
                        loc_url = marc_lookup._get_tag_url(field.tag)
                        if loc_url:
                            info += f"[View full documentation on Library of Congress]({loc_url})"
                        
                        return info
                    else:
                        # Try dynamic lookup
                        tag_def = marc_lookup.get_tag_info(field.tag)
                        if tag_def and tag_def.subfields.get(subfield.code):
                            subfield_def = tag_def.subfields[subfield.code]
                            info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                            info += f"{subfield_def.description}\n\n"
                            if subfield_def.repeatable:
                                info += "*Repeatable subfield*\n\n"
                            info += f"**Content:** {subfield.content}\n\n"
                            
                            # Add LOC URL
                            loc_url = marc_lookup._get_tag_url(field.tag)
                            if loc_url:
                                info += f"[View full documentation on Library of Congress]({loc_url})"
                            
                            return info
                        else:
                            return f"**${subfield.code}** - Unknown subfield for tag {field.tag}"
    
    # Check if hovering over indicators
    if field.field_type == FieldType.DATA:
        # Match any characters in indicator positions after =XXX and space(s)
        # Typically format is =XXX  II where there are 2 spaces before indicators
        ind_match = re.search(r'=(\d{3})\s+(.)(.)(?=\$)', line)
        if ind_match:
            ind1_pos = ind_match.start(2)  # Position of first indicator
            ind2_pos = ind_match.start(3)  # Position of second indicator
            
            # Try dynamic lookup first
            tag_def = marc_adapter.get_tag_definition(field.tag)
            if not tag_def:
                tag_def = marc_lookup.get_tag_info(field.tag)
            
            if ind1_pos <= char_idx <= ind1_pos:  # First indicator
                if tag_def and tag_def.indicators and "1" in tag_def.indicators:
                    ind_value = field.indicator1 or " "
                    ind_desc = tag_def.indicators["1"].get(ind_value, "Unknown value")
                    info = f"**Indicator 1:** `{ind_value}`\n\n{ind_desc}"
                    
                    # Add LOC URL
                    loc_url = marc_lookup._get_tag_url(field.tag)
                    if loc_url:
                        info += f"\n\n[View full documentation on Library of Congress]({loc_url})"
                    
                    return info
                else:
                    return f"**Indicator 1:** `{field.indicator1 or ' '}`"
                    
            elif ind2_pos <= char_idx <= ind2_pos:  # Second indicator
                if tag_def and tag_def.indicators and "2" in tag_def.indicators:
                    ind_value = field.indicator2 or " "
                    ind_desc = tag_def.indicators["2"].get(ind_value, "Unknown value")
                    info = f"**Indicator 2:** `{ind_value}`\n\n{ind_desc}"
                    
                    # Add LOC URL
                    loc_url = marc_lookup._get_tag_url(field.tag)
                    if loc_url:
                        info += f"\n\n[View full documentation on Library of Congress]({loc_url})"
                    
                    return info
                else:
                    return f"**Indicator 2:** `{field.indicator2 or ' '}`"
    
    return None


def get_fixed_field_hover_info_with_range(line: str, field, char_idx: int, line_idx: int) -> Optional[tuple]:
    """Get hover information and range for fixed fields like 008, 001, etc."""
    
    # Skip if hovering over the tag itself
    if char_idx <= 4:  # =XXX position
        return None
    
    # Find the content start position (after =XXX )
    tag_pattern = f'={field.tag}'
    tag_end = line.find(tag_pattern)
    if tag_end == -1:
        return None
    
    content_start = tag_end + len(tag_pattern)
    
    # Skip any spaces after the tag
    while content_start < len(line) and line[content_start] == ' ':
        content_start += 1
    
    # Calculate the character position within the field content
    if char_idx < content_start:
        return None
    
    field_char_pos = char_idx - content_start
    
    # Get position information
    pos_info = marc_fixed_fields.get_position_info(field.tag, field_char_pos)
    if not pos_info:
        # Default single character range
        hover_range = lsp.Range(
            start=lsp.Position(line=line_idx, character=char_idx),
            end=lsp.Position(line=line_idx, character=char_idx + 1)
        )
        return f"**{field.tag} position {field_char_pos}** - Character position in fixed field", hover_range
    
    # Calculate the range to highlight for this position
    if pos_info.end == -1:  # Variable length field
        field_content = line[content_start:].strip()
        range_start = content_start + pos_info.start
        range_end = content_start + len(field_content)
    else:  # Fixed length position
        range_start = content_start + pos_info.start
        range_end = content_start + pos_info.end + 1
    
    # Make sure we don't go beyond the line length
    range_end = min(range_end, len(line))
    range_start = min(range_start, len(line))
    
    hover_range = lsp.Range(
        start=lsp.Position(line=line_idx, character=range_start),
        end=lsp.Position(line=line_idx, character=range_end)
    )
    
    # Get the actual character value(s) at this position
    field_content = line[content_start:].strip()
    if pos_info.end == -1:  # Variable length
        char_value = field_content[pos_info.start:] if pos_info.start < len(field_content) else ''
    else:  # Fixed length
        char_value = field_content[pos_info.start:pos_info.end + 1] if pos_info.start < len(field_content) else ''
    
    # Build hover info
    if pos_info.end == -1:
        info = f"**{field.tag} - {pos_info.name}**\n\n"
        info += f"Position: {pos_info.start}+\n"
        info += f"Value: `{char_value}`\n\n"
    else:
        position_range = f"{pos_info.start}-{pos_info.end}" if pos_info.start != pos_info.end else str(pos_info.start)
        info = f"**{field.tag} - {pos_info.name}**\n\n"
        info += f"Position: {position_range}\n"
        info += f"Value: `{char_value}`\n\n"
    
    info += f"{pos_info.description}\n\n"
    
    # Add value-specific information if available
    if pos_info.values:
        # For multi-character fields, check if the value matches exactly
        if char_value in pos_info.values:
            info += f"**Current:** `{char_value}` = {pos_info.values[char_value]}\n\n"
        elif len(char_value) == 1 and char_value in pos_info.values:
            info += f"**Current:** `{char_value}` = {pos_info.values[char_value]}\n\n"
        else:
            info += f"**Current:** `{char_value}` (not recognized)\n\n"
        
        # Show possible values more compactly
        info += "**Other values:**\n"
        for value, desc in pos_info.values.items():
            if value != char_value:  # Don't repeat current value
                info += f"`{value}`: {desc}\n"
    
    # Add LOC URL
    loc_url = marc_lookup._get_tag_url(field.tag)
    if loc_url:
        info += f"\n[View full documentation on Library of Congress]({loc_url})"
    
    return info, hover_range


def get_fixed_field_hover_info(line: str, field, char_idx: int) -> Optional[str]:
    """Get hover information for fixed fields like 008, 001, etc."""
    
    # Skip if hovering over the tag itself
    if char_idx <= 4:  # =XXX position
        return None
    
    # Find the content start position (after =XXX )
    tag_pattern = f'={field.tag}'
    tag_end = line.find(tag_pattern)
    if tag_end == -1:
        return None
    
    content_start = tag_end + len(tag_pattern)
    
    # Skip any spaces after the tag
    while content_start < len(line) and line[content_start] == ' ':
        content_start += 1
    
    # Calculate the character position within the field content
    if char_idx < content_start:
        return None
    
    field_char_pos = char_idx - content_start
    
    # Get position information
    pos_info = marc_fixed_fields.get_position_info(field.tag, field_char_pos)
    if not pos_info:
        return f"**{field.tag} position {field_char_pos}** - Character position in fixed field"
    
    # Get the actual character value at this position
    field_content = line[content_start:].strip()
    char_value = field_content[field_char_pos] if field_char_pos < len(field_content) else ' '
    
    # Build hover info
    info = f"**{field.tag} - {pos_info.name}**\n\n"
    info += f"Position: {field_char_pos}\n"
    info += f"Value: `{char_value}`\n\n"
    info += f"{pos_info.description}\n\n"
    
    # Add value-specific information if available
    if pos_info.values:
        if char_value in pos_info.values:
            info += f"**Current:** `{char_value}` = {pos_info.values[char_value]}\n\n"
        else:
            info += f"**Current:** `{char_value}` (not recognized)\n\n"
        
        # Show possible values more compactly
        info += "**Other values:**\n"
        for value, desc in pos_info.values.items():
            if value != char_value:  # Don't repeat current value
                info += f"`{value}`: {desc}\n"
    
    # Add LOC URL
    loc_url = marc_lookup._get_tag_url(field.tag)
    if loc_url:
        info += f"\n[View full documentation on Library of Congress]({loc_url})"
    
    return info


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
async def did_open_text_document(params: lsp.DidOpenTextDocumentParams):
    """Handle document open events."""
    logging.info(f"Document opened: {params.text_document.uri}")


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
async def did_change_text_document(params: lsp.DidChangeTextDocumentParams):
    """Handle document change events."""
    document = server.workspace.get_text_document(params.text_document.uri)
    logging.info(f"Document changed: {params.text_document.uri}")
    
    # Validate MRK syntax and publish diagnostics
    diagnostics = validate_mrk_document(document)
    server.publish_diagnostics(document.uri, diagnostics)


def validate_mrk_document(document) -> List[lsp.Diagnostic]:
    """Validate MRK document and return diagnostics."""
    diagnostics = []
    content = document.source
    lines = content.split('\n')
    
    for line_idx, line in enumerate(lines):
        if not line.strip() or not line.startswith('='):
            continue
            
        field = server.parser.parse_line(line, line_idx + 1)
        if not field:
            # Invalid MARC line
            diagnostics.append(lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line_idx, character=0),
                    end=lsp.Position(line=line_idx, character=len(line))
                ),
                severity=lsp.DiagnosticSeverity.Error,
                source="marc-lsp",
                message="Invalid MARC line format"
            ))
            continue
            
        # Validate field
        field_errors = server.parser.validate_field(field)
        for error in field_errors:
            diagnostics.append(lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line_idx, character=0),
                    end=lsp.Position(line=line_idx, character=len(line))
                ),
                severity=lsp.DiagnosticSeverity.Warning,
                source="marc-lsp",
                message=error
            ))
    
    return diagnostics


def main():
    """Main entry point for the MARC LSP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    server.start_io()

if __name__ == "__main__":
    main()
