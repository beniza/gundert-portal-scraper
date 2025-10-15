# Gundert Portal Scraper 🏛️

> **Universal Digital Manuscript Extractor for Historical Collections**

A comprehensive, production-ready tool for extracting, transforming, and validating content from the Gundert Portal and OpenDigi digital manuscript collections. Works with **multiple Indian languages** and **diverse content types** including linguistic studies, religious texts, literary works, cultural documents, and scholarly manuscripts. Built with academic rigor and modern software engineering practices.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)](https://github.com/beniza/gundert-portal-scraper)

## 🌟 Features

### **Universal Content Extraction**
- 🔍 **Multi-Portal Support**: Works with Gundert Portal and OpenDigi collections
- 🌍 **Multi-Language Support**: Handles Malayalam, Sanskrit, Tamil, and other Indian languages
- � **Diverse Content Types**: Biblical texts, linguistic studies, literary works, cultural documents
- �📜 **Historical Manuscript Processing**: Specialized for 19th-century digitized manuscripts
- 🎯 **Intelligent Content Detection**: Automatically identifies text regions in multiple scripts
- 📊 **Line-Level Preservation**: Maintains exact manuscript formatting and structure

### **Professional Transformation Pipeline**
- 📝 **5 Output Formats**: USFM, TEI XML, ParaBible JSON, BibleML/OSIS, Microsoft Word DOCX
- 🔄 **Plugin Architecture**: Extensible transformation system
- 📋 **Academic Standards**: TEI XML compliance for digital humanities
- 💼 **Publication Ready**: Professional DOCX output with proper styling

### **Comprehensive Quality Assurance**
- ✅ **Multi-Format Validation**: Built-in validators for all output formats
- 🧪 **Test-Driven Development**: 28+ tests with 88% code coverage
- 🔍 **Malayalam-Specific Checks**: Unicode validation and encoding verification
- 📈 **Quality Metrics**: Detailed reports on extraction success and content quality

### **User-Friendly Interface**
- 🖥️ **Professional CLI**: Rich console interface with progress indicators
- 🚀 **Simple Commands**: Extract, transform, validate, and batch process
- 📚 **Comprehensive Help**: Built-in documentation and examples
- 🔧 **Flexible Configuration**: Customizable extraction and transformation options

## 🚀 Quick Start

### Installation
```bash
# Using uv (recommended)
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper
uv sync

# Using pip
pip install gundert-portal-scraper  # Coming soon to PyPI
```

### Basic Usage
```bash
# Extract content from Gundert Portal manuscripts
gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1 \
  --formats usfm,docx --output ./extracted

# Validate generated content
gundert-scraper validate extracted/*.usfm --detailed

# Transform existing data to different formats
gundert-scraper transform book_data.json --formats tei_xml,bibleml

# Batch process multiple books
gundert-scraper batch *.json --formats usfm,docx --parallel 3
```

### Programmatic Usage
```python
from gundert_portal_scraper import BookIdentifier, GundertPortalConnector, ContentScraper

# Extract content programmatically
book_id = BookIdentifier("https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1")

with GundertPortalConnector(book_id, use_selenium=True) as connector:
    scraper = ContentScraper(connector, preserve_formatting=True)
    book_data = scraper.scrape_full_book(start_page=1, end_page=10)
    
    print(f"Extracted {book_data['statistics']['total_lines_extracted']} lines")
    print(f"Success rate: {book_data['statistics']['success_rate']:.1f}%")
```

## 📚 Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Complete CLI usage and workflows
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Architecture and API reference
- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[API Reference](docs/API_REFERENCE.md)** - Programmatic interface documentation
- **[Examples](examples/)** - Practical use cases and sample outputs

## 🏗️ Architecture

### Modular Design
```
src/gundert_portal_scraper/
├── core/           # Connection and book identification
├── extraction/     # Content and metadata scraping
├── storage/        # Data persistence and schemas
├── transformations/# Format conversion plugins
├── validation/     # Content quality assurance
├── cli/           # Command-line interface
└── preview/       # Content preview and sampling
```

### Supported Formats
| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| **USFM** | `.usfm` | Unified Standard Format Marker | Bible translation projects |
| **TEI XML** | `.xml` | Text Encoding Initiative | Digital humanities research |
| **ParaBible JSON** | `.json` | Structured verse data | Data analysis and APIs |
| **BibleML/OSIS** | `.xml` | Biblical markup standard | Scripture publishing |
| **DOCX** | `.docx` | Microsoft Word document | Publication and sharing |

## 🎯 Use Cases

### **Digital Humanities Research**
- Extract and analyze historical manuscripts in multiple Indian languages
- Generate TEI XML for scholarly digital editions
- Preserve historical text formatting and structure
- Support comparative textual analysis

### **Bible Translation Projects**
- Convert historical texts to modern USFM format
- Maintain verse numbering and chapter structure
- Generate publication-ready Word documents
- Validate content against biblical standards

### **Language Preservation**
- Digitize 19th-century Malayalam typography
- Preserve Unicode text with proper encoding
- Document historical spelling variations
- Support linguistic analysis and research

### **Academic Publishing**
- Generate properly formatted academic outputs
- Maintain scholarly metadata and provenance
- Support citation and referencing standards
- Enable collaborative research workflows

## 🔧 Requirements

- **Python 3.10+**
- **Chrome/Chromium** (for Selenium-based extraction)
- **Dependencies**: Automatically managed via `uv` or `pip`

### Optional Dependencies
- `usfm-grammar` - Enhanced USFM validation
- `lxml` - Advanced XML processing
- `python-docx` - Word document generation

## 🤝 Contributing

We welcome contributions! See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for:
- Development setup and guidelines
- Architecture overview and design principles
- Testing requirements and coverage standards
- Code style and documentation standards

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Hermann Gundert** - 19th-century scholar and Malayalam linguist
- **University of Tübingen** - OpenDigi digital manuscript collection
- **Malayalam Digital Humanities** - Preserving historical texts for future generations

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/beniza/gundert-portal-scraper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/beniza/gundert-portal-scraper/discussions)
- **Documentation**: [Project Wiki](https://github.com/beniza/gundert-portal-scraper/wiki)

---

**Made with ❤️ for Malayalam digital preservation and biblical studies**