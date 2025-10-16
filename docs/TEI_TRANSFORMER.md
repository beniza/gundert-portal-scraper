# TEI XML Transformer Documentation

## Overview

The TEI (Text Encoding Initiative) transformer extracts and enhances the embedded TEI markup from OpenDigi manuscripts, producing valid TEI P5 XML output suitable for digital humanities scholarship and long-term preservation.

## Features

### TEI P5 Compliance
- ✅ **Valid TEI P5** - Proper namespace (`http://www.tei-c.org/ns/1.0`)
- ✅ **Complete TEI Header** - Enhanced metadata with publication, encoding, and revision information
- ✅ **Source Document** - Preserves original `<sourceDoc>` structure with `<surface>` elements for each page
- ✅ **Unicode Preservation** - Maintains Malayalam and other Indic scripts correctly
- ✅ **Structural Integrity** - Preserves paragraphs (`<p>`), line breaks (`<lb>`), and page organization

### Enhanced Metadata
The transformer enriches the minimal TEI header from the source with:
- **File Description**: Title, responsibility statement, publication details, source description
- **Encoding Description**: Project description and encoding practices
- **Profile Description**: Language identification (Malayalam/ml by default)
- **Revision Description**: Generation date and transformation history

### Validation
Built-in validation checks:
- XML well-formedness
- Required TEI elements present
- Proper namespace declaration
- Structural completeness

### Statistics
Provides detailed transformation statistics:
- Total pages processed
- Paragraph count
- Line break count
- Character and word counts
- Page number listing

## Usage

### CLI Usage

#### Extract with TEI Output
```bash
# Extract full manuscript as TEI XML
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a \
  --formats tei --output ./output/psalms

# Extract specific page range
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a \
  --formats tei --start-page 1 --end-page 20 --output ./output/psalms_sample

# Multiple formats (JSON interim, TEI final)
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a \
  --formats json,tei,usfm --output ./output/complete
```

#### Transform Existing Cache to TEI
```bash
# Transform from cache (requires prior extraction)
uv run gundert-scraper transform output/GaXXXIV5a.json --format tei \
  --output output/GaXXXIV5a.xml
```

### Python API Usage

```python
from pathlib import Path
from gundert_portal_scraper.core.cache import RawContentCache
from gundert_portal_scraper.transformations import TEITransformer

# Load cached content
cache = RawContentCache()
cached_content = cache.load('GaXXXIV5a')

# Create transformer
transformer = TEITransformer()

# Check compatibility
if transformer.is_compatible(cached_content):
    # Transform to TEI
    result = transformer.transform(
        cached_content,
        Path('output/psalms.xml'),
        page_range=(1, 20)  # Optional: limit to specific pages
    )
    
    # Check results
    print(f"Success: {result['success']}")
    print(f"Valid TEI: {result['validation']['valid']}")
    print(f"Pages: {result['statistics']['total_pages']}")
    print(f"Paragraphs: {result['statistics']['total_paragraphs']}")
    print(f"Words: {result['statistics']['total_words']}")
    
    # Validation details
    for check in result['validation']['checks']:
        print(f"{check['status']}: {check['check']} - {check['message']}")
```

## Output Structure

### TEI XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Saṅkīrttanaṅṅaḷ</title>
        <respStmt>
          <resp>Digitization</resp>
          <name>Universitätsbibliothek Tübingen</name>
        </respStmt>
      </titleStmt>
      <publicationStmt>
        <publisher>OpenDigi - University of Tübingen</publisher>
        <pubPlace>Tübingen, Germany</pubPlace>
        <date when="2025-10-16">2025</date>
        <availability>
          <p>This work is protected by copyright...</p>
        </availability>
        <idno type="OpenDigi">GaXXXIV5a</idno>
      </publicationStmt>
      <sourceDesc>
        <p>Digitized manuscript from Gundert Collection (ID: GaXXXIV5a)</p>
        <bibl/>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <projectDesc>
        <p>Digital edition created from manuscript digitization...</p>
      </projectDesc>
    </encodingDesc>
    <profileDesc>
      <langUsage>
        <language ident="ml">Malayalam</language>
      </langUsage>
    </profileDesc>
    <revisionDesc>
      <change when="2025-10-16">TEI file generated...</change>
    </revisionDesc>
  </teiHeader>
  
  <sourceDoc rend="lang(ml)">
    <surface n="7" type="scan">
      <p>സങ്കീൎത്തനങ്ങൾ.</p>
      <p>1 ദുഷ്ടരുടേ അഭിപ്രായത്തിൽ നടക്കാതേയും
        <lb/>പാപികളുടേ വഴിയിൽ നില്ക്കാതേയും
        <lb/>പരിഹാസക്കാരുടെ ഇരിപ്പിൽ ഇരിക്കാതേയും,
      </p>
      <!-- More content -->
    </surface>
    <surface n="8" type="scan">
      <!-- Page 8 content -->
    </surface>
  </sourceDoc>
</TEI>
```

### Key TEI Elements

- **`<TEI>`** - Root element with TEI namespace
- **`<teiHeader>`** - Comprehensive metadata about the digital edition
- **`<sourceDoc>`** - Contains the manuscript content in source-oriented encoding
- **`<surface n="X">`** - Each manuscript page (identified by page number in `n` attribute)
- **`<p>`** - Paragraphs of text
- **`<lb/>`** - Line breaks within paragraphs (preserves manuscript line structure)

## Validation Results

The transformer performs automatic validation:

```
✓ XML parsing: Valid XML
✓ Root TEI element: TEI element found
✓ TEI Header: teiHeader element found
✓ File Description: fileDesc element found
✓ Title Statement: titleStmt element found
✓ Publication Statement: publicationStmt element found
✓ Source Description: sourceDesc element found
✓ Source Document: sourceDoc element found
✓ TEI namespace: Correct namespace: http://www.tei-c.org/ns/1.0
```

## Example Output (Psalms 1)

### Malayalam Content Preserved
```xml
<surface class="hidden" n="7" type="scan">
  <p>സങ്കീൎത്തനങ്ങൾ.</p>
  <p>ഒന്നാം കാണ്ഡം, ൧- ൪൧:</p>
  <p>ദാവിദിന്റേ യഹോവാകീൎത്തനങ്ങൾ.</p>
  <p>൧. സങ്കീൎത്തനം.</p>
  <p>ദേവഭക്തരേ അനുഗ്രഹവും (൪) ദുഷ്ടരേ നിഗ്രഹവും.</p>
  <p>1 ദുഷ്ടരുടേ അഭിപ്രായത്തിൽ നടക്കാതേയും
    <lb/>പാപികളുടേ വഴിയിൽ നില്ക്കാതേയും
    <lb/>പരിഹാസക്കാരുടെ ഇരിപ്പിൽ ഇരിക്കാതേയും,
  </p>
  <p>2 യഹോവയുടേ ധൎമ്മോപദേശത്തിൽ അത്രേ ഇഷ്ടം ഉണ്ടായി
    <lb/>അവന്റേ വേദത്തിൽ രാപ്പകൽ ധ്യാനിച്ചും കൊള്ളുന്ന പുരുഷൻ ധന്യൻ.
  </p>
</surface>
```

## Use Cases

### Digital Humanities Research
- **Scholarly Editions** - TEI P5 is the standard for digital critical editions
- **Text Analysis** - Compatible with TEI-aware tools (XSLT, XQuery, TEI Publisher)
- **Long-term Preservation** - TEI ensures future accessibility and machine-readability
- **Interoperability** - Exchange with other digital humanities projects

### Manuscript Studies
- **Page-level Preservation** - `<surface>` elements maintain original pagination
- **Line-level Accuracy** - `<lb/>` elements preserve manuscript line breaks
- **Structural Analysis** - Paragraph organization retained from source
- **Image Alignment** - Page numbers (`n` attribute) correspond to IIIF image URLs

### Publishing Workflows
- **Print Generation** - Transform TEI to PDF/print layouts
- **Web Publishing** - Use TEI Publisher or custom XSLT for web display
- **E-book Creation** - Convert TEI to EPUB or other e-book formats
- **Database Import** - Load into BaseX, eXist-db, or other XML databases

## Technical Details

### Requirements
- **Input**: Cached HTML content with embedded TEI (from OpenDigi)
- **Dependencies**: BeautifulSoup4 for XML parsing
- **Output**: Valid TEI P5 XML with UTF-8 encoding

### Validation
The transformer validates:
1. **XML Well-formedness** - Proper XML syntax
2. **Required Elements** - All mandatory TEI elements present
3. **Namespace** - Correct TEI P5 namespace declaration
4. **Structure** - teiHeader and sourceDoc properly nested

### Compatibility
Compatible with:
- TEI P5 specification (http://www.tei-c.org/P5/)
- TEI Guidelines (https://tei-c.org/guidelines/)
- Oxygen XML Editor (with TEI framework)
- TEI Publisher
- BaseX, eXist-db XML databases

## Statistics Example

Transformation of Psalms pages 5-10:
```
Total pages: 6
Total paragraphs: 73
Total line breaks: 142
Total characters: 14,523
Total words: 1,847
Page numbers: [5, 6, 7, 8, 9, 10]
```

## Troubleshooting

### "No cached content found"
**Problem**: TEI transformation requires the original cached HTML
**Solution**: Run extract command first to download and cache the manuscript

```bash
# First: Extract and cache
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a

# Then: Transform to TEI
uv run gundert-scraper transform output/GaXXXIV5a.json --format tei
```

### "Content does not contain valid TEI structure"
**Problem**: Source content doesn't have embedded TEI markup
**Solution**: This transformer is specifically for OpenDigi manuscripts with TEI. Other sources may require different transformation approaches.

### Validation Warnings
**Minor warnings** (e.g., namespace issues) don't prevent successful transformation. The output is still valid TEI, but may benefit from manual refinement for specific scholarly needs.

## Best Practices

1. **Always keep cache** - Cache contains the original TEI structure needed for transformation
2. **Validate output** - Use TEI tools (Oxygen XML, jing) to validate against TEI schema if strict compliance needed
3. **Preserve page ranges** - Use `--start-page` and `--end-page` for focused extractions
4. **Combine with other formats** - Generate TEI alongside USFM for different use cases
5. **Document provenance** - TEI header includes transformation date and source information automatically

## Related Documentation

- [USFM_TRANSFORMER.md](USFM_TRANSFORMER.md) - USFM format transformation
- [CACHE_MANAGEMENT.md](CACHE_MANAGEMENT.md) - Cache usage and safety
- [OUTPUT_MANAGEMENT.md](OUTPUT_MANAGEMENT.md) - Output organization

## References

- **TEI Consortium**: https://tei-c.org/
- **TEI P5 Guidelines**: https://tei-c.org/guidelines/P5/
- **TEI by Example**: https://teibyexample.org/
- **OpenDigi Platform**: https://opendigi.ub.uni-tuebingen.de/
