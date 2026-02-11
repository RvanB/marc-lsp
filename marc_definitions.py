"""
MARC Static Data Loader

Fast static data loader that replaces the dynamic Library of Congress lookup system.
Uses pre-generated JSON files for instant access to MARC field definitions.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Literal
from dataclasses import dataclass
from enum import Enum


class RecordType(Enum):
    """MARC record types based on Leader byte 6."""
    BIBLIOGRAPHIC = "bib"
    HOLDINGS = "hold"
    CLASSIFICATION = "class"
    AUTHORITY = "auth"
    COMMUNITY = "comm"
    UNKNOWN = "unknown"


@dataclass
class SubfieldDefinition:
    """Definition of a MARC subfield."""
    code: str
    name: str
    description: str
    repeatable: bool = False


@dataclass
class TagDefinition:
    """Definition of a MARC tag."""
    tag: str
    name: str
    description: str
    indicators: Dict[str, Dict[str, str]] = None  # indicator_num -> value -> description
    subfields: Dict[str, SubfieldDefinition] = None
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}
        if self.subfields is None:
            self.subfields = {}

@dataclass
class FixedFieldPosition:
    """Definition of a character position in a fixed field."""
    start: int
    end: int
    name: str
    description: str
    values: Optional[Dict[str, str]] = None  # value -> description mapping


class MarcStaticData:
    """Static MARC data loader for fast field lookups."""
    
    def __init__(self, data_dir: str = ""):
        """Initialize static data loader."""
        if not data_dir:
            # Try data directory relative to this file first (development),
            # then fall back to sys.prefix/data (installed via pip/pipx)
            local_data = Path(__file__).parent / "data"
            prefix_data = Path(sys.prefix) / "data"
            if local_data.exists():
                self.data_dir = local_data
            else:
                self.data_dir = prefix_data
        else:
            self.data_dir = Path(data_dir)
        
        # In-memory caches
        self._bibliographic_tags = {}
        self._holdings_tags = {}
        self._fixed_fields = {}  # Default fixed fields
        self._fixed_fields_by_type = {}  # Record-type specific fixed fields
        self._loaded = False
        
        # Lazy load data when first accessed
        self._load_data()
    
    def _load_data(self):
        """Load all static data from JSON files."""
        if self._loaded:
            return
        
        try:
            # Load bibliographic tags
            bib_file = self.data_dir / "marc_bibliographic.json"
            if bib_file.exists():
                with open(bib_file, 'r', encoding='utf-8') as f:
                    bib_data = json.load(f)
                    self._bibliographic_tags = self._parse_tag_data(bib_data.get("tags", {}))
                    logging.info(f"Loaded {len(self._bibliographic_tags)} bibliographic tags")
            
            # Load holdings tags
            holdings_file = self.data_dir / "marc_holdings.json"
            if holdings_file.exists():
                with open(holdings_file, 'r', encoding='utf-8') as f:
                    holdings_data = json.load(f)
                    self._holdings_tags = self._parse_tag_data(holdings_data.get("tags", {}))
                    logging.info(f"Loaded {len(self._holdings_tags)} holdings tags")
            
            # Load fixed fields
            fixed_file = self.data_dir / "marc_fixed_fields.json"
            if fixed_file.exists():
                with open(fixed_file, 'r', encoding='utf-8') as f:
                    fixed_data = json.load(f)
                    fields_data = fixed_data.get("fields", {})
                    
                    # Fields are organized by record type (BIB, HOLD, etc.)
                    for record_type, type_fields in fields_data.items():
                        self._fixed_fields_by_type[record_type] = self._parse_fixed_field_data(type_fields)
                    logging.info(f"Loaded record-type-specific fixed field definitions for: {', '.join(self._fixed_fields_by_type.keys())}")
            
            # Use test data if main files don't exist
            test_file = self.data_dir / "test_extraction.json"
            if not self._bibliographic_tags and not self._holdings_tags and test_file.exists():
                logging.info("Using test extraction data")
                with open(test_file, 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                    self._bibliographic_tags = self._parse_tag_data(test_data.get("marc_tags", {}))
                    self._fixed_fields = self._parse_fixed_field_data(test_data.get("fixed_fields", {}))
            
            self._loaded = True
            
        except Exception as e:
            logging.error(f"Failed to load static MARC data: {e}")
            # Continue with empty data rather than crashing
    
    def detect_record_type(self, leader: str) -> RecordType:
        """Detect MARC record type from the leader (byte 6)."""
        if not leader or len(leader) < 7:
            return RecordType.UNKNOWN
        
        type_code = leader[6]
        
        # Map leader byte 6 to record type
        type_map = {
            'a': RecordType.BIBLIOGRAPHIC,  # Language material
            'c': RecordType.BIBLIOGRAPHIC,  # Notated music
            'd': RecordType.BIBLIOGRAPHIC,  # Manuscript notated music
            'e': RecordType.BIBLIOGRAPHIC,  # Cartographic material
            'f': RecordType.BIBLIOGRAPHIC,  # Manuscript cartographic
            'g': RecordType.BIBLIOGRAPHIC,  # Projected medium
            'i': RecordType.BIBLIOGRAPHIC,  # Nonmusical sound recording
            'j': RecordType.BIBLIOGRAPHIC,  # Musical sound recording
            'k': RecordType.BIBLIOGRAPHIC,  # Two-dimensional nonprojectable graphic
            'm': RecordType.BIBLIOGRAPHIC,  # Computer file
            'o': RecordType.BIBLIOGRAPHIC,  # Kit
            'p': RecordType.BIBLIOGRAPHIC,  # Mixed materials
            'r': RecordType.BIBLIOGRAPHIC,  # Three-dimensional artifact or naturally occurring object
            't': RecordType.BIBLIOGRAPHIC,  # Manuscript language material
            'u': RecordType.UNKNOWN,        # Unknown
            'v': RecordType.BIBLIOGRAPHIC,  # Single unit within an integrating resource
            'w': RecordType.BIBLIOGRAPHIC,  # Integrating resource
            'x': RecordType.BIBLIOGRAPHIC,  # Serial integrating resource
            'y': RecordType.BIBLIOGRAPHIC,  # Serial monograph
            'z': RecordType.BIBLIOGRAPHIC,  # Serial item
            'v': RecordType.HOLDINGS,       # Holdings (Leader position 6)
            'c': RecordType.CLASSIFICATION,
            'n': RecordType.AUTHORITY,
            'z': RecordType.AUTHORITY,
        }
        
        return type_map.get(type_code, RecordType.UNKNOWN)
    
    def _parse_tag_data(self, tag_data: Dict) -> Dict[str, TagDefinition]:
        """Parse tag data from JSON into TagDefinition objects."""
        parsed_tags = {}
        
        for tag, data in tag_data.items():
            # Parse subfields
            subfields = {}
            for code, subfield_data in data.get("subfields", {}).items():
                subfields[code] = SubfieldDefinition(
                    code=subfield_data["code"],
                    name=subfield_data["name"],
                    description=subfield_data["description"],
                    repeatable=subfield_data.get("repeatable", False)
                )
            
            # Create tag definition
            parsed_tags[tag] = TagDefinition(
                tag=data["tag"],
                name=data["name"],
                description=data["description"],
                indicators=data.get("indicators", {}),
                subfields=subfields
            )
        
        return parsed_tags
    
    def _parse_fixed_field_data(self, fixed_data: Dict) -> Dict[str, Dict[str, FixedFieldPosition]]:
        """Parse fixed field data from JSON into FixedFieldPosition objects."""
        parsed_fields = {}
        
        for field_tag, positions in fixed_data.items():
            field_positions = {}
            
            for pos_name, pos_data in positions.items():
                field_positions[pos_name] = FixedFieldPosition(
                    start=pos_data["start"],
                    end=pos_data["end"],
                    name=pos_data["name"],
                    description=pos_data["description"],
                    values=pos_data.get("values")
                )
            
            parsed_fields[field_tag] = field_positions
        
        return parsed_fields
    
    def get_tag_definition(self, tag: str) -> Optional[TagDefinition]:
        """Get tag definition for bibliographic or holdings records."""
        # Check bibliographic tags first
        if tag in self._bibliographic_tags:
            return self._bibliographic_tags[tag]
        
        # Check holdings tags
        if tag in self._holdings_tags:
            return self._holdings_tags[tag]
        
        return None
    
    def get_subfield_definition(self, tag: str, subfield_code: str) -> Optional[SubfieldDefinition]:
        """Get subfield definition for a specific tag and subfield code."""
        tag_def = self.get_tag_definition(tag)
        if not tag_def:
            return None
        
        return tag_def.subfields.get(subfield_code)
    
    def get_all_tags(self) -> list[str]:
        """Get list of all available tag numbers."""
        all_tags = list(self._bibliographic_tags.keys()) + list(self._holdings_tags.keys())
        return sorted(set(all_tags))
    
    def get_subfields_for_tag(self, tag: str) -> list[str]:
        """Get list of subfield codes for a specific tag."""
        tag_def = self.get_tag_definition(tag)
        if not tag_def:
            return []
        
        return list(tag_def.subfields.keys())
    
    def is_fixed_field(self, field_tag: str, record_type: Optional[RecordType] = None) -> bool:
        """Check if a field tag is a fixed field in the given record type."""
        if not record_type:
            return False
        
        record_type_key = record_type.value.upper()
        if record_type_key in self._fixed_fields_by_type:
            return field_tag in self._fixed_fields_by_type[record_type_key]
        
        return False
    
    def get_position_info(self, field_tag: str, char_position: int, record_type: RecordType) -> Optional[FixedFieldPosition]:
        """Get information for a specific character position in a fixed field.
        
        Args:
            field_tag: The MARC field tag
            char_position: The character position to look up
            record_type: Record type for type-specific lookups
        """
        record_type_key = record_type.value.upper()
        if record_type_key not in self._fixed_fields_by_type:
            return None
        
        if field_tag not in self._fixed_fields_by_type[record_type_key]:
            return None
        
        field_def = self._fixed_fields_by_type[record_type_key][field_tag]
        return self._find_position_in_def(field_def, char_position)
    
    def _find_position_in_def(self, field_def: Dict[str, FixedFieldPosition], char_position: int) -> Optional[FixedFieldPosition]:
        """Helper to find position definition within a field."""
        for pos_name, pos_def in field_def.items():
            if pos_def.end == -1:  # Variable length field
                if char_position >= pos_def.start:
                    return pos_def
            elif pos_def.start <= char_position <= pos_def.end:
                return pos_def
        
        return None
    
    def get_data_info(self):
        """Get information about loaded data."""
        return {
            "bibliographic_tags": len(self._bibliographic_tags),
            "holdings_tags": len(self._holdings_tags),
            "fixed_fields": len(self._fixed_fields),
            "total_tags": len(self._bibliographic_tags) + len(self._holdings_tags),
            "data_loaded": self._loaded
        }


