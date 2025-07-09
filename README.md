# MARC LSP Server

A Language Server Protocol implementation for MARC MRK (Machine-Readable Cataloging) files.

## Features

- **Syntax Highlighting**: Semantic tokens for MARC tags, indicators, subfields, and content
- **Hover Documentation**: Detailed information about MARC tags and subfields from Library of Congress documentation
- **Auto-completion**: Smart completion for MARC tags and valid subfield codes
- **Validation**: Real-time validation of MARC structure and field formats
- **Error Detection**: Highlights invalid tags, subfields, and structural issues

## Installation

1. Install dependencies:
   ```bash
   cd /Users/rvanbron/test-lsp
   uv sync
   ```

2. The LSP server is already configured in your Emacs init.el file to work with `.mrk` files.

## Usage

1. Open any `.mrk` file in Emacs
2. The LSP server will automatically start and provide:
   - Syntax highlighting for MARC elements
   - Hover documentation when you hover over tags or subfields
   - Auto-completion when typing `=` (for tags) or `$` (for subfields)
   - Real-time validation and error highlighting

## Testing

Use the included `test_record.mrk` file to test all LSP features:

```bash
emacs test_record.mrk
```

## MARC Format Support

The LSP server supports standard MARC bibliographic format including:

- **Leader** (=LDR): Record header information
- **Control Fields** (001-009): System control numbers and coded data
- **Data Fields** (010-999): Bibliographic data with indicators and subfields

### Common Tags Supported

- **1XX**: Main entry fields (100, 110, 111)
- **245**: Title statement
- **250**: Edition statement  
- **260**: Publication information
- **300**: Physical description
- **4XX**: Series statements
- **5XX**: Note fields
- **6XX**: Subject access fields
- **7XX**: Added entry fields
- **856**: Electronic location and access

## Architecture

- `marc_lsp_server.py`: Main LSP server implementation
- `mrk_parser.py`: MRK format parser and validator
- `marc_tags.py`: MARC tag definitions and documentation database

## Development

To extend the tag database or add new features:

1. Update `marc_tags.py` to add new tag definitions
2. Modify `mrk_parser.py` for parsing improvements
3. Enhance `marc_lsp_server.py` for new LSP capabilities