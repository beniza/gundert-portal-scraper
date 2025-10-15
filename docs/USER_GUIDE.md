# User Guide 📖

Complete guide to using the Gundert Portal Scraper for extracting, transforming, and validating Malayalam manuscript content.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Command Line Interface](#command-line-interface)
3. [Common Workflows](#common-workflows)
4. [Output Formats](#output-formats)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

Before using the Gundert Portal Scraper, ensure you have:

- **Python 3.10 or higher**
- **Chrome or Chromium browser** (for dynamic content extraction)
- **Stable internet connection** (for accessing digital manuscript portals)

### Basic Commands Overview

```bash
# Show all available commands
gundert-scraper --help

# Get information about supported formats
gundert-scraper info --show-formats

# Extract content from a manuscript
gundert-scraper extract <URL> --formats usfm,docx --output ./results

# Validate generated content
gundert-scraper validate file.usfm --detailed

# Transform existing data to different formats  
gundert-scraper transform book.json --formats tei_xml
```

## Command Line Interface

### Global Options

All commands support these global flags:

```bash
gundert-scraper [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]

Global Options:
  -v, --verbose     Enable detailed output and debugging information
  -q, --quiet       Suppress all output except errors
  --no-banner       Hide the application banner
  --help           Show help message and exit
```

### Extract Command

Extract Malayalam content from digital manuscript portals.

#### Basic Syntax
```bash
gundert-scraper extract <URL> [OPTIONS]
```

#### Options
- `-o, --output PATH` - Output directory for extracted content
- `-s, --start-page INTEGER` - Starting page number (default: 1)
- `-e, --end-page INTEGER` - Ending page number (default: extract all)
- `-b, --batch-size INTEGER` - Number of pages to process at once (default: 10)
- `-f, --formats TEXT` - Comma-separated output formats
- `--validate/--no-validate` - Enable/disable content validation (default: enabled)
- `--preserve-images` - Download and preserve page images
- `--book-id TEXT` - Override auto-detected book ID

#### Examples

**Basic Extraction:**
```bash
# Extract first 10 pages to USFM format
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --start-page 1 --end-page 10 --formats usfm --output ./psalms
```

**Multi-Format Extraction:**
```bash
# Extract to multiple formats with validation
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --formats usfm,tei_xml,docx --output ./complete_extraction --validate
```

**Large Book Extraction:**
```bash
# Extract entire book with optimized batch processing
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --batch-size 20 --formats usfm --output ./full_book --preserve-images
```

### Transform Command

Convert saved content between different formats.

#### Basic Syntax
```bash
gundert-scraper transform <INPUT_FILE> [OPTIONS]
```

#### Options
- `-f, --formats TEXT` - Target formats (required)
- `-o, --output PATH` - Output directory
- `--validate/--no-validate` - Validate transformed content

#### Examples

**Single Format Transformation:**
```bash
# Convert JSON data to USFM
gundert-scraper transform book_data.json --formats usfm --output ./usfm_output
```

**Multiple Format Generation:**
```bash
# Generate academic and publication formats
gundert-scraper transform book_data.json \
  --formats tei_xml,bibleml,docx --output ./multi_format --validate
```

### Validate Command

Check content files for format compliance and quality.

#### Basic Syntax
```bash
gundert-scraper validate <FILE>... [OPTIONS]
```

#### Options
- `-f, --format FORMAT` - Specify file format (auto-detected if not provided)
- `-d, --detailed` - Show detailed validation report with suggestions

#### Examples

**Single File Validation:**
```bash
# Validate USFM file with detailed report
gundert-scraper validate psalms.usfm --format usfm --detailed
```

**Batch Validation:**
```bash
# Validate multiple files
gundert-scraper validate *.usfm *.xml --detailed
```

**Format-Specific Validation:**
```bash
# Validate TEI XML for academic compliance
gundert-scraper validate manuscript.xml --format tei_xml --detailed
```

### Batch Command

Process multiple book files efficiently.

#### Basic Syntax
```bash
gundert-scraper batch <FILE>... [OPTIONS]
```

#### Options
- `-f, --formats TEXT` - Output formats for all files
- `-o, --output PATH` - Base output directory
- `-p, --parallel INTEGER` - Number of parallel processes (default: 1)
- `--validate/--no-validate` - Validate all generated content

#### Examples

**Parallel Processing:**
```bash
# Process multiple books in parallel
gundert-scraper batch book1.json book2.json book3.json \
  --formats usfm,docx --parallel 3 --output ./batch_results
```

### Info Command

Display system information and capabilities.

#### Options
- `--show-formats` - List supported transformation formats
- `--show-validators` - List available content validators
- `--system-info` - Show system and dependency information

#### Examples

**Check Available Formats:**
```bash
gundert-scraper info --show-formats --show-validators
```

**System Diagnostics:**
```bash
gundert-scraper info --system-info
```

## Common Workflows

### Workflow 1: Academic Research Project

**Goal**: Extract Malayalam psalms for digital humanities research

```bash
# Step 1: Extract content with academic formats
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --formats tei_xml,parabible_json --output ./psalms_research --validate

# Step 2: Validate academic compliance
gundert-scraper validate psalms_research/*.xml --format tei_xml --detailed

# Step 3: Generate additional formats if needed
gundert-scraper transform psalms_research/psalms_data.json \
  --formats docx --output ./publication_draft
```

### Workflow 2: Bible Translation Project

**Goal**: Convert historical text to modern translation format

```bash
# Step 1: Extract to USFM for translation work
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --formats usfm --output ./translation_base --book-id PSA

# Step 2: Validate USFM compliance
gundert-scraper validate translation_base/*.usfm --detailed

# Step 3: Generate Word documents for review
gundert-scraper transform translation_base/book_data.json \
  --formats docx --output ./review_documents
```

### Workflow 3: Digital Preservation

**Goal**: Complete digitization with multiple backup formats

```bash
# Step 1: Full extraction with images
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --formats usfm,tei_xml,parabible_json --preserve-images \
  --output ./preservation_archive

# Step 2: Generate all available formats
gundert-scraper transform preservation_archive/book_data.json \
  --formats bibleml,docx --output ./preservation_archive

# Step 3: Comprehensive validation
gundert-scraper validate preservation_archive/* --detailed
```

### Workflow 4: Batch Processing Multiple Books

**Goal**: Process an entire collection efficiently

```bash
# Step 1: Extract multiple books (run separately for each URL)
for book in book1_url book2_url book3_url; do
  gundert-scraper extract "$book" --formats usfm,json --output "./books/$(basename $book)"
done

# Step 2: Batch transform all extracted data
gundert-scraper batch books/*/book_data.json \
  --formats tei_xml,docx --parallel 4 --output ./collection_output

# Step 3: Validate entire collection
gundert-scraper validate collection_output/**/*.usfm --detailed
```

## Output Formats

### USFM (Unified Standard Format Marker)

**Use Case**: Bible translation and publishing
**Extension**: `.usfm`
**Features**:
- Standard biblical text markup
- Verse and chapter numbering
- Poetry and prose formatting
- Cross-references and footnotes

**Example Output:**
```usfm
\id PSA Malayalam Psalms - Gundert 1881
\h സങ്കീർത്തനങ്ങൾ
\mt1 സങ്കീർത്തനങ്ങൾ

\c 1
\p
\v 1 ആശീർവാദമുള്ളവൻ ദുഷ്ടന്മാരുടെ ആലോചനയിൽ നടക്കാതെ...
```

### TEI XML (Text Encoding Initiative)

**Use Case**: Digital humanities and academic research
**Extension**: `.xml`
**Features**:
- Scholarly text encoding standards
- Manuscript metadata preservation
- Editorial annotations support
- Academic citation compliance

**Key Elements:**
```xml
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>സങ്കീർത്തനങ്ങൾ</title>
        <author>Hermann Gundert</author>
      </titleStmt>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div type="chapter" n="1">
        <l n="1">ആശീർവാദമുള്ളവൻ...</l>
      </div>
    </body>
  </text>
</TEI>
```

### ParaBible JSON

**Use Case**: Data analysis and API integration
**Extension**: `.json`
**Features**:
- Structured verse data
- Metadata preservation
- Easy programmatic access
- Search and analysis friendly

### BibleML/OSIS

**Use Case**: Biblical software and publishing
**Extension**: `.xml`
**Features**:
- OSIS standard compliance
- Cross-reference support
- Multi-language capabilities
- Publishing industry standard

### Microsoft Word DOCX

**Use Case**: Publication and sharing
**Extension**: `.docx`
**Features**:
- Professional formatting
- Malayalam font support
- Table of contents generation
- Print-ready layout

## Troubleshooting

### Common Issues

#### 1. Connection Errors

**Symptom**: "Connection failed" or timeout errors
**Solutions**:
```bash
# Check internet connection
ping opendigi.ub.uni-tuebingen.de

# Use verbose mode to diagnose
gundert-scraper extract <URL> --verbose

# Try with smaller batch size
gundert-scraper extract <URL> --batch-size 5
```

#### 2. Chrome/Selenium Issues

**Symptom**: "WebDriver setup failed" or browser errors
**Solutions**:
```bash
# Update Chrome browser
sudo apt update && sudo apt upgrade google-chrome-stable

# Check Chrome version
google-chrome --version

# Try without Selenium (limited functionality)
# Note: This feature would need to be implemented
```

#### 3. Malayalam Text Display Issues

**Symptom**: Garbled or missing Malayalam characters
**Solutions**:
```bash
# Install Malayalam fonts
sudo apt install fonts-malayalam

# Check Unicode support
locale | grep UTF-8

# Validate output encoding
gundert-scraper validate output.usfm --detailed
```

#### 4. Memory Issues with Large Books

**Symptom**: Process killed or memory errors
**Solutions**:
```bash
# Use smaller batch sizes
gundert-scraper extract <URL> --batch-size 5

# Process in chunks
gundert-scraper extract <URL> --start-page 1 --end-page 50
gundert-scraper extract <URL> --start-page 51 --end-page 100
```

#### 5. Validation Failures

**Symptom**: Content validation reports errors
**Solutions**:
```bash
# Get detailed validation report
gundert-scraper validate file.usfm --detailed

# Check format-specific requirements
gundert-scraper info --show-validators

# Manual inspection of problematic content
```

### Debug Mode

Enable verbose logging for detailed troubleshooting:

```bash
# Maximum verbosity
gundert-scraper --verbose extract <URL>

# Python logging (if needed)
export PYTHONPATH=/path/to/project
python -m logging.config.dictConfig '{"version":1,"disable_existing_loggers":false,"formatters":{"default":{"format":"%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},"handlers":{"console":{"class":"logging.StreamHandler","formatter":"default"}},"root":{"level":"DEBUG","handlers":["console"]}}'
```

### Getting Help

1. **Built-in Help**: `gundert-scraper --help`
2. **Command Help**: `gundert-scraper <command> --help`
3. **System Info**: `gundert-scraper info --system-info`
4. **GitHub Issues**: [Report bugs and request features](https://github.com/beniza/gundert-portal-scraper/issues)
5. **Discussions**: [Ask questions and share experiences](https://github.com/beniza/gundert-portal-scraper/discussions)

## Best Practices

### Performance Optimization

1. **Use Appropriate Batch Sizes**:
   - Small books: `--batch-size 10-20`
   - Large books: `--batch-size 5-10`
   - Slow connections: `--batch-size 3-5`

2. **Selective Format Generation**:
   ```bash
   # Generate only needed formats
   gundert-scraper extract <URL> --formats usfm  # Fast
   
   # Add formats later if needed
   gundert-scraper transform book.json --formats docx,tei_xml
   ```

3. **Parallel Processing**:
   ```bash
   # Use parallel processing for multiple books
   gundert-scraper batch *.json --parallel 4
   ```

### Data Quality

1. **Always Validate Output**:
   ```bash
   gundert-scraper extract <URL> --validate  # During extraction
   gundert-scraper validate output/* --detailed  # Post-processing
   ```

2. **Check Content Statistics**:
   - Review extraction success rates
   - Verify Malayalam character counts
   - Confirm verse/chapter numbering

3. **Preserve Original Data**:
   ```bash
   # Keep original extraction data
   gundert-scraper extract <URL> --formats parabible_json --preserve-images
   ```

### Organization

1. **Structured Output Directories**:
   ```bash
   mkdir -p projects/psalms/{extracted,transformed,validated}
   gundert-scraper extract <URL> --output projects/psalms/extracted
   ```

2. **Consistent Naming**:
   ```bash
   # Use book IDs for consistency
   gundert-scraper extract <URL> --book-id PSA --output projects/psalms
   ```

3. **Version Control**:
   ```bash
   # Track generated files in git
   git add projects/psalms/extracted/
   git commit -m "Add psalms extraction - pages 1-150"
   ```

### Academic Compliance

1. **Use TEI XML for Scholarly Work**:
   ```bash
   gundert-scraper extract <URL> --formats tei_xml --validate
   ```

2. **Preserve Metadata**:
   - Keep extraction timestamps
   - Document source URLs
   - Record processing parameters

3. **Citation Information**:
   - Include Gundert Portal source attribution
   - Document extraction methodology
   - Provide data provenance information

---

**Next**: See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for programmatic usage and API reference.