# Changelog

All notable changes to the Gundert Portal Scraper project.

## [0.1.0] - 2025-01-16

### Added
- Two-phase extraction architecture (download → process)
- Smart caching system for downloaded manuscripts (771KB for 201 pages)
- TEI XML parsing from embedded OpenDigi content
- Image URL generation using IIIF API pattern
- Line-level content preservation
- CLI with `extract` command using Click and Rich
- Pydantic data models for type-safe data handling
- Selenium-based SPA navigation
- BeautifulSoup-based content extraction
- Statistics and success rate tracking

### Architecture
- `src/gundert_portal_scraper/core/` - Book identification, WebDriver, caching
- `src/gundert_portal_scraper/extraction/` - Two-phase scraper implementation
- `src/gundert_portal_scraper/storage/` - Pydantic schemas
- `src/gundert_portal_scraper/cli/` - Command-line interface

### Validated
- ✅ 100% extraction success rate on Malayalam Psalms (GaXXXIV5a)
- ✅ Tested on pages 1-20, with various page ranges
- ✅ Image URLs verified accessible (HTTP 200)
- ✅ Cache system working (instant reload)
- ✅ Unicode Malayalam text preserved correctly

### Documentation
- Complete README with usage examples
- LLM recreation guide in `project_reconstruction_guide.json`
- Implementation summary in `docs/IMPLEMENTATION_SUMMARY.md`

## [Future Releases]

### Planned Features
- USFM transformer for biblical texts
- TEI XML output format
- DOCX generation
- Batch processing capabilities
- Additional validation tests
- Support for more manuscript types
