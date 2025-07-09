"""
MRK Format Parser

Parser for MARC MRK (Machine-Readable Cataloging) files.
MRK is a human-readable representation of MARC binary files.

Format:
- Leader: =LDR  00000pam  2200000 a 4500
- Control fields: =001  123456789
- Data fields: =245  10$aTitle$bsubtitle$h[electronic resource]/$cby Author.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum


class FieldType(Enum):
    """Types of MARC fields."""
    LEADER = "leader"
    CONTROL = "control"
    DATA = "data"


@dataclass
class MarcSubfield:
    """Represents a MARC subfield."""
    code: str
    content: str
    start_pos: int
    end_pos: int


@dataclass
class MarcField:
    """Represents a MARC field."""
    tag: str
    field_type: FieldType
    indicator1: Optional[str] = None
    indicator2: Optional[str] = None
    content: Optional[str] = None  # For control fields
    subfields: Optional[List[MarcSubfield]] = None  # For data fields
    line_number: int = 0
    start_pos: int = 0
    end_pos: int = 0


@dataclass 
class MarcRecord:
    """Represents a complete MARC record."""
    leader: Optional[MarcField] = None
    fields: List[MarcField] = None
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []


class MrkParser:
    """Parser for MRK format files."""
    
    # Regular expressions for parsing
    FIELD_TAG_PATTERN = re.compile(r'^=([A-Z0-9]{3})\s+')
    LEADER_PATTERN = re.compile(r'^=LDR\s+(.+)$')
    CONTROL_FIELD_PATTERN = re.compile(r'^=([0-9]{3})\s+(.+)$')
    DATA_FIELD_PATTERN = re.compile(r'^=([0-9]{3})\s+([0-9\s])([0-9\s])(.*)$')
    SUBFIELD_PATTERN = re.compile(r'\$([a-z0-9])([^$]*)')
    
    def __init__(self):
        self.current_record = None
        
    def parse_document(self, content: str) -> List[MarcRecord]:
        """Parse entire MRK document and return list of records."""
        records = []
        lines = content.split('\n')
        
        current_record = MarcRecord()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            field = self.parse_line(line, line_num)
            if field:
                if field.field_type == FieldType.LEADER:
                    # New record starts with leader
                    if current_record.leader or current_record.fields:
                        records.append(current_record)
                        current_record = MarcRecord()
                    current_record.leader = field
                else:
                    current_record.fields.append(field)
        
        # Add the last record
        if current_record.leader or current_record.fields:
            records.append(current_record)
            
        return records
    
    def parse_line(self, line: str, line_number: int = 0) -> Optional[MarcField]:
        """Parse a single MRK line and return a MarcField."""
        if not line.startswith('='):
            return None
            
        # Try to match leader
        leader_match = self.LEADER_PATTERN.match(line)
        if leader_match:
            return MarcField(
                tag="LDR",
                field_type=FieldType.LEADER,
                content=leader_match.group(1),
                line_number=line_number,
                start_pos=0,
                end_pos=len(line)
            )
        
        # Try to match control field (001-009)
        control_match = self.CONTROL_FIELD_PATTERN.match(line)
        if control_match and control_match.group(1) < '010':
            return MarcField(
                tag=control_match.group(1),
                field_type=FieldType.CONTROL,
                content=control_match.group(2),
                line_number=line_number,
                start_pos=0,
                end_pos=len(line)
            )
        
        # Try to match data field
        data_match = self.DATA_FIELD_PATTERN.match(line)
        if data_match:
            tag = data_match.group(1)
            ind1 = data_match.group(2).strip() or ' '
            ind2 = data_match.group(3).strip() or ' '
            subfield_data = data_match.group(4)
            
            # Parse subfields
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
    
    def get_field_at_position(self, content: str, line: int, character: int) -> Optional[MarcField]:
        """Get the MARC field at a specific line and character position."""
        lines = content.split('\n')
        if line >= len(lines):
            return None
            
        line_content = lines[line]
        return self.parse_line(line_content, line + 1)
    
    def get_subfield_at_position(self, field: MarcField, character: int) -> Optional[MarcSubfield]:
        """Get the subfield at a specific character position within a field."""
        if not field.subfields:
            return None
            
        for subfield in field.subfields:
            if subfield.start_pos <= character <= subfield.end_pos:
                return subfield
                
        return None
    
    def validate_field(self, field: MarcField) -> List[str]:
        """Validate a MARC field and return list of error messages."""
        errors = []
        
        if field.field_type == FieldType.DATA:
            # Validate indicators
            if field.indicator1 and not (field.indicator1.isdigit() or field.indicator1 == ' '):
                errors.append(f"Invalid first indicator '{field.indicator1}' for field {field.tag}")
            if field.indicator2 and not (field.indicator2.isdigit() or field.indicator2 == ' '):
                errors.append(f"Invalid second indicator '{field.indicator2}' for field {field.tag}")
            
            # Validate subfields
            if field.subfields:
                for subfield in field.subfields:
                    if not re.match(r'^[a-z0-9]$', subfield.code):
                        errors.append(f"Invalid subfield code '{subfield.code}' in field {field.tag}")
        
        return errors


def create_parser() -> MrkParser:
    """Factory function to create a new MRK parser."""
    return MrkParser()