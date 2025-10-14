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
from src.scraper import GundertBibleScraper

scraper = GundertBibleScraper()
# Add usage examples here
```

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