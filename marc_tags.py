"""
MARC Tag Reference Database

Contains definitions and documentation for MARC bibliographic tags
and their subfields based on Library of Congress documentation.
"""

from typing import Dict, List, Optional
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


class MarcTagDatabase:
    """Database of MARC tag definitions."""
    
    def __init__(self):
        self.tags = self._initialize_tags()
    
    def _initialize_tags(self) -> Dict[str, TagDefinition]:
        """Initialize the tag database with common MARC tags."""
        tags = {}
        
        # Leader
        tags["LDR"] = TagDefinition(
            tag="LDR",
            name="Leader",
            description="Record header containing coded information for processing the record"
        )
        
        # Control Fields (001-009)
        tags["001"] = TagDefinition(
            tag="001",
            name="Control Number",
            description="System-assigned unique record identifier"
        )
        
        tags["003"] = TagDefinition(
            tag="003", 
            name="Control Number Identifier",
            description="MARC code for the agency assigning the control number"
        )
        
        tags["005"] = TagDefinition(
            tag="005",
            name="Date and Time of Latest Transaction", 
            description="Date and time of the latest record transaction"
        )
        
        tags["008"] = TagDefinition(
            tag="008",
            name="Fixed-Length Data Elements",
            description="Fixed-length data elements that provide coded information about the record"
        )
        
        # Main Entry Fields (1XX)
        tags["100"] = TagDefinition(
            tag="100",
            name="Main Entry--Personal Name",
            description="Personal name used as a main entry",
            indicators={
                "1": {
                    "0": "Forename",
                    "1": "Surname", 
                    "3": "Family name"
                },
                "2": {" ": "No information provided"}
            },
            subfields={
                "a": SubfieldDefinition("a", "Personal name", "Personal name"),
                "b": SubfieldDefinition("b", "Numeration", "Roman numeral or roman numeral and name of dynasty"),
                "c": SubfieldDefinition("c", "Titles and words", "Titles and other words associated with name", True),
                "d": SubfieldDefinition("d", "Dates", "Dates associated with name"),
                "e": SubfieldDefinition("e", "Relator term", "Designation of function", True),
                "q": SubfieldDefinition("q", "Fuller form of name", "More complete form of name")
            }
        )
        
        tags["110"] = TagDefinition(
            tag="110", 
            name="Main Entry--Corporate Name",
            description="Corporate name used as a main entry",
            indicators={
                "1": {
                    "0": "Inverted name",
                    "1": "Jurisdiction name",
                    "2": "Name in direct order"
                },
                "2": {" ": "No information provided"}
            },
            subfields={
                "a": SubfieldDefinition("a", "Corporate name", "Corporate name or jurisdiction name"),
                "b": SubfieldDefinition("b", "Subordinate unit", "Subordinate unit", True),
                "c": SubfieldDefinition("c", "Location of meeting", "Location of meeting", True),
                "d": SubfieldDefinition("d", "Date of meeting or treaty", "Date of meeting or signing", True),
                "n": SubfieldDefinition("n", "Number of part/section/meeting", "Number designation", True)
            }
        )
        
        # Title Fields (2XX)
        tags["245"] = TagDefinition(
            tag="245",
            name="Title Statement", 
            description="Title and statement of responsibility information",
            indicators={
                "1": {
                    "0": "No added entry",
                    "1": "Added entry"
                },
                "2": {
                    "0": "No nonfiling characters",
                    "1": "Number of nonfiling characters (1)",
                    "2": "Number of nonfiling characters (2)",
                    "3": "Number of nonfiling characters (3)",
                    "4": "Number of nonfiling characters (4)",
                    "5": "Number of nonfiling characters (5)",
                    "6": "Number of nonfiling characters (6)",
                    "7": "Number of nonfiling characters (7)",
                    "8": "Number of nonfiling characters (8)",
                    "9": "Number of nonfiling characters (9)"
                }
            },
            subfields={
                "a": SubfieldDefinition("a", "Title", "Title proper"),
                "b": SubfieldDefinition("b", "Remainder of title", "Remainder of title"),
                "c": SubfieldDefinition("c", "Statement of responsibility", "Statement of responsibility"),
                "f": SubfieldDefinition("f", "Inclusive dates", "Inclusive dates"),
                "g": SubfieldDefinition("g", "Bulk dates", "Bulk dates"),
                "h": SubfieldDefinition("h", "Medium", "General material designation"),
                "k": SubfieldDefinition("k", "Form", "Form", True),
                "n": SubfieldDefinition("n", "Number of part/section", "Number designation", True),
                "p": SubfieldDefinition("p", "Name of part/section", "Name designation", True),
                "s": SubfieldDefinition("s", "Version", "Version")
            }
        )
        
        # Edition, Imprint Fields (25X-28X)
        tags["250"] = TagDefinition(
            tag="250",
            name="Edition Statement",
            description="Information relating to the edition of a work",
            subfields={
                "a": SubfieldDefinition("a", "Edition statement", "Edition statement"),
                "b": SubfieldDefinition("b", "Remainder of edition statement", "Remainder of edition statement")
            }
        )
        
        tags["260"] = TagDefinition(
            tag="260",
            name="Publication, Distribution, etc. (Imprint)",
            description="Publication, distribution, etc. information",
            indicators={
                "1": {" ": "Not applicable/No information provided", "2": "Intervening publisher", "3": "Current/latest publisher"},
                "2": {" ": "Not applicable/No information provided"}
            },
            subfields={
                "a": SubfieldDefinition("a", "Place of publication", "Place of publication, distribution", True),
                "b": SubfieldDefinition("b", "Name of publisher", "Name of publisher, distributor", True),
                "c": SubfieldDefinition("c", "Date of publication", "Date of publication, distribution", True),
                "e": SubfieldDefinition("e", "Place of manufacture", "Place of manufacture", True),
                "f": SubfieldDefinition("f", "Manufacturer", "Manufacturer", True),
                "g": SubfieldDefinition("g", "Date of manufacture", "Date of manufacture", True)
            }
        )
        
        # Physical Description Fields (3XX)
        tags["300"] = TagDefinition(
            tag="300",
            name="Physical Description", 
            description="Physical description of the described item",
            subfields={
                "a": SubfieldDefinition("a", "Extent", "Extent", True),
                "b": SubfieldDefinition("b", "Other physical details", "Other physical details"),
                "c": SubfieldDefinition("c", "Dimensions", "Dimensions", True),
                "e": SubfieldDefinition("e", "Accompanying material", "Accompanying material")
            }
        )
        
        # Series Fields (4XX)
        tags["490"] = TagDefinition(
            tag="490",
            name="Series Statement",
            description="Series statement for which no series added entry is traced or for which the added entry is traced differently",
            indicators={
                "1": {
                    "0": "Series not traced",
                    "1": "Series traced"
                },
                "2": {" ": "Not applicable/No information provided"}
            },
            subfields={
                "a": SubfieldDefinition("a", "Series statement", "Series statement", True),
                "l": SubfieldDefinition("l", "Library of Congress call number", "Library of Congress call number"),
                "v": SubfieldDefinition("v", "Volume designation", "Volume designation", True),
                "x": SubfieldDefinition("x", "International Standard Serial Number", "ISSN", True)
            }
        )
        
        # Note Fields (5XX)
        tags["500"] = TagDefinition(
            tag="500",
            name="General Note",
            description="General note for which a specialized 5XX note field has not been defined",
            repeatable=True,
            subfields={
                "a": SubfieldDefinition("a", "General note", "General note")
            }
        )
        
        tags["504"] = TagDefinition(
            tag="504",
            name="Bibliography, etc. Note",
            description="Note that indicates the presence of a bibliography, discography, filmography, etc.",
            repeatable=True,
            subfields={
                "a": SubfieldDefinition("a", "Bibliography, etc. note", "Bibliography, etc. note"),
                "b": SubfieldDefinition("b", "Number of references", "Number of references")
            }
        )
        
        # Subject Access Fields (6XX)
        tags["650"] = TagDefinition(
            tag="650", 
            name="Subject Added Entry--Topical Term",
            description="Subject added entry in which the entry element is a topical term",
            repeatable=True,
            indicators={
                "1": {
                    " ": "No information provided",
                    "0": "No level specified",
                    "1": "Primary",
                    "2": "Secondary"
                },
                "2": {
                    "0": "Library of Congress Subject Headings",
                    "1": "LC subject headings for children's literature",
                    "2": "Medical Subject Headings",
                    "3": "National Agricultural Library subject authority file",
                    "4": "Source not specified",
                    "5": "Canadian Subject Headings",
                    "6": "Répertoire de vedettes-matière",
                    "7": "Source specified in subfield $2"
                }
            },
            subfields={
                "a": SubfieldDefinition("a", "Topical term", "Topical term or geographic name entry element"),
                "b": SubfieldDefinition("b", "Topical term following", "Following geographic name entry element"),
                "c": SubfieldDefinition("c", "Location of event", "Location of event"),
                "d": SubfieldDefinition("d", "Active dates", "Active dates"),
                "v": SubfieldDefinition("v", "Form subdivision", "Form subdivision", True),
                "x": SubfieldDefinition("x", "General subdivision", "General subdivision", True),
                "y": SubfieldDefinition("y", "Chronological subdivision", "Chronological subdivision", True),
                "z": SubfieldDefinition("z", "Geographic subdivision", "Geographic subdivision", True),
                "2": SubfieldDefinition("2", "Source of heading", "Source of heading or term")
            }
        )
        
        # Added Entry Fields (7XX)
        tags["700"] = TagDefinition(
            tag="700",
            name="Added Entry--Personal Name",
            description="Personal name used as an added entry",
            repeatable=True,
            indicators={
                "1": {
                    "0": "Forename",
                    "1": "Surname",
                    "3": "Family name"
                },
                "2": {
                    " ": "No information provided",
                    "2": "Analytical entry"
                }
            },
            subfields={
                "a": SubfieldDefinition("a", "Personal name", "Personal name"),
                "b": SubfieldDefinition("b", "Numeration", "Numeration"),
                "c": SubfieldDefinition("c", "Titles and words", "Titles and other words", True),
                "d": SubfieldDefinition("d", "Dates", "Dates associated with name"),
                "e": SubfieldDefinition("e", "Relator term", "Relator term", True),
                "q": SubfieldDefinition("q", "Fuller form of name", "Fuller form of name"),
                "t": SubfieldDefinition("t", "Title of a work", "Title of a work")
            }
        )
        
        tags["710"] = TagDefinition(
            tag="710",
            name="Added Entry--Corporate Name",
            description="Corporate name used as an added entry",
            repeatable=True,
            indicators={
                "1": {
                    "0": "Inverted name",
                    "1": "Jurisdiction name", 
                    "2": "Name in direct order"
                },
                "2": {
                    " ": "No information provided",
                    "2": "Analytical entry"
                }
            },
            subfields={
                "a": SubfieldDefinition("a", "Corporate name", "Corporate name or jurisdiction name"),
                "b": SubfieldDefinition("b", "Subordinate unit", "Subordinate unit", True),
                "c": SubfieldDefinition("c", "Location of meeting", "Location of meeting", True),
                "d": SubfieldDefinition("d", "Date of meeting", "Date of meeting or treaty signing", True)
            }
        )
        
        # Electronic Location and Access (856)
        tags["856"] = TagDefinition(
            tag="856",
            name="Electronic Location and Access",
            description="Information needed to locate and access an electronic resource",
            repeatable=True,
            indicators={
                "1": {
                    " ": "No information provided",
                    "0": "Email",
                    "1": "FTP",
                    "2": "Remote login (Telnet)",
                    "3": "Dial-up",
                    "4": "HTTP",
                    "7": "Method specified in subfield $2"
                },
                "2": {
                    " ": "No information provided",
                    "0": "Resource",
                    "1": "Version of resource",
                    "2": "Related resource",
                    "8": "No display constant generated"
                }
            },
            subfields={
                "a": SubfieldDefinition("a", "Host name", "Host name", True),
                "f": SubfieldDefinition("f", "Electronic name", "Electronic name", True),
                "u": SubfieldDefinition("u", "Uniform Resource Identifier", "Uniform Resource Identifier", True),
                "x": SubfieldDefinition("x", "Nonpublic note", "Nonpublic note", True),
                "z": SubfieldDefinition("z", "Public note", "Public note", True),
                "3": SubfieldDefinition("3", "Materials specified", "Materials specified")
            }
        )
        
        return tags
    
    def get_tag_definition(self, tag: str) -> Optional[TagDefinition]:
        """Get definition for a specific MARC tag."""
        return self.tags.get(tag)
    
    def get_subfield_definition(self, tag: str, subfield_code: str) -> Optional[SubfieldDefinition]:
        """Get definition for a specific subfield within a tag."""
        tag_def = self.get_tag_definition(tag)
        if not tag_def or not tag_def.subfields:
            return None
        return tag_def.subfields.get(subfield_code)
    
    def get_all_tags(self) -> List[str]:
        """Get list of all available tags."""
        return list(self.tags.keys())
    
    def get_tags_by_range(self, start: str, end: str) -> List[str]:
        """Get tags within a specific range."""
        return [tag for tag in self.tags.keys() if start <= tag <= end]
    
    def get_subfields_for_tag(self, tag: str) -> List[str]:
        """Get list of valid subfield codes for a tag."""
        tag_def = self.get_tag_definition(tag)
        if not tag_def or not tag_def.subfields:
            return []
        return list(tag_def.subfields.keys())


# Global instance
marc_tag_db = MarcTagDatabase()