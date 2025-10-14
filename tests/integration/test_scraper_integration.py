"""Integration tests for the scraper functionality."""

import pytest
import responses
from gundert_bible_scraper.scraper import GundertBibleScraper


class TestScraperIntegration:
    """Integration tests for scraper functionality."""

    @pytest.mark.integration
    @responses.activate
    def test_full_scraping_workflow(self):
        """Test complete scraping workflow from URL to extracted data."""
        # Mock HTML response that simulates a real page structure
        mock_page = """
        <html>
            <head><title>Gundert Bible - Chapter 1</title></head>
            <body>
                <div class="chapter">
                    <h1 class="chapter-title">Genesis Chapter 1</h1>
                    <div class="verse" data-verse="1">
                        <span class="verse-number">1</span>
                        <span class="verse-text">In the beginning God created the heaven and the earth.</span>
                    </div>
                    <div class="verse" data-verse="2">
                        <span class="verse-number">2</span>
                        <span class="verse-text">And the earth was without form, and void.</span>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Setup mock response
        responses.add(
            responses.GET,
            "https://example.com/genesis/1",
            body=mock_page,
            status=200
        )
        
        # Initialize scraper
        scraper = GundertBibleScraper(base_url="https://example.com")
        
        # Fetch and parse page
        soup = scraper.get_page("https://example.com/genesis/1")
        assert soup is not None
        
        # Extract different types of content
        chapter_title = scraper.extract_text(soup, ".chapter-title")
        verse_texts = scraper.extract_text(soup, ".verse-text")
        verse_numbers = scraper.extract_text(soup, ".verse-number")
        
        # Verify results
        assert len(chapter_title) == 1
        assert "Genesis Chapter 1" in chapter_title[0]
        
        assert len(verse_texts) == 2
        assert "In the beginning God created" in verse_texts[0]
        assert "And the earth was without form" in verse_texts[1]
        
        assert len(verse_numbers) == 2
        assert "1" in verse_numbers
        assert "2" in verse_numbers

    @pytest.mark.integration
    @pytest.mark.slow
    @responses.activate
    def test_multiple_page_scraping(self):
        """Test scraping multiple pages in sequence."""
        pages = {
            "https://example.com/page1": "<html><body><p>Page 1 content</p></body></html>",
            "https://example.com/page2": "<html><body><p>Page 2 content</p></body></html>",
            "https://example.com/page3": "<html><body><p>Page 3 content</p></body></html>"
        }
        
        # Setup multiple mock responses
        for url, content in pages.items():
            responses.add(responses.GET, url, body=content, status=200)
        
        scraper = GundertBibleScraper()
        results = []
        
        # Scrape all pages
        for url in pages.keys():
            soup = scraper.get_page(url)
            if soup:
                content = scraper.extract_text(soup, "p")
                results.extend(content)
        
        # Verify all pages were scraped
        assert len(results) == 3
        assert "Page 1 content" in results
        assert "Page 2 content" in results
        assert "Page 3 content" in results