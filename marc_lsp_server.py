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
from pygls.cli import start_server
from pygls.lsp.server import LanguageServer

from mrk_parser import MrkParser, FieldType
from marc_tags import marc_tag_db


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
    
    hover_info = get_hover_info(line, field, char_idx)
    if not hover_info:
        return None
    
    return lsp.Hover(
        contents=lsp.MarkupContent(
            kind=lsp.MarkupKind.Markdown,
            value=hover_info
        ),
        range=lsp.Range(
            start=lsp.Position(line=line_idx, character=0),
            end=lsp.Position(line=line_idx, character=len(line))
        )
    )


def get_hover_info(line: str, field, char_idx: int) -> Optional[str]:
    """Generate hover information for a specific position in a MARC line."""
    
    # Check if hovering over tag
    if 0 <= char_idx <= 4:  # =XXX position
        tag_def = marc_tag_db.get_tag_definition(field.tag)
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
                    # Get subfield definition
                    subfield_def = marc_tag_db.get_subfield_definition(field.tag, subfield.code)
                    if subfield_def:
                        info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                        info += f"{subfield_def.description}\n\n"
                        if subfield_def.repeatable:
                            info += "*Repeatable subfield*\n\n"
                        info += f"**Content:** {subfield.content}"
                        return info
                    else:
                        return f"**${subfield.code}** - Unknown subfield for tag {field.tag}"
    
    # Check if hovering over indicators
    if field.field_type == FieldType.DATA:
        ind_match = re.search(r'=\d{3}\s+([0-9\s])([0-9\s])', line)
        if ind_match:
            ind1_pos = ind_match.start(1)
            ind2_pos = ind_match.start(2)
            
            tag_def = marc_tag_db.get_tag_definition(field.tag)
            
            if ind1_pos <= char_idx <= ind1_pos:  # First indicator
                if tag_def and tag_def.indicators and "1" in tag_def.indicators:
                    ind_value = field.indicator1 or " "
                    ind_desc = tag_def.indicators["1"].get(ind_value, "Unknown value")
                    return f"**Indicator 1:** `{ind_value}`\n\n{ind_desc}"
                else:
                    return f"**Indicator 1:** `{field.indicator1 or ' '}`"
                    
            elif ind2_pos <= char_idx <= ind2_pos:  # Second indicator
                if tag_def and tag_def.indicators and "2" in tag_def.indicators:
                    ind_value = field.indicator2 or " "
                    ind_desc = tag_def.indicators["2"].get(ind_value, "Unknown value")
                    return f"**Indicator 2:** `{ind_value}`\n\n{ind_desc}"
                else:
                    return f"**Indicator 2:** `{field.indicator2 or ' '}`"
    
    return None


@server.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(
        trigger_characters=["=", "$"],
        all_commit_characters=[" ", "\n", "\t"]
    )
)
def completion(params: lsp.CompletionParams) -> lsp.CompletionList:
    """Provide completion suggestions for MARC tags and subfields."""
    document = server.workspace.get_text_document(params.text_document.uri)
    content = document.source
    lines = content.split('\n')
    
    line_idx = params.position.line
    char_idx = params.position.character
    
    if line_idx >= len(lines):
        return lsp.CompletionList(is_incomplete=False, items=[])
    
    line = lines[line_idx]
    line_prefix = line[:char_idx]
    
    completion_items = []
    
    # Check if we're completing a MARC tag (after =)
    if line_prefix.endswith('=') or re.search(r'=\d{0,2}$', line_prefix):
        completion_items = get_tag_completions(line_prefix)
    
    # Check if we're completing a subfield (after $)
    elif '$' in line_prefix:
        # Find the current field tag
        tag_match = re.search(r'=(\d{3})', line)
        if tag_match:
            tag = tag_match.group(1)
            completion_items = get_subfield_completions(tag, line_prefix)
    
    return lsp.CompletionList(is_incomplete=False, items=completion_items)


def get_tag_completions(line_prefix: str) -> List[lsp.CompletionItem]:
    """Get completion items for MARC tags."""
    # Extract partial tag from line prefix
    tag_match = re.search(r'=(\d*)$', line_prefix)
    partial_tag = tag_match.group(1) if tag_match else ""
    
    completions = []
    all_tags = marc_tag_db.get_all_tags()
    
    for tag in sorted(all_tags):
        # Skip non-numeric tags for now (like LDR)
        if not tag.isdigit():
            continue
            
        if tag.startswith(partial_tag):
            tag_def = marc_tag_db.get_tag_definition(tag)
            if tag_def:
                completion_item = lsp.CompletionItem(
                    label=f"={tag}",
                    kind=lsp.CompletionItemKind.Class,
                    detail=tag_def.name,
                    documentation=lsp.MarkupContent(
                        kind=lsp.MarkupKind.Markdown,
                        value=f"**{tag_def.name}**\n\n{tag_def.description}"
                    ),
                    insert_text=tag,
                    filter_text=tag
                )
                
                # Add snippet with indicators for data fields
                if tag >= "010" and tag_def.indicators:
                    completion_item.insert_text = f"{tag}  ${{1: }}${{2: }}${{3:$$a}}"
                    completion_item.insert_text_format = lsp.InsertTextFormat.Snippet
                
                completions.append(completion_item)
    
    return completions


def get_subfield_completions(tag: str, line_prefix: str) -> List[lsp.CompletionItem]:
    """Get completion items for subfields within a specific tag."""
    # Extract partial subfield from line prefix
    subfield_match = re.search(r'\$([a-z0-9]*)$', line_prefix)
    partial_subfield = subfield_match.group(1) if subfield_match else ""
    
    completions = []
    subfield_codes = marc_tag_db.get_subfields_for_tag(tag)
    
    for code in sorted(subfield_codes):
        if code.startswith(partial_subfield):
            subfield_def = marc_tag_db.get_subfield_definition(tag, code)
            if subfield_def:
                completion_item = lsp.CompletionItem(
                    label=f"${code}",
                    kind=lsp.CompletionItemKind.Property,
                    detail=subfield_def.name,
                    documentation=lsp.MarkupContent(
                        kind=lsp.MarkupKind.Markdown,
                        value=f"**${code} - {subfield_def.name}**\n\n{subfield_def.description}"
                    ),
                    insert_text=code,
                    filter_text=code
                )
                
                # Mark as repeatable if applicable
                if subfield_def.repeatable:
                    completion_item.detail += " (Repeatable)"
                
                completions.append(completion_item)
    
    return completions


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


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    start_server(server)