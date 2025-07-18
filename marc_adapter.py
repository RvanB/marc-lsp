"""
MARC Adapter
Adapts between dynamic lookup and existing LSP server format
"""

from typing import Optional, Dict
from marc_lookup import marc_lookup, TagInfo, SubfieldInfo
from dataclasses import dataclass

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
    repeatable: bool = False
    indicators: Dict[str, Dict[str, str]] = None  # indicator_num -> value -> description
    subfields: Dict[str, SubfieldDefinition] = None
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}
        if self.subfields is None:
            self.subfields = {}


class MarcAdapter:
    """Adapter to convert between dynamic lookup and LSP server formats."""
    
    def __init__(self):
        self.lookup = marc_lookup
        self.failed_tags = set()  # Cache tags that failed to lookup
    
    def get_tag_definition(self, tag: str) -> Optional[TagDefinition]:
        """Get tag definition in LSP server format."""
        # Skip if we know this tag failed before
        if tag in self.failed_tags:
            return None
        
        tag_info = self.lookup.get_tag_info(tag)
        if not tag_info:
            # Remember that this tag failed
            self.failed_tags.add(tag)
            return None
        
        # Convert subfields
        subfields = {}
        for code, subfield_info in tag_info.subfields.items():
            subfields[code] = SubfieldDefinition(
                code=subfield_info.code,
                name=subfield_info.name,
                description=subfield_info.description,
                repeatable=subfield_info.repeatable
            )
        
        return TagDefinition(
            tag=tag_info.tag,
            name=tag_info.name,
            description=tag_info.description,
            repeatable=tag_info.repeatable,
            indicators=tag_info.indicators,
            subfields=subfields
        )
    
    def get_subfield_definition(self, tag: str, subfield_code: str) -> Optional[SubfieldDefinition]:
        """Get subfield definition in LSP server format."""
        tag_info = self.lookup.get_tag_info(tag)
        if not tag_info or subfield_code not in tag_info.subfields:
            return None
            
        subfield_info = tag_info.subfields[subfield_code]
        return SubfieldDefinition(
            code=subfield_info.code,
            name=subfield_info.name,
            description=subfield_info.description,
            repeatable=subfield_info.repeatable
        )


# Global instance
marc_adapter = MarcAdapter()
