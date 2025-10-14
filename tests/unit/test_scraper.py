"""Unit tests for the GundertBibleScraper class."""

import pytest
import responses
from unittest.mock import Mock
from gundert_bible_scraper.scraper import GundertBibleScraper
from bs4 import BeautifulSoup


class TestGundertBibleScraper:
    """Test cases for GundertBibleScraper."""

    @pytest.mark.unit
    def test_scraper_initialization(self, scraper):
        """Test that scraper initializes with correct default values."""
        assert scraper.base_url == "https://example.com"
        assert scraper.timeout == 10
        assert scraper.session is not None
        assert "GundertBibleScraper" in scraper.session.headers['User-Agent']

    @pytest.mark.unit
    def test_scraper_initialization_with_defaults(self):
        """Test scraper initialization with default parameters."""
        scraper = GundertBibleScraper()
        assert scraper.base_url == ""
        assert scraper.timeout == 30

    @pytest.mark.unit
    @responses.activate
    def test_get_page_success(self, scraper, mock_html):
        """Test successful page retrieval and parsing."""
        responses.add(
            responses.GET,
            "https://example.com/test",
            body=mock_html,
            status=200
        )
        
        soup = scraper.get_page("https://example.com/test")
        
        assert soup is not None
        assert isinstance(soup, BeautifulSoup)
        assert soup.title.string == "Test Page"

    @pytest.mark.unit
    @responses.activate
    def test_get_page_http_error(self, scraper):
        """Test page retrieval with HTTP error."""
        responses.add(
            responses.GET,
            "https://example.com/404",
            status=404
        )
        
        soup = scraper.get_page("https://example.com/404")
        
        assert soup is None

    @pytest.mark.unit
    def test_extract_text_with_valid_selector(self, scraper, mock_html):
        """Test text extraction with valid CSS selector."""
        soup = BeautifulSoup(mock_html, 'html.parser')
        
        texts = scraper.extract_text(soup, "p")
        
        assert len(texts) == 2
        assert "First paragraph" in texts
        assert "Second paragraph" in texts

    @pytest.mark.unit
    def test_extract_text_with_invalid_selector(self, scraper, mock_html):
        """Test text extraction with invalid CSS selector."""
        soup = BeautifulSoup(mock_html, 'html.parser')
        
        texts = scraper.extract_text(soup, ".nonexistent")
        
        assert texts == []

    @pytest.mark.unit
    def test_extract_text_removes_empty_strings(self, scraper):
        """Test that extract_text removes empty strings."""
        html_with_empty = """
        <div>
            <p>Text content</p>
            <p></p>
            <p>   </p>
            <p>More content</p>
        </div>
        """
        soup = BeautifulSoup(html_with_empty, 'html.parser')
        
        texts = scraper.extract_text(soup, "p")
        
        assert len(texts) == 2
        assert "Text content" in texts
        assert "More content" in texts