# USFM Transformer

The USFM (Unified Standard Format Marker) transformer converts extracted JSON content from Malayalam biblical manuscripts into standard USFM format for Bible translation projects.

## Features

- ✅ **Malayalam Digit Support** - Converts Malayalam numerals (൧, ൨, ൩...) to Arabic (1, 2, 3...)
- ✅ **Verse Detection** - Automatically identifies verse numbers at the start of lines
- ✅ **Psalm/Chapter Detection** - Recognizes psalm headings and creates chapter markers
- ✅ **Header Filtering** - Removes page headers, footers, and non-content lines
- ✅ **Multi-line Verses** - Handles verses that span multiple lines
- ✅ **Descriptive Titles** - Preserves psalm titles and musical notations as `\d` markers

## USFM Markers Generated

| Marker | Purpose | Example |
|--------|---------|---------|
| `\id` | Book identification | `\id PSA Malayalam: Gundert's Translation (1880)` |
| `\h` | Running header | `\h സങ്കീർത്തനങ്ങൾ` |
| `\toc1` | Long table of contents | `\toc1 സങ്കീർത്തനങ്ങൾ` |
| `\toc2` | Short table of contents | `\toc2 സങ്കീർത്തനങ്ങൾ` |
| `\toc3` | Abbreviation | `\toc3 സങ്കീ` |
| `\mt1` | Main title | `\mt1 സങ്കീർത്തനങ്ങൾ` |
| `\c` | Chapter number | `\c 1` |
| `\d` | Descriptive title | `\d ദാവിദിന്റെതു; ൨ ശമു. ൭` |
| `\v` | Verse number and text | `\v 1 ദുഷ്ടരുടേ അഭിപ്രായത്തിൽ...` |

## Usage

### Command Line

```bash
# Transform single JSON file to USFM
uv run gundert-scraper transform output/GaXXXIV5a.json --format usfm --output output/psalms.usfm

# Let it auto-generate output filename
uv run gundert-scraper transform output/GaXXXIV5a.json --format usfm
```

### Python API

```python
from gundert_portal_scraper.transformations import USFMTransformer

# Transform JSON to USFM
transformer = USFMTransformer()
usfm_content = transformer.transform('output/GaXXXIV5a.json', 'output/psalms.usfm')

# Transform directory of JSON files
transformer.transform_directory('output/', 'output/usfm/')
```

## Example Output

```usfm
\id PSA Malayalam: Gundert's Translation (1880)
\usfm 3.0
\ide UTF-8
\h സങ്കീർത്തനങ്ങൾ
\toc1 സങ്കീർത്തനങ്ങൾ
\toc2 സങ്കീർത്തനങ്ങൾ
\toc3 സങ്കീ
\mt1 സങ്കീർത്തനങ്ങൾ

\rem Extracted from: GaXXXIV5a
\rem Extraction date: 2025-10-16T07:05:08.623719
\rem Total pages: 201

\c 1
\v 1 ദുഷ്ടരുടേ അഭിപ്രായത്തിൽ നടക്കാതേയും പാപികളുടേ വഴിയിൽ നില്ക്കാതേയും പരിഹാസക്കാരുടെ ഇരിപ്പിൽ ഇരിക്കാതേയും,
\v 2 യഹോവയുടേ ധൎമ്മോപദേശത്തിൽ അത്രേ ഇഷ്ടം ഉണ്ടായി അവന്റേ വേദത്തിൽ രാപ്പകൽ ധ്യാനിച്ചും കൊള്ളുന്ന പുരുഷൻ ധന്യൻ.
\v 3 ആയവൻ നീൎത്തോടുകൾ്ക്കരികിൽ നട്ടതായി തല്ക്കാലത്തു ഫലം കാച്ചും ഇല വാടാതേയും ഉള്ള മരത്തോട് ഒക്കും. അവൻ ചെയ്യുന്നത് ഒക്കയും സാധിക്കും.
```

## Tested On

- **Book**: Malayalam Psalms (GaXXXIV5a)
- **Source**: Gundert's Translation (1880)
- **Pages**: 201 pages
- **Result**: Successfully transformed Psalms 1-10 with 156 verses

## Known Limitations

1. **Psalm Titles** - Some descriptive titles may be split across multiple lines
2. **Cross-references** - Biblical cross-references (e.g., "൨ ശമു. ൭") are preserved as-is
3. **Selah Markers** - Musical notations like "(സേല)" are included in verse text
4. **Page Numbers** - Some page markers may still appear in output

## Future Improvements

- [ ] Better handling of psalm superscriptions
- [ ] Separate cross-references into `\x` markers
- [ ] Convert Selah to `\qs` (selah) markers
- [ ] Add paragraph markers (`\p`, `\q`) for poetry structure
- [ ] Support for parallel passages
- [ ] USFM validation

## USFM Specification

This transformer follows [USFM 3.0 specification](https://ubsicap.github.io/usfm/). For questions about specific markers or formatting, refer to the official USFM documentation.
