# MARC LSP Server

A Language Server Protocol implementation for MARC MRK (Machine-Readable Cataloging) files with dynamic documentation lookup from the Library of Congress.

## Features

- **Dynamic Documentation Lookup**: Real-time fetching of MARC tag and subfield definitions from Library of Congress website
- **Intelligent Caching**: HTML cache system with automatic cache invalidation for performance
- **Comprehensive Hover Support**: Detailed hover information for MARC tags, subfields, indicators, and fixed field positions
- **Fixed Field Analysis**: Character-by-character definitions for MARC fixed fields (008, etc.)
- **MRK Format Parsing**: Robust parser for Machine-Readable format with error handling
- **LSP Integration**: Full Language Server Protocol implementation for editor integration

## Installation

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure your editor to use the LSP server with `.mrk` files.

## Usage

1. Start the LSP server:
   ```bash
   python marc_lsp_server.py
   ```

2. Configure your editor to connect to the LSP server for `.mrk` files

3. Open any MARC record in MRK format and get:
   - Dynamic hover documentation for tags and subfields
   - Fixed field position analysis for 008 fields
   - Real-time MARC format validation

## Testing

The project includes comprehensive test files for development:
- `test_record.mrk`: Sample MARC record for testing
- Various `test_*.py` files for specific functionality testing

## Architecture

### Core Modules

- **`marc_lsp_server.py`**: Main LSP server implementation with hover and completion support
- **`marc_lookup.py`**: Dynamic documentation fetching from Library of Congress website
- **`marc_adapter.py`**: Adapter layer between lookup system and LSP server format
- **`marc_fixed_fields.py`**: Character-by-character definitions for MARC fixed fields
- **`mrk_parser.py`**: MRK format parser with comprehensive error handling
- **`marc_tags.py`**: Static MARC tag database for fallback support

### Caching System

- **HTML Cache**: Stores fetched documentation pages with metadata
- **Pickle Cache**: Serialized cache for parsed MARC data
- **Automatic Invalidation**: Cache entries expire and refresh automatically

## Development

The system is designed for extensibility:

1. **Add new fixed field definitions** in `marc_fixed_fields.py`
2. **Enhance parsing logic** in `mrk_parser.py` 
3. **Extend LSP capabilities** in `marc_lsp_server.py`
4. **Improve lookup algorithms** in `marc_lookup.py`

The dynamic lookup system automatically handles new MARC tags without code changes.