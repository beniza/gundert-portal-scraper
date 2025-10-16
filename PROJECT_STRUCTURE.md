# Project Structure

```
gundert-bible/
│
├── src/gundert_portal_scraper/     # Main package
│   ├── __init__.py
│   ├── core/                       # Core functionality
│   │   ├── __init__.py
│   │   ├── book_identifier.py      # URL parsing and book ID extraction
│   │   ├── connector.py            # Selenium WebDriver management
│   │   └── cache.py                # Content caching system
│   ├── extraction/                 # Content extraction
│   │   ├── __init__.py
│   │   ├── content_scraper.py      # Legacy single-phase scraper
│   │   └── two_phase_scraper.py    # Current two-phase implementation
│   ├── storage/                    # Data models
│   │   ├── __init__.py
│   │   └── schemas.py              # Pydantic data validation models
│   └── cli/                        # Command-line interface
│       ├── __init__.py
│       └── commands.py             # Click commands with Rich output
│
├── docs/                           # Documentation
│   ├── README.md                   # Documentation index
│   ├── IMPLEMENTATION_SUMMARY.md   # Technical details
│   └── archived/                   # Historical files
│       ├── conversation_backup_oct16_2025.md
│       ├── next_session_notes.md
│       └── essential_backup/       # Project backups
│
├── cache/                          # Downloaded manuscript cache (gitignored)
│   └── GaXXXIV5a.json             # 771KB cached content (201 pages)
│
├── output/                         # Extracted JSON files (gitignored)
│   ├── psalms_sample/              # Sample extractions
│   └── psalms_transformed/         # Full book extractions
│
├── .git/                           # Git repository
├── .venv/                          # Virtual environment (gitignored)
├── .gitignore                      # Git ignore patterns
├── pyproject.toml                  # Project configuration and dependencies
├── uv.lock                         # Locked dependencies
├── README.md                       # Main project documentation
├── CHANGELOG.md                    # Version history
└── project_reconstruction_guide.json  # LLM recreation instructions
```

## Key Files

### Configuration
- **pyproject.toml** - Project metadata, dependencies, CLI entry points
- **uv.lock** - Locked dependency versions

### Documentation
- **README.md** - Quick start guide and project overview
- **CHANGELOG.md** - Version history and features
- **project_reconstruction_guide.json** - Complete instructions for LLM recreation
- **docs/IMPLEMENTATION_SUMMARY.md** - Technical implementation details

### Source Code
- **src/gundert_portal_scraper/** - Main package with modular architecture
  - `core/` - Low-level functionality (URLs, connections, caching)
  - `extraction/` - High-level scraping logic
  - `storage/` - Data models and schemas
  - `cli/` - Command-line interface

### Generated Files (gitignored)
- **cache/** - Downloaded manuscript content for quick processing
- **output/** - Extracted JSON with line-level structure

## Dependencies

### Core
- **selenium** 4.27.1 - WebDriver for SPA navigation
- **beautifulsoup4** - HTML/TEI XML parsing
- **pydantic** 2.0+ - Data validation and models
- **click** 8.3+ - CLI framework
- **rich** 14.2+ - Terminal formatting

### Development
- **uv** - Fast Python package manager
- **python** 3.10+ - Required Python version
