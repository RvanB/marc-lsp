#!/usr/bin/env python3
"""
Generate Static MARC Data

This script uses the existing dynamic lookup system to scrape all MARC tags
from the Library of Congress and generate static JSON files for fast access.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from marc_lookup import marc_lookup, TagInfo, SubfieldInfo
from marc_fixed_fields import marc_fixed_fields


def generate_tag_range(start: int, end: int) -> List[str]:
    """Generate a list of 3-digit tag strings in the given range."""
    return [f"{i:03d}" for i in range(start, end + 1)]


def get_all_marc_tags() -> Dict[str, List[str]]:
    """Get all MARC tags categorized by record type based on actual LC documentation."""
    return {
        "bibliographic": [
            # Control fields (00X)
            "001", "003", "005", "006", "007", "008",
            
            # Numbers and codes (01X-09X) - Common ones
            "010", "013", "015", "016", "017", "018", "020", "022", "024", "025", "026", "027", "028", "030", "031", "032", "033", "034", "035", "036", "037", "038", "040", "041", "042", "043", "044", "045", "046", "047", "048", "050", "051", "052", "055", "060", "061", "066", "070", "071", "072", "074", "080", "082", "083", "084", "085", "086", "088",
            
            # Main entries (1XX)
            "100", "110", "111", "130",
            
            # Titles (20X-24X)
            "210", "222", "240", "242", "243", "245", "246", "247",
            
            # Edition/Imprint (25X-28X)
            "250", "254", "255", "256", "257", "258", "260", "261", "262", "263", "264", "270", "280", "285",
            
            # Physical description (3XX)
            "300", "306", "307", "310", "321", "336", "337", "338", "340", "342", "343", "344", "345", "346", "347", "348", "351", "352", "355", "357", "362", "363", "365", "366", "370", "377", "380", "381", "382", "383", "384", "385", "386", "388",
            
            # Series (4XX)
            "400", "410", "411", "440", "490",
            
            # Notes (5XX)
            "500", "501", "502", "504", "505", "506", "507", "508", "510", "511", "513", "514", "515", "516", "518", "520", "521", "522", "524", "525", "526", "530", "533", "534", "535", "536", "538", "540", "541", "542", "544", "545", "546", "547", "550", "552", "555", "556", "561", "562", "563", "565", "567", "580", "581", "583", "584", "585", "586", "588",
            
            # Subjects (6XX)
            "600", "610", "611", "630", "647", "648", "650", "651", "653", "654", "655", "656", "657", "658", "662", "688",
            
            # Added entries (70X-75X)
            "700", "710", "711", "720", "730", "740", "751", "752", "753", "754",
            
            # Linking entries (76X-78X)
            "760", "762", "765", "767", "770", "772", "773", "774", "775", "776", "777", "780", "785", "786", "787",
            
            # Series added entries (80X-83X)
            "800", "810", "811", "830",
            
            # Electronic location (856)
            "856", "857"
        ],
        "holdings": [
            # Holdings-specific fields based on LC documentation
            "852",  # Location
            "853", "854", "855",  # Captions and patterns
            "856",  # Electronic location
            "857",  # Electronic location (alternate)
            "863", "864", "865",  # Enumeration and chronology 
            "866", "867", "868",  # Textual holdings
            "876", "877", "878"   # Item information
        ]
    }


def convert_tag_info_to_dict(tag_info: TagInfo) -> Dict:
    """Convert TagInfo object to dictionary for JSON serialization."""
    subfields_dict = {}
    for code, subfield_info in tag_info.subfields.items():
        subfields_dict[code] = {
            "code": subfield_info.code,
            "name": subfield_info.name,
            "description": subfield_info.description,
            "repeatable": subfield_info.repeatable
        }
    
    return {
        "tag": tag_info.tag,
        "name": tag_info.name,
        "description": tag_info.description,
        "repeatable": tag_info.repeatable,
        "indicators": tag_info.indicators or {},
        "subfields": subfields_dict
    }


def extract_fixed_field_data() -> Dict:
    """Extract fixed field definitions to dictionary format.
    
    The 008 field has different position meanings for different record types,
    so this is organized by record type when output.
    """
    fixed_fields = {}
    
    for field_tag, positions in marc_fixed_fields.field_definitions.items():
        field_data = {}
        
        for pos_name, pos_def in positions.items():
            field_data[pos_name] = {
                "start": pos_def.start,
                "end": pos_def.end,
                "name": pos_def.name,
                "description": pos_def.description,
                "values": pos_def.values or {}
            }
        
        fixed_fields[field_tag] = field_data
    
    return fixed_fields


def extract_marc_data(tag_list: List[str], category: str) -> Dict:
    """Extract MARC data for a list of tags."""
    total_time_estimate = len(tag_list) * 7 / 60  # 7 seconds per tag in minutes
    logging.info(f"Extracting {category} tags: {len(tag_list)} tags to process")
    logging.info(f"Estimated time: {total_time_estimate:.1f} minutes (respecting 10 req/min limit)")
    
    extracted_tags = {}
    failed_tags = []
    success_count = 0
    
    for i, tag in enumerate(tag_list):
        if tag == "LDR":
            # Leader is handled separately - it's not a numbered tag
            continue
            
        try:
            logging.info(f"Processing {category} tag {tag} ({i+1}/{len(tag_list)})")
            
            # Use existing dynamic lookup
            tag_info = marc_lookup.get_tag_info(tag)
            
            if tag_info:
                extracted_tags[tag] = convert_tag_info_to_dict(tag_info)
                success_count += 1
                logging.info(f"✓ Successfully extracted {tag}: {tag_info.name}")
            else:
                failed_tags.append(tag)
                logging.warning(f"✗ Failed to extract tag {tag}")
            
            # Rate limiting: max 10 requests per minute = 6+ seconds between requests
            time.sleep(7)  # 7 seconds between requests to be safe
            
        except Exception as e:
            failed_tags.append(tag)
            logging.error(f"✗ Error processing tag {tag}: {e}")
    
    logging.info(f"{category.title()} extraction complete: {success_count} successful, {len(failed_tags)} failed")
    if failed_tags:
        logging.info(f"Failed tags: {', '.join(failed_tags[:10])}")
        if len(failed_tags) > 10:
            logging.info(f"... and {len(failed_tags) - 10} more")
    
    return extracted_tags


def generate_marc_data_files():
    """Generate static MARC data files."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scripts/generate_marc_data.log')
        ]
    )
    
    logging.info("Starting MARC data extraction...")
    
    # Get all tags
    all_tags = get_all_marc_tags()
    
    # Create base directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Generate metadata
    metadata = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": "Library of Congress MARC documentation",
        "version": "1.0",
        "generator": "marc-lsp-server data extraction script"
    }
    
    # Extract bibliographic records
    logging.info("=" * 60)
    logging.info("EXTRACTING BIBLIOGRAPHIC RECORDS")
    logging.info("=" * 60)
    
    bib_data = extract_marc_data(all_tags["bibliographic"], "bibliographic")
    
    bib_output = {
        "metadata": metadata,
        "tags": bib_data
    }
    
    bib_file = data_dir / "marc_bibliographic.json"
    with open(bib_file, 'w', encoding='utf-8') as f:
        json.dump(bib_output, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Bibliographic data saved to {bib_file}")
    
    # Extract holdings records
    logging.info("=" * 60)
    logging.info("EXTRACTING HOLDINGS RECORDS")
    logging.info("=" * 60)
    
    holdings_data = extract_marc_data(all_tags["holdings"], "holdings")
    
    holdings_output = {
        "metadata": metadata,
        "tags": holdings_data
    }
    
    holdings_file = data_dir / "marc_holdings.json"
    with open(holdings_file, 'w', encoding='utf-8') as f:
        json.dump(holdings_output, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Holdings data saved to {holdings_file}")
    
    # Extract fixed field data
    logging.info("=" * 60)
    logging.info("EXTRACTING FIXED FIELD DATA")
    logging.info("=" * 60)
    
    fixed_field_data = extract_fixed_field_data()
    
    # Organize fixed fields by record type
    # Check if source has record-type-specific 008 definitions
    record_type_008 = None
    if hasattr(marc_fixed_fields, 'field_definitions_by_type') and "008" in marc_fixed_fields.field_definitions_by_type:
        record_type_008 = marc_fixed_fields.field_definitions_by_type["008"]
    
    if record_type_008:
        # Build record-type-specific structure with 008 variations
        fixed_output = {
            "metadata": metadata,
            "fields": {}
        }
        
        # Get all record types from the 008 data
        for record_type in record_type_008.keys():
            fixed_output["fields"][record_type.upper()] = {}
        
        # Add 008 definitions for each record type
        for record_type, positions in record_type_008.items():
            field_data = {}
            for pos_name, pos_def in positions.items():
                field_data[pos_name] = {
                    "start": pos_def.start,
                    "end": pos_def.end,
                    "name": pos_def.name,
                    "description": pos_def.description,
                    "values": pos_def.values or {}
                }
            fixed_output["fields"][record_type.upper()]["008"] = field_data
        
        # Add other fixed fields to all record types
        for field_tag, field_def in fixed_field_data.items():
            if field_tag != "008":
                for record_type in fixed_output["fields"].keys():
                    fixed_output["fields"][record_type][field_tag] = field_def
        
        logging.info("Fixed fields organized by record type with record-type-specific 008 definitions")
    else:
        # Standard organization by record type (all fields same across types)
        fixed_output = {
            "metadata": metadata,
            "fields": {
                "BIB": fixed_field_data,
                "HOLD": fixed_field_data,
                "AUTH": fixed_field_data,
                "CLASS": fixed_field_data,
                "COMM": fixed_field_data,
            }
        }
        logging.info("Fixed fields organized by record type (generic definitions)")
    
    fixed_file = data_dir / "marc_fixed_fields.json"
    with open(fixed_file, 'w', encoding='utf-8') as f:
        json.dump(fixed_output, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Fixed field data saved to {fixed_file}")
    
    # Summary
    total_bib_tags = len(bib_data)
    total_holdings_tags = len(holdings_data)
    total_fixed_fields = len(fixed_field_data)
    
    logging.info("=" * 60)
    logging.info("EXTRACTION COMPLETE")
    logging.info("=" * 60)
    logging.info(f"Bibliographic tags: {total_bib_tags}")
    logging.info(f"Holdings tags: {total_holdings_tags}")
    logging.info(f"Fixed fields: {total_fixed_fields}")
    logging.info(f"Total: {total_bib_tags + total_holdings_tags + total_fixed_fields}")
    
    print(f"\n🎉 MARC data extraction completed successfully!")
    print(f"📊 Generated {total_bib_tags + total_holdings_tags + total_fixed_fields} definitions")
    print(f"📁 Files saved to: {data_dir.absolute()}")


if __name__ == "__main__":
    generate_marc_data_files()