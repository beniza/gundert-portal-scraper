"""Pytest configuration and fixtures."""

import pytest
import responses
from gundert_bible_scraper.scraper import GundertBibleScraper


@pytest.fixture
def scraper():
    """Create a GundertBibleScraper instance for testing."""
    return GundertBibleScraper(base_url="https://example.com", timeout=10)


@pytest.fixture
def mock_html():
    """Sample HTML content for testing."""
    return """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <div class="content">
                <p>First paragraph</p>
                <p>Second paragraph</p>
            </div>
            <div class="sidebar">
                <span>Sidebar content</span>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_responses():
    """Mock HTTP responses for testing."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(scope="session")
def sample_urls():
    """Sample URLs for testing."""
    return {
        "valid": "https://example.com/valid",
        "invalid": "https://example.com/404",
        "timeout": "https://example.com/timeout"
    }