# Gundert Bible Scraper

A web scraping project for the Gundert Bible using Test-Driven Development (TDD) approach.

## Features

- Clean, maintainable web scraping code
- Comprehensive test coverage with pytest
- Support for both unit and integration testing
- Robust error handling and data validation

## Installation

```bash
# Create virtual environment
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv sync --dev
```

## Usage

```python
from gundert_bible_scraper.scraper import GundertBibleScraper

# Initialize scraper for Gundert Bible site
scraper = GundertBibleScraper(
    base_url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
)

# Scrape a specific page (returns transcript and image data)
page_data = scraper.scrape_page(11)

if page_data:
    print(f"Page {page_data['page_number']}")
    print(f"Transcript lines: {len(page_data['transcript'])}")
    for line in page_data['transcript']:
        print(f"  {line}")
    
    if page_data['image']:
        print(f"Image URL: {page_data['image']['url']}")
```

### Demo Script

Run the included demo to see the scraper in action:

```bash
python demo.py
```

**Note**: The Gundert Bible website uses JavaScript to load content dynamically. The current implementation handles static HTML content. For full functionality with dynamic content, consider using tools like Selenium or Playwright.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

## Development

This project follows TDD principles:
1. Write a failing test
2. Write minimal code to make it pass
3. Refactor while keeping tests green

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── scraper.py
│   └── utils/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── pyproject.toml
└── README.md
```