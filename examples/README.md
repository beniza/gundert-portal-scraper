# Examples 📚

Practical use cases and sample outputs demonstrating different scenarios for the Gundert Portal Scraper.

> **Note**: While these examples use biblical content, the Gundert Portal Scraper works with **all types of manuscripts** in the collection, including linguistic studies, literary works, cultural documents, and scholarly texts in **multiple Indian languages** (Malayalam, Sanskrit, Tamil, etc.).

## Directory Structure

```
examples/
├── README.md                    # This file
├── basic_usage.py              # Simple extraction examples
├── batch_processing.py         # Multiple book processing
├── custom_transformation.py    # Custom format development
├── scholarly_workflow.py       # Academic research workflow
├── api_integration.py          # Integration with other systems
├── cli_automation.py           # CLI scripting and automation
├── output_samples/             # Sample output files
│   ├── sample.usfm
│   ├── sample.tei.xml
│   ├── sample.docx
│   ├── sample.json
│   └── sample_scholarly.json
└── notebooks/                  # Jupyter notebooks
    ├── interactive_exploration.ipynb
    └── data_analysis.ipynb
```

## Available Examples

### 1. Basic Usage (`basic_usage.py`)
- Simple book extraction
- Single page processing
- Basic format conversion
- Error handling patterns

### 2. Batch Processing (`batch_processing.py`)
- Multiple book extraction
- Concurrent processing
- Progress tracking
- Result aggregation

### 3. Custom Transformation (`custom_transformation.py`)
- Plugin development
- Custom format creation
- Validation implementation
- Format-specific options

### 4. Scholarly Workflow (`scholarly_workflow.py`)
- Academic research pipeline
- TEI compliance
- Critical apparatus generation
- Metadata preservation

### 5. API Integration (`api_integration.py`)
- Web service integration
- Database storage
- RESTful API endpoints
- Data synchronization

### 6. CLI Automation (`cli_automation.py`)
- Shell scripting
- Automated workflows
- Configuration management
- System integration

## Quick Start

### Running Examples

```bash
# Clone repository
git clone https://github.com/beniza/gundert-portal-scraper.git
cd gundert-portal-scraper

# Install dependencies
uv sync

# Activate environment
source .venv/bin/activate

# Run basic example
python examples/basic_usage.py

# Run with custom parameters
python examples/batch_processing.py --config examples/config.yaml
```

### Sample Output Files

The `output_samples/` directory contains example outputs in various formats:

- **USFM**: `sample.usfm` - Bible translation standard format
- **TEI XML**: `sample.tei.xml` - Academic standard for digital texts
- **DOCX**: `sample.docx` - Microsoft Word format
- **JSON**: `sample.json` - ParaBible JSON format
- **Scholarly**: `sample_scholarly.json` - Enhanced academic format

### Interactive Notebooks

Jupyter notebooks for interactive exploration:

```bash
# Install Jupyter
uv add jupyter

# Start Jupyter server
jupyter notebook examples/notebooks/

# Open interactive_exploration.ipynb
```

## Example Categories

### Beginner Examples
- Basic extraction and conversion
- Simple CLI usage
- Error handling basics

### Intermediate Examples
- Batch processing workflows
- Custom format options
- Performance optimization

### Advanced Examples
- Plugin development
- System integration
- Academic workflows

### Production Examples
- Automated pipelines
- Error recovery
- Monitoring and logging

## Contributing Examples

We welcome contributions of new examples! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Example Template

```python
"""
Title: Brief description of the example
Level: Beginner/Intermediate/Advanced
Use Case: Specific scenario this addresses
"""

from gundert_portal_scraper import BookIdentifier, GundertPortalConnector

def main():
    """Main example function with clear documentation."""
    # Implementation here
    pass

if __name__ == "__main__":
    main()
```

## Support

- **Issues**: Report problems in [GitHub Issues](https://github.com/beniza/gundert-portal-scraper/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/beniza/gundert-portal-scraper/discussions)
- **Documentation**: See [docs/](../docs/) for comprehensive guides