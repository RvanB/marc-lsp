"""
MARC Line Mode Parser

Parser for MARC line mode format files.
Line mode is a human-readable representation of MARC records with a different
layout than MRK format.

Format:
- Leader: 00000pam  2200000 a 4500 (raw, no tag prefix)
- Control fields: 001 123456789
- Data fields: 245 04 $a Title $b subtitle
  - Pos 0-2: tag
  - Pos 3: space
  - Pos 4: indicator 1
  - Pos 5: indicator 2
  - Pos 6: space
  - Pos 7+: subfield data
"""

import re
from typing import List, Optional

from .mrk_parser import MarcField, MarcSubfield, MarcRecord, FieldType


class LineParser:
    """Parser for MARC line mode format files."""

    # Leader: 24-char string starting with digits, no tag prefix
    LEADER_PATTERN = re.compile(r'^(\d{5}.{19})$')
    # Control fields (001-009): TAG followed by space and content
    CONTROL_FIELD_PATTERN = re.compile(r'^(00[1-9])\s(.+)$')
    # Data fields: TAG IND1 IND2 space subfield_data
    DATA_FIELD_PATTERN = re.compile(r'^(\d{3})\s(.)(.)(\s.*)$')
    # Subfield pattern
    SUBFIELD_PATTERN = re.compile(r'\$([a-z0-9])([^$]*)')

    def __init__(self):
        self.current_record = None

    def parse_document(self, content: str) -> List[MarcRecord]:
        """Parse entire line mode document and return list of records."""
        records = []
        lines = content.split('\n')

        current_record = MarcRecord()

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            field = self.parse_line(line, line_num)
            if field:
                if field.field_type == FieldType.LEADER:
                    if current_record.leader or current_record.fields:
                        records.append(current_record)
                        current_record = MarcRecord()
                    current_record.leader = field
                else:
                    current_record.fields.append(field)

        if current_record.leader or current_record.fields:
            records.append(current_record)

        return records

    def parse_line(self, line: str, line_number: int = 0) -> Optional[MarcField]:
        """Parse a single line mode line and return a MarcField."""
        if not line.strip():
            return None

        # Try leader: raw 24-char string starting with digits
        leader_match = self.LEADER_PATTERN.match(line.strip())
        if leader_match:
            return MarcField(
                tag="LDR",
                field_type=FieldType.LEADER,
                content=leader_match.group(1),
                line_number=line_number,
                start_pos=0,
                end_pos=len(line)
            )

        # Try control field (001-009)
        control_match = self.CONTROL_FIELD_PATTERN.match(line)
        if control_match:
            return MarcField(
                tag=control_match.group(1),
                field_type=FieldType.CONTROL,
                content=control_match.group(2),
                line_number=line_number,
                start_pos=0,
                end_pos=len(line)
            )

        # Try data field
        data_match = self.DATA_FIELD_PATTERN.match(line)
        if data_match:
            tag = data_match.group(1)
            ind1 = data_match.group(2)
            ind2 = data_match.group(3)
            subfield_data = data_match.group(4)

            if ind1 == ' ':
                ind1 = ' '
            if ind2 == ' ':
                ind2 = ' '

            subfields = self.parse_subfields(subfield_data)

            return MarcField(
                tag=tag,
                field_type=FieldType.DATA,
                indicator1=ind1,
                indicator2=ind2,
                subfields=subfields,
                line_number=line_number,
                start_pos=0,
                end_pos=len(line)
            )

        return None

    def parse_subfields(self, subfield_data: str) -> List[MarcSubfield]:
        """Parse subfield data and return list of subfields."""
        subfields = []

        for match in self.SUBFIELD_PATTERN.finditer(subfield_data):
            code = match.group(1)
            content = match.group(2).rstrip()
            start_pos = match.start()
            end_pos = match.end()

            subfields.append(MarcSubfield(
                code=code,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos
            ))

        return subfields

    def validate_field(self, field: MarcField) -> List[str]:
        """Validate a MARC field and return list of error messages."""
        errors = []

        if field.field_type == FieldType.DATA:
            if field.indicator1 and len(field.indicator1) != 1:
                errors.append(f"First indicator must be single character for field {field.tag}")
            if field.indicator2 and len(field.indicator2) != 1:
                errors.append(f"Second indicator must be single character for field {field.tag}")

            if field.subfields:
                for subfield in field.subfields:
                    if not re.match(r'^[a-z0-9]$', subfield.code):
                        errors.append(f"Invalid subfield code '{subfield.code}' in field {field.tag}")

        return errors
