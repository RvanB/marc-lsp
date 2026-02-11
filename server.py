#!/usr/bin/env python3
"""
MARC LSP Server

Language Server Protocol implementation for MARC files.
Supports both MRK format (=245  10$aTitle) and line mode (245 10 $a Title).
Provides hover documentation, completion, and validation.
"""

import logging
import re
from typing import List, Optional, Union

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from parsers import MrkParser, LineParser, FieldType
from marc_definitions import MarcStaticData


def get_tag_url(tag: str) -> Optional[str]:
    """Generate Library of Congress URL for a MARC tag (for reference only)."""
    if not tag.isdigit() or len(tag) != 3:
        return None

    tag_num = int(tag)

    # Holdings record tags use holdings documentation
    if (tag_num >= 852 and tag_num <= 878) or tag_num >= 880:
        return f"https://www.loc.gov/marc/holdings/hd{tag}.html"
    else:
        # Bibliographic record tags use bibliographic documentation
        return f"https://www.loc.gov/marc/bibliographic/bd{tag}.html"


def detect_format(content: str) -> str:
    """Detect whether content is MRK format or line mode.

    Returns 'mrk' or 'line'.
    """
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('='):
            return 'mrk'
        # Non-empty, non-= line found; assume line mode
        return 'line'
    return 'mrk'  # default


class MarcLspServer(LanguageServer):
    """LSP Server for MARC files."""

    def __init__(self):
        super().__init__("marc-lsp-server", "v0.1.0")
        self.mrk_parser = MrkParser()
        self.line_parser = LineParser()
        # Keep self.parser for backward compat
        self.parser = self.mrk_parser

    def get_parser(self, fmt: str):
        """Return the appropriate parser for the detected format."""
        if fmt == 'line':
            return self.line_parser
        return self.mrk_parser


# Create server instance
server = MarcLspServer()

static_data = MarcStaticData()


def _is_marc_line(line: str, fmt: str) -> bool:
    """Check if a line looks like a MARC field line for the given format."""
    stripped = line.strip()
    if not stripped:
        return False
    if fmt == 'mrk':
        return stripped.startswith('=')
    else:
        # Line mode: starts with a digit (tag) or is a leader line
        return bool(re.match(r'^\d', stripped))


def _tag_end_char(fmt: str) -> int:
    """Return the character position after which the tag ends.

    MRK: =XXX -> tag spans chars 0-3, so tag region is 0..4
    Line: XXX  -> tag spans chars 0-2, so tag region is 0..2
    """
    return 4 if fmt == 'mrk' else 2


def _indicator_pattern(fmt: str) -> re.Pattern:
    """Return regex pattern to match indicators for the given format."""
    if fmt == 'mrk':
        # =XXX  II$a... (2 spaces typically between tag and indicators)
        return re.compile(r'=(\d{3})\s+(.)(.)(?=\$)')
    else:
        # XXX II $a... (1 space after tag, then ind1 ind2, then space before $)
        return re.compile(r'^(\d{3})\s(.)(.)(?:\s)')


def _find_content_start(line: str, field, fmt: str) -> int:
    """Find the character position where field content starts (after tag and spaces)."""
    if fmt == 'mrk':
        tag_pattern = f'={field.tag}'
    else:
        tag_pattern = field.tag

    tag_end = line.find(tag_pattern)
    if tag_end == -1:
        return -1

    content_start = tag_end + len(tag_pattern)

    # Skip any spaces after the tag
    while content_start < len(line) and line[content_start] == ' ':
        content_start += 1

    return content_start


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

    fmt = detect_format(content)
    parser = server.get_parser(fmt)

    line = lines[line_idx]
    if not _is_marc_line(line, fmt):
        return None

    # Parse the line to get field information
    field = parser.parse_line(line, line_idx + 1)
    if not field:
        return None

    hover_result = get_hover_info_with_range(line, field, char_idx, line_idx, fmt)
    if not hover_result:
        return None

    hover_info, hover_range = hover_result

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


def get_hover_info_with_range(line: str, field, char_idx: int, line_idx: int, fmt: str = 'mrk') -> Optional[tuple]:
    """Generate hover information and range for a specific position in a MARC line."""

    # Check if this is a fixed field and hovering over content
    if static_data.is_fixed_field(field.tag):
        fixed_result = get_fixed_field_hover_info_with_range(line, field, char_idx, line_idx, fmt)
        if fixed_result:
            return fixed_result

    # Check if hovering over indicators to get precise range
    if field.field_type == FieldType.DATA:
        indicator_result = get_indicator_hover_info_with_range(line, field, char_idx, line_idx, fmt)
        if indicator_result:
            return indicator_result

    # Check if hovering over subfield content to get precise range
    if field.field_type == FieldType.DATA and field.subfields:
        subfield_result = get_subfield_hover_info_with_range(line, field, char_idx, line_idx)
        if subfield_result:
            return subfield_result

    # For other cases, use the original logic with default range
    hover_info = get_hover_info(line, field, char_idx, fmt)
    if hover_info:
        # Default range - highlight entire line
        default_range = lsp.Range(
            start=lsp.Position(line=line_idx, character=0),
            end=lsp.Position(line=line_idx, character=len(line))
        )
        return hover_info, default_range

    return None


def get_indicator_hover_info_with_range(line: str, field, char_idx: int, line_idx: int, fmt: str = 'mrk') -> Optional[tuple]:
    """Get hover information and range for indicators."""

    pattern = _indicator_pattern(fmt)
    ind_match = pattern.search(line)
    if ind_match:
        ind1_pos = ind_match.start(2)  # Position of first indicator
        ind2_pos = ind_match.start(3)  # Position of second indicator

        # Get tag definition from static data
        tag_def = static_data.get_tag_definition(field.tag)

        if char_idx == ind1_pos:  # First indicator
            if tag_def and tag_def.indicators and "1" in tag_def.indicators:
                ind_value = field.indicator1 or " "
                ind_desc = tag_def.indicators["1"].get(ind_value, "Unknown value")
                info = f"**Indicator 1:** `{ind_value}`\n\n{ind_desc}"

                loc_url = get_tag_url(field.tag)
                if loc_url:
                    info += f"\n\n[View full documentation on Library of Congress]({loc_url})"
            else:
                info = f"**Indicator 1:** `{field.indicator1 or ' '}`"

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

                loc_url = get_tag_url(field.tag)
                if loc_url:
                    info += f"\n\n[View full documentation on Library of Congress]({loc_url})"
            else:
                info = f"**Indicator 2:** `{field.indicator2 or ' '}`"

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
                # Get subfield definition
                subfield_def = static_data.get_subfield_definition(field.tag, subfield.code)

                if subfield_def:
                    info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                    info += f"{subfield_def.description}\n\n"
                    if subfield_def.repeatable:
                        info += "*Repeatable subfield*\n\n"
                    info += f"**Content:** {subfield.content}\n\n"

                    loc_url = get_tag_url(field.tag)
                    if loc_url:
                        info += f"[View full documentation on Library of Congress]({loc_url})"

                    hover_range = lsp.Range(
                        start=lsp.Position(line=line_idx, character=start_pos),
                        end=lsp.Position(line=line_idx, character=content_end)
                    )

                    return info, hover_range
                else:
                    # Get tag definition from static data
                    tag_def = static_data.get_tag_definition(field.tag)
                    if tag_def and tag_def.subfields.get(subfield.code):
                        subfield_def = tag_def.subfields[subfield.code]
                        info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                        info += f"{subfield_def.description}\n\n"
                        if subfield_def.repeatable:
                            info += "*Repeatable subfield*\n\n"
                        info += f"**Content:** {subfield.content}\n\n"

                        loc_url = get_tag_url(field.tag)
                        if loc_url:
                            info += f"[View full documentation on Library of Congress]({loc_url})"

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


def get_hover_info(line: str, field, char_idx: int, fmt: str = 'mrk') -> Optional[str]:
    """Generate hover information for a specific position in a MARC line."""

    # Check if this is a fixed field and hovering over content
    if static_data.is_fixed_field(field.tag):
        fixed_info = get_fixed_field_hover_info(line, field, char_idx, fmt)
        if fixed_info:
            return fixed_info

    # Check if hovering over tag
    tag_end = _tag_end_char(fmt)
    if 0 <= char_idx <= tag_end:
        tag_def = static_data.get_tag_definition(field.tag)
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

            loc_url = get_tag_url(field.tag)
            if loc_url:
                info += f"\n[View full documentation on Library of Congress]({loc_url})"

            return info

    # Check if hovering over subfield
    if field.field_type == FieldType.DATA and field.subfields:
        for subfield in field.subfields:
            subfield_pattern = f'\\${re.escape(subfield.code)}'
            for match in re.finditer(subfield_pattern, line):
                start_pos = match.start()
                end_pos = match.end() + len(subfield.content)

                if start_pos <= char_idx <= end_pos:
                    subfield_def = static_data.get_subfield_definition(field.tag, subfield.code)
                    if subfield_def:
                        info = f"**${subfield_def.code} - {subfield_def.name}**\n\n"
                        info += f"{subfield_def.description}\n\n"
                        if subfield_def.repeatable:
                            info += "*Repeatable subfield*\n\n"
                        info += f"**Content:** {subfield.content}\n\n"

                        loc_url = get_tag_url(field.tag)
                        if loc_url:
                            info += f"[View full documentation on Library of Congress]({loc_url})"

                        return info
                    else:
                        return f"**${subfield.code}** - Unknown subfield for tag {field.tag}"

    # Check if hovering over indicators
    if field.field_type == FieldType.DATA:
        pattern = _indicator_pattern(fmt)
        ind_match = pattern.search(line)
        if ind_match:
            ind1_pos = ind_match.start(2)
            ind2_pos = ind_match.start(3)

            tag_def = static_data.get_tag_definition(field.tag)

            if char_idx == ind1_pos:
                if tag_def and tag_def.indicators and "1" in tag_def.indicators:
                    ind_value = field.indicator1 or " "
                    ind_desc = tag_def.indicators["1"].get(ind_value, "Unknown value")
                    info = f"**Indicator 1:** `{ind_value}`\n\n{ind_desc}"

                    loc_url = get_tag_url(field.tag)
                    if loc_url:
                        info += f"\n\n[View full documentation on Library of Congress]({loc_url})"

                    return info
                else:
                    return f"**Indicator 1:** `{field.indicator1 or ' '}`"

            elif char_idx == ind2_pos:
                if tag_def and tag_def.indicators and "2" in tag_def.indicators:
                    ind_value = field.indicator2 or " "
                    ind_desc = tag_def.indicators["2"].get(ind_value, "Unknown value")
                    info = f"**Indicator 2:** `{ind_value}`\n\n{ind_desc}"

                    loc_url = get_tag_url(field.tag)
                    if loc_url:
                        info += f"\n\n[View full documentation on Library of Congress]({loc_url})"

                    return info
                else:
                    return f"**Indicator 2:** `{field.indicator2 or ' '}`"

    return None


def get_fixed_field_hover_info_with_range(line: str, field, char_idx: int, line_idx: int, fmt: str = 'mrk') -> Optional[tuple]:
    """Get hover information and range for fixed fields like 008, 001, etc."""

    tag_end = _tag_end_char(fmt)

    # Skip if hovering over the tag itself
    if char_idx <= tag_end:
        return None

    content_start = _find_content_start(line, field, fmt)
    if content_start == -1:
        return None

    # Calculate the character position within the field content
    if char_idx < content_start:
        return None

    field_char_pos = char_idx - content_start

    # Get position information
    pos_info = static_data.get_position_info(field.tag, field_char_pos)
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
        if char_value in pos_info.values:
            info += f"**Current:** `{char_value}` = {pos_info.values[char_value]}\n\n"
        elif len(char_value) == 1 and char_value in pos_info.values:
            info += f"**Current:** `{char_value}` = {pos_info.values[char_value]}\n\n"
        else:
            info += f"**Current:** `{char_value}` (not recognized)\n\n"

        info += "**Other values:**\n"
        for value, desc in pos_info.values.items():
            if value != char_value:
                info += f"`{value}`: {desc}\n"

    loc_url = get_tag_url(field.tag)
    if loc_url:
        info += f"\n[View full documentation on Library of Congress]({loc_url})"

    return info, hover_range


def get_fixed_field_hover_info(line: str, field, char_idx: int, fmt: str = 'mrk') -> Optional[str]:
    """Get hover information for fixed fields like 008, 001, etc."""

    tag_end = _tag_end_char(fmt)

    # Skip if hovering over the tag itself
    if char_idx <= tag_end:
        return None

    content_start = _find_content_start(line, field, fmt)
    if content_start == -1:
        return None

    # Calculate the character position within the field content
    if char_idx < content_start:
        return None

    field_char_pos = char_idx - content_start

    # Get position information
    pos_info = static_data.get_position_info(field.tag, field_char_pos)
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

        info += "**Other values:**\n"
        for value, desc in pos_info.values.items():
            if value != char_value:
                info += f"`{value}`: {desc}\n"

    loc_url = get_tag_url(field.tag)
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

    # Validate syntax and publish diagnostics
    diagnostics = validate_document(document)
    server.publish_diagnostics(document.uri, diagnostics)


def validate_document(document) -> List[lsp.Diagnostic]:
    """Validate MARC document (MRK or line mode) and return diagnostics."""
    diagnostics = []
    content = document.source
    lines = content.split('\n')

    fmt = detect_format(content)
    parser = server.get_parser(fmt)

    for line_idx, line in enumerate(lines):
        if not _is_marc_line(line, fmt):
            continue

        field = parser.parse_line(line, line_idx + 1)
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
        field_errors = parser.validate_field(field)
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


# Keep old name as alias for backward compatibility
validate_mrk_document = validate_document


def main():
    """Main entry point for the MARC LSP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    server.start_io()

if __name__ == "__main__":
    main()
