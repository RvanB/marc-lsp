"""
MARC Fixed Field Definitions
Character-by-character definitions for MARC fixed fields like 008
"""

from typing import Dict, Optional, NamedTuple
from dataclasses import dataclass


@dataclass
class FixedFieldPosition:
    """Definition of a character position in a fixed field."""
    start: int
    end: int
    name: str
    description: str
    values: Optional[Dict[str, str]] = None  # value -> description mapping


class MarcFixedFields:
    """Definitions for MARC fixed fields character positions."""
    
    def __init__(self):
        self.field_definitions = self._initialize_fixed_fields()
    
    def _initialize_fixed_fields(self) -> Dict[str, Dict[str, FixedFieldPosition]]:
        """Initialize fixed field definitions."""
        fields = {}
        
        # 008 Field - Fixed-Length Data Elements (Books)
        # This is a comprehensive definition based on LC documentation
        fields["008"] = {
            "date_entered": FixedFieldPosition(
                start=0, end=5,
                name="Date entered on file",
                description="Date the record was entered into the database (YYMMDD format)"
            ),
            "type_of_date": FixedFieldPosition(
                start=6, end=6,
                name="Type of date/Publication status",
                description="Type of date in Date 1 and Date 2",
                values={
                    "b": "No dates given; B.C. date involved",
                    "c": "Continuing resource currently published",
                    "d": "Continuing resource ceased publication", 
                    "e": "Detailed date",
                    "i": "Inclusive dates of collection",
                    "k": "Range of years of bulk of collection",
                    "m": "Multiple dates",
                    "n": "Dates unknown",
                    "p": "Date of distribution/release/issue and production/recording session different",
                    "q": "Questionable date",
                    "r": "Reprint/reissue date and original date",
                    "s": "Single known/probable date",
                    "t": "Publication date and copyright date",
                    "u": "Continuing resource status unknown",
                    "|": "No attempt to code"
                }
            ),
            "date1": FixedFieldPosition(
                start=7, end=10,
                name="Date 1",
                description="First date in bibliographic record"
            ),
            "date2": FixedFieldPosition(
                start=11, end=14,
                name="Date 2", 
                description="Second date in bibliographic record"
            ),
            "place_of_publication": FixedFieldPosition(
                start=15, end=17,
                name="Place of publication, production, or execution",
                description="Geographic area code for place of publication"
            ),
            "language": FixedFieldPosition(
                start=35, end=37,
                name="Language",
                description="Language code for the language of the item"
            ),
            "modified_record": FixedFieldPosition(
                start=38, end=38,
                name="Modified record",
                description="Whether the record has been modified",
                values={
                    " ": "Not modified",
                    "d": "Dashed-on information omitted",
                    "o": "Completely romanized/printed cards romanized",
                    "r": "Completely romanized/printed cards in script",
                    "s": "Shortened",
                    "x": "Missing characters",
                    "|": "No attempt to code"
                }
            ),
            "cataloging_source": FixedFieldPosition(
                start=39, end=39,
                name="Cataloging source",
                description="Original cataloging source",
                values={
                    " ": "National bibliographic agency",
                    "c": "Cooperative cataloging program", 
                    "d": "Other",
                    "u": "Unknown",
                    "|": "No attempt to code"
                }
            )
        }
        
        # Add material-specific 008 positions for books
        fields["008"].update({
            "illustrations": FixedFieldPosition(
                start=18, end=21,
                name="Illustrations",
                description="Illustration code(s)",
                values={
                    " ": "No illustrations",
                    "a": "Illustrations", 
                    "b": "Maps",
                    "c": "Portraits",
                    "d": "Charts",
                    "e": "Plans",
                    "f": "Plates",
                    "g": "Music",
                    "h": "Facsimiles",
                    "i": "Coats of arms",
                    "j": "Genealogical tables",
                    "k": "Forms",
                    "l": "Samples",
                    "m": "Phonodisc, phonowire, etc.",
                    "o": "Photographs",
                    "p": "Illuminations",
                    "|": "No attempt to code"
                }
            ),
            "target_audience": FixedFieldPosition(
                start=22, end=22,
                name="Target audience",
                description="Intellectual level of the item",
                values={
                    " ": "Unknown or not specified",
                    "a": "Preschool",
                    "b": "Primary",
                    "c": "Pre-adolescent",
                    "d": "Adolescent", 
                    "e": "Adult",
                    "f": "Specialized",
                    "g": "General",
                    "j": "Juvenile",
                    "|": "No attempt to code"
                }
            ),
            "form_of_item": FixedFieldPosition(
                start=23, end=23,
                name="Form of item",
                description="Form of material",
                values={
                    " ": "None of the following",
                    "a": "Microfilm",
                    "b": "Microfiche",
                    "c": "Microopaque",
                    "d": "Large print",
                    "f": "Braille",
                    "o": "Online",
                    "q": "Direct electronic",
                    "r": "Regular print reproduction",
                    "s": "Electronic",
                    "|": "No attempt to code"
                }
            ),
            "nature_of_contents": FixedFieldPosition(
                start=24, end=27,
                name="Nature of contents",
                description="Special characteristics",
                values={
                    " ": "No specified nature of contents",
                    "a": "Abstracts/summaries",
                    "b": "Bibliographies",
                    "c": "Catalogs",
                    "d": "Dictionaries",
                    "e": "Encyclopedias",
                    "f": "Handbooks",
                    "g": "Legal articles",
                    "i": "Indexes",
                    "j": "Patent document",
                    "k": "Discographies",
                    "l": "Legislation",
                    "m": "Theses",
                    "n": "Surveys of literature",
                    "o": "Reviews",
                    "p": "Programmed texts",
                    "q": "Filmographies",
                    "r": "Directories",
                    "s": "Statistics",
                    "t": "Technical reports",
                    "u": "Standards/specifications",
                    "v": "Legal cases and case notes",
                    "w": "Law reports and digests",
                    "x": "Other reports",
                    "y": "Yearbooks",
                    "z": "Treaties",
                    "2": "Offprints",
                    "5": "Calendars",
                    "6": "Comics/graphic novels",
                    "|": "No attempt to code"
                }
            ),
            "government_publication": FixedFieldPosition(
                start=28, end=28,
                name="Government publication",
                description="Government publication code",
                values={
                    " ": "Not a government publication",
                    "a": "Autonomous or semi-autonomous component",
                    "c": "Multilocal",
                    "f": "Federal/national",
                    "i": "International intergovernmental",
                    "l": "Local",
                    "m": "Multistate",
                    "o": "Government publication-level undetermined",
                    "s": "State, provincial, territorial, dependent, etc.",
                    "u": "Unknown if item is government publication",
                    "z": "Other",
                    "|": "No attempt to code"
                }
            ),
            "conference_publication": FixedFieldPosition(
                start=29, end=29,
                name="Conference publication",
                description="Conference publication indicator",
                values={
                    "0": "Not a conference publication",
                    "1": "Conference publication",
                    "|": "No attempt to code"
                }
            ),
            "festschrift": FixedFieldPosition(
                start=30, end=30,
                name="Festschrift",
                description="Festschrift indicator",
                values={
                    "0": "Not a festschrift",
                    "1": "Festschrift", 
                    "|": "No attempt to code"
                }
            ),
            "index": FixedFieldPosition(
                start=31, end=31,
                name="Index",
                description="Index present indicator",
                values={
                    "0": "No index",
                    "1": "Index present",
                    "|": "No attempt to code"
                }
            ),
            "literary_form": FixedFieldPosition(
                start=33, end=33,
                name="Literary form",
                description="Literary form code",
                values={
                    "0": "Not fiction (not further specified)",
                    "1": "Fiction (not further specified)",
                    "c": "Comic strips",
                    "d": "Dramas",
                    "e": "Essays",
                    "f": "Novels",
                    "h": "Humor, satires, etc.",
                    "i": "Letters",
                    "j": "Short stories",
                    "m": "Mixed forms",
                    "p": "Poetry",
                    "s": "Speeches",
                    "u": "Unknown",
                    "|": "No attempt to code"
                }
            ),
            "biography": FixedFieldPosition(
                start=34, end=34,
                name="Biography",
                description="Biography code",
                values={
                    " ": "No biographical material",
                    "a": "Autobiography",
                    "b": "Individual biography",
                    "c": "Collective biography",
                    "d": "Contains biographical information",
                    "|": "No attempt to code"
                }
            )
        })
        
        # 001 Field - Control Number  
        fields["001"] = {
            "control_number": FixedFieldPosition(
                start=0, end=-1,
                name="Control Number",
                description="System-assigned unique record identifier"
            )
        }
        
        # 003 Field - Control Number Identifier
        fields["003"] = {
            "control_number_identifier": FixedFieldPosition(
                start=0, end=-1,
                name="Control Number Identifier", 
                description="MARC code for the agency assigning the control number"
            )
        }
        
        # 005 Field - Date and Time of Latest Transaction
        fields["005"] = {
            "date_time": FixedFieldPosition(
                start=0, end=-1,
                name="Date and Time of Latest Transaction",
                description="Date and time of the latest record transaction (YYYYMMDDHHMMSS.F format)"
            )
        }
        
        return fields
    
    def get_position_info(self, field_tag: str, char_position: int) -> Optional[FixedFieldPosition]:
        """Get information for a specific character position in a fixed field."""
        if field_tag not in self.field_definitions:
            return None
        
        field_def = self.field_definitions[field_tag]
        
        # Find which position definition contains this character
        for pos_name, pos_def in field_def.items():
            if pos_def.end == -1:  # Variable length field
                if char_position >= pos_def.start:
                    return pos_def
            elif pos_def.start <= char_position <= pos_def.end:
                return pos_def
        
        return None
    
    def is_fixed_field(self, field_tag: str) -> bool:
        """Check if a field tag is a fixed field."""
        return field_tag in self.field_definitions


# Global instance
marc_fixed_fields = MarcFixedFields()