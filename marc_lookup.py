"""
MARC Tag Dynamic Lookup
Fetches MARC tag information from Library of Congress website
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
import time
import logging
import hashlib
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class SubfieldInfo:
    """Information about a MARC subfield."""
    code: str
    name: str
    description: str
    repeatable: bool = False


@dataclass
class TagInfo:
    """Information about a MARC tag."""
    tag: str
    name: str
    description: str
    repeatable: bool = False
    indicators: Dict[str, Dict[str, str]] = None
    subfields: Dict[str, SubfieldInfo] = None
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}
        if self.subfields is None:
            self.subfields = {}


class MarcHtmlCache:
    """Cache for HTML pages from Library of Congress with TTL."""
    
    def __init__(self, cache_dir: str = "marc_html_cache", ttl_hours: int = 168):  # 1 week default
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600
        self.parsed_cache = {}  # In-memory cache for parsed TagInfo objects
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
    
    def _get_cache_file(self, url: str) -> Path:
        """Get cache file path for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.html"
    
    def _get_metadata_file(self, url: str) -> Path:
        """Get metadata file path for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.meta"
    
    def _is_cache_valid(self, url: str) -> bool:
        """Check if cached HTML is still valid."""
        meta_file = self._get_metadata_file(url)
        if not meta_file.exists():
            return False
        
        try:
            with open(meta_file, 'r') as f:
                metadata = json.load(f)
                cache_time = metadata.get('timestamp', 0)
                return time.time() - cache_time < self.ttl_seconds
        except Exception:
            return False
    
    def get_html(self, url: str) -> Optional[str]:
        """Get HTML from cache or fetch from web."""
        cache_file = self._get_cache_file(url)
        
        # Return cached HTML if valid
        if self._is_cache_valid(url) and cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logging.warning(f"Failed to read cached HTML: {e}")
        
        # Check if we've already tried and failed for this URL
        if self._is_failed_lookup_cached(url):
            logging.debug(f"Skipping previously failed URL: {url}")
            return None
        
        # Fetch from web with rate limiting
        return self._fetch_and_cache_html(url)
    
    def _fetch_and_cache_html(self, url: str) -> Optional[str]:
        """Fetch HTML from web and cache it."""
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logging.info(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'MARC-LSP-Server/1.0 (Educational/Library Tool)'
            })
            
            logging.info(f"Fetching HTML from: {url}")
            # Use shorter timeout for LSP responsiveness
            response = session.get(url, timeout=5)
            response.raise_for_status()
            
            self.last_request_time = time.time()
            
            # Cache the HTML and metadata
            html_content = response.text
            cache_file = self._get_cache_file(url)
            meta_file = self._get_metadata_file(url)
            
            # Save HTML
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save metadata
            metadata = {
                'url': url,
                'timestamp': time.time(),
                'status_code': response.status_code,
                'content_length': len(html_content)
            }
            with open(meta_file, 'w') as f:
                json.dump(metadata, f)
            
            logging.info(f"Cached HTML for {url} ({len(html_content)} bytes)")
            return html_content
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Failed to fetch HTML from {url}: {error_msg}")
            # Cache the failure to avoid repeated attempts
            self._cache_failed_lookup(url, error_msg)
            return None
    
    def get_parsed_tag(self, tag: str) -> Optional[TagInfo]:
        """Get parsed tag info from memory cache."""
        return self.parsed_cache.get(tag)
    
    def set_parsed_tag(self, tag: str, tag_info: TagInfo):
        """Store parsed tag info in memory cache."""
        self.parsed_cache[tag] = tag_info
    
    def _get_failed_cache_file(self, url: str) -> Path:
        """Get failed lookup cache file path for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.failed"
    
    def _is_failed_lookup_cached(self, url: str) -> bool:
        """Check if this URL has been tried and failed recently."""
        failed_file = self._get_failed_cache_file(url)
        if not failed_file.exists():
            return False
        
        try:
            with open(failed_file, 'r') as f:
                metadata = json.load(f)
                fail_time = metadata.get('timestamp', 0)
                # Cache failures for shorter time (24 hours)
                return time.time() - fail_time < (24 * 3600)
        except Exception:
            return False
    
    def _cache_failed_lookup(self, url: str, error_msg: str):
        """Cache that a URL lookup failed."""
        failed_file = self._get_failed_cache_file(url)
        try:
            metadata = {
                'url': url,
                'timestamp': time.time(),
                'error': error_msg
            }
            with open(failed_file, 'w') as f:
                json.dump(metadata, f)
            logging.debug(f"Cached failed lookup for {url}")
        except Exception as e:
            logging.warning(f"Failed to cache failed lookup: {e}")


class MarcDynamicLookup:
    """Dynamic lookup for MARC tag information from Library of Congress."""
    
    def __init__(self):
        self.bibliographic_base_url = "https://www.loc.gov/marc/bibliographic/"
        self.holdings_base_url = "https://www.loc.gov/marc/holdings/"
        self.html_cache = MarcHtmlCache()
    
    def get_tag_info(self, tag: str) -> Optional[TagInfo]:
        """Get information for a MARC tag."""
        # Check in-memory parsed cache first
        cached = self.html_cache.get_parsed_tag(tag)
        if cached:
            return cached
        
        # Get HTML (from cache or web) and parse
        try:
            tag_info = self._fetch_and_parse_tag_info(tag)
            if tag_info:
                self.html_cache.set_parsed_tag(tag, tag_info)
                return tag_info
        except Exception as e:
            logging.error(f"Failed to fetch tag {tag}: {e}")
        
        return None
    
    def _fetch_and_parse_tag_info(self, tag: str) -> Optional[TagInfo]:
        """Fetch HTML (from cache or web) and parse tag information."""
        # Construct URL based on tag
        url = self._get_tag_url(tag)
        if not url:
            return None
        
        # Get HTML from cache or web
        html_content = self.html_cache.get_html(url)
        if not html_content:
            return None
        
        # Parse the HTML
        return self._parse_tag_page(tag, html_content)
    
    def _get_tag_url(self, tag: str) -> Optional[str]:
        """Get the URL for a specific tag's documentation."""
        if not tag.isdigit() or len(tag) != 3:
            return None
        
        tag_num = int(tag)
        
        # Holdings record tags use holdings documentation
        if (tag_num >= 852 and tag_num <= 878) or tag_num >= 880:
            return f"{self.holdings_base_url}hd{tag}.html"
        else:
            # Bibliographic record tags use bibliographic documentation
            return f"{self.bibliographic_base_url}bd{tag}.html"
    
    def _parse_tag_page(self, tag: str, html: str) -> Optional[TagInfo]:
        """Parse tag information from HTML page."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract tag name and description
            name, description = self._extract_title_info(soup)
            if not name:
                return None
            
            # Extract indicators
            indicators = self._extract_indicators(soup)
            
            # Extract subfields
            subfields = self._extract_subfields(soup)
            
            # Check if repeatable
            repeatable = self._check_repeatable(soup)
            
            return TagInfo(
                tag=tag,
                name=name,
                description=description,
                repeatable=repeatable,
                indicators=indicators,
                subfields=subfields
            )
            
        except Exception as e:
            logging.error(f"Error parsing HTML for tag {tag}: {e}")
            return None
    
    def _extract_title_info(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """Extract tag name and description from page."""
        # Try to find the main heading
        heading = soup.find('h1')
        if not heading:
            return "", ""
        
        heading_text = heading.get_text().strip()
        
        # Parse pattern like "245 - Title Statement"
        match = re.match(r'(\d{3})\s*-\s*(.+)', heading_text)
        if match:
            name = match.group(2).strip()
            
            # Look for description in nearby text
            description = self._find_description(soup)
            if not description:
                description = name
                
            return name, description
        
        return "", ""
    
    def _find_description(self, soup: BeautifulSoup) -> str:
        """Find the field description."""
        # Look for common patterns in LC documentation
        for element in soup.find_all(['p', 'div']):
            text = element.get_text().strip()
            if text and len(text) > 20 and 'field' in text.lower():
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)
                if len(text) < 500:  # Reasonable description length
                    return text
        
        return ""
    
    def _extract_indicators(self, soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
        """Extract indicator information."""
        indicators = {}
        
        # Look for indicator sections
        for element in soup.find_all(['h2', 'h3', 'h4']):
            if 'indicator' in element.get_text().lower():
                indicator_num = self._extract_indicator_number(element.get_text())
                if indicator_num:
                    values = self._extract_indicator_values(element)
                    if values:
                        indicators[indicator_num] = values
        
        return indicators
    
    def _extract_indicator_number(self, text: str) -> Optional[str]:
        """Extract indicator number from heading text."""
        match = re.search(r'indicator\s*(\d)', text.lower())
        if match:
            return match.group(1)
        return None
    
    def _extract_indicator_values(self, element) -> Dict[str, str]:
        """Extract indicator values from the section following the heading."""
        values = {}
        
        # Look for the next elements that contain indicator values
        current = element.next_sibling
        while current and len(values) < 20:  # Reasonable limit
            if hasattr(current, 'find_all'):
                # Look for patterns like "0 - Description" or "# - Description"
                text = current.get_text()
                matches = re.findall(r'^([0-9#\s])\s*-\s*(.+)', text, re.MULTILINE)
                for match in matches:
                    key = match[0].strip()
                    desc = match[1].strip()
                    if key and desc:
                        values[key] = desc
            
            current = current.next_sibling
            if hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3', 'h4']:
                break
        
        return values
    
    def _extract_subfields(self, soup: BeautifulSoup) -> Dict[str, SubfieldInfo]:
        """Extract subfield information from LC HTML structure."""
        subfields = {}
        
        # First try to get basic subfield info from the subfields table
        basic_subfields = self._extract_basic_subfields(soup)
        subfields.update(basic_subfields)
        
        # Then try to get detailed descriptions from the detailed subfield sections
        detailed_subfields = self._extract_detailed_subfields(soup)
        
        # Merge detailed descriptions into basic subfields
        for code, detailed_info in detailed_subfields.items():
            if code in subfields:
                # Update with more detailed description
                subfields[code].description = detailed_info.description
            else:
                # Add new subfield if not found in basic list
                subfields[code] = detailed_info
        
        return subfields
    
    def _extract_basic_subfields(self, soup: BeautifulSoup) -> Dict[str, SubfieldInfo]:
        """Extract basic subfield info from the subfields table."""
        subfields = {}
        
        # Look for table with class="subfields"
        subfield_table = soup.find('table', class_='subfields')
        if subfield_table:
            # Find all list items with subfield codes
            for li in subfield_table.find_all('li'):
                text = li.get_text().strip()
                # Match pattern like "$a - Title (NR)" or "$k - Form (R)"
                match = re.match(r'\$([a-z0-9])\s*-\s*([^(]+)(?:\s*\(([NR]+)\))?', text)
                if match:
                    code = match.group(1).lower()
                    name = match.group(2).strip()
                    repeatability = match.group(3) or ''
                    repeatable = 'R' in repeatability
                    
                    subfields[code] = SubfieldInfo(
                        code=code,
                        name=name,
                        description=name,  # Will be updated with detailed description if available
                        repeatable=repeatable
                    )
        else:
            # Alternative format: look for table cells with subfield info separated by <br>
            subfields.update(self._extract_subfields_from_table_cells(soup))
        
        return subfields
    
    def _extract_subfields_from_table_cells(self, soup: BeautifulSoup) -> Dict[str, SubfieldInfo]:
        """Extract subfield information from table cells with <br> separated content."""
        subfields = {}
        
        # Look through all table cells for subfield patterns
        for td in soup.find_all('td'):
            # Check if this cell contains subfield information
            if '$' in td.get_text() and re.search(r'\$[a-z0-9]\s*-', td.get_text()):
                # Split content by <br> tags
                parts = []
                for element in td.children:
                    if element.name == 'br':
                        continue
                    elif hasattr(element, 'get_text'):
                        parts.append(element.get_text().strip())
                    elif isinstance(element, str):
                        parts.append(element.strip())
                
                # Join and split by line breaks in text
                text = ' '.join(parts)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # Also try splitting the HTML content directly
                html_content = str(td)
                if '<br' in html_content:
                    # Split by <br> tags and clean up
                    br_parts = re.split(r'<br\s*/?>', html_content)
                    for part in br_parts:
                        # Remove HTML tags and get clean text
                        clean_part = BeautifulSoup(part, 'html.parser').get_text().strip()
                        if clean_part and '$' in clean_part:
                            lines.append(clean_part)
                
                # Parse each line for subfield information
                for line in lines:
                    if not line or not line.startswith('$'):
                        continue
                    
                    # Match pattern like "$a - System control number (NR)"
                    match = re.match(r'\$([a-z0-9])\s*-\s*([^(]+)(?:\s*\(([NR]+)\))?', line)
                    if match:
                        code = match.group(1).lower()
                        name = match.group(2).strip()
                        repeatability = match.group(3) or ''
                        repeatable = 'R' in repeatability
                        
                        subfields[code] = SubfieldInfo(
                            code=code,
                            name=name,
                            description=name,
                            repeatable=repeatable
                        )
        
        return subfields
    
    def _extract_detailed_subfields(self, soup: BeautifulSoup) -> Dict[str, SubfieldInfo]:
        """Extract detailed subfield descriptions from the detailed sections."""
        subfields = {}
        
        # Look for div with class="subfields" containing detailed descriptions
        subfields_div = soup.find('div', class_='subfields')
        if not subfields_div:
            return subfields
        
        # Find all subfield sections with class="subfield"
        for subfield_div in subfields_div.find_all('div', class_='subfield'):
            # Look for the label paragraph with the subfield code
            label_p = subfield_div.find('p', class_='label')
            if not label_p:
                continue
            
            label_text = label_p.get_text().strip()
            # Match pattern like "$a - Title" 
            match = re.match(r'\$([a-z0-9])\s*-\s*(.+)', label_text)
            if not match:
                continue
            
            code = match.group(1).lower()
            name = match.group(2).strip()
            
            # Extract the description from the following div or paragraphs
            description = self._extract_subfield_description(subfield_div, label_p)
            
            subfields[code] = SubfieldInfo(
                code=code,
                name=name,
                description=description or name,
                repeatable=False  # This will be set from basic info if available
            )
        
        return subfields
    
    def _extract_subfield_description(self, subfield_div, label_p) -> str:
        """Extract the description text for a subfield."""
        # Look for the next div after the label that contains the description
        desc_div = label_p.find_next_sibling('div')
        if not desc_div:
            return ""
        
        # Get all paragraph text, but skip examples
        description_parts = []
        for p in desc_div.find_all('p', recursive=False):
            # Skip if this paragraph is inside an example div
            if p.find_parent('div', class_='example'):
                continue
            
            text = p.get_text().strip()
            if text and not text.startswith('245 '):  # Skip MARC examples
                description_parts.append(text)
        
        # Join the parts and clean up
        description = ' '.join(description_parts)
        # Remove extra whitespace and normalize
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Limit length for hover display
        if len(description) > 300:
            # Find a good break point
            if '. ' in description[:300]:
                description = description[:description.find('. ', 200) + 1]
            else:
                description = description[:300] + '...'
        
        return description
    
    def _check_repeatable(self, soup: BeautifulSoup) -> bool:
        """Check if the field is repeatable."""
        text = soup.get_text().lower()
        return 'repeatable' in text and 'not repeatable' not in text


# Global instance
marc_lookup = MarcDynamicLookup()