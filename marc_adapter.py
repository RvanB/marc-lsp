"""
MARC Adapter
Adapts between dynamic lookup and existing LSP server format
"""

from typing import Optional
from marc_tags import TagDefinition, SubfieldDefinition
from marc_lookup import marc_lookup, TagInfo, SubfieldInfo


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
    
    def get_all_tags(self):
        """Get all available tags - fallback to hardcoded for completion."""
        # For completion, we'll still use the hardcoded list as a starting point
        # Dynamic lookup will be used for detailed information
        from marc_tags import marc_tag_db
        return marc_tag_db.get_all_tags()
    
    def get_subfields_for_tag(self, tag: str):
        """Get subfields for a tag - try dynamic first, fallback to hardcoded."""
        tag_info = self.lookup.get_tag_info(tag)
        if tag_info and tag_info.subfields:
            return list(tag_info.subfields.keys())
        
        # Fallback to hardcoded
        from marc_tags import marc_tag_db
        return marc_tag_db.get_subfields_for_tag(tag)


# Global instance
marc_adapter = MarcAdapter()