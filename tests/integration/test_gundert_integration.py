"""Integration tests for Gundert Bible scraping.

These tests may make actual HTTP requests to test real functionality.
"""

import pytest
import time
from gundert_bible_scraper.scraper import GundertBibleScraper


class TestGundertBibleIntegration:
    """Integration tests that may use real HTTP requests."""

    @pytest.fixture
    def live_scraper(self):
        """Create a scraper for the real Gundert Bible site."""
        return GundertBibleScraper(
            base_url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1",
            timeout=30
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_page_scraping(self, live_scraper):
        """Test scraping a real page from the Gundert Bible site.
        
        Note: This makes actual HTTP requests and may be slow.
        """
        # Test with page 11 which should have content
        page_data = live_scraper.scrape_page(11)
        
        if page_data:  # Only assert if we got data (network dependent)
            assert page_data['page_number'] == 11
            assert 'transcript' in page_data
            assert 'image' in page_data
            assert isinstance(page_data['transcript'], list)
            
            # If there's transcript content, it should be non-empty strings
            if page_data['transcript']:
                for line in page_data['transcript']:
                    assert isinstance(line, str)
                    assert len(line.strip()) > 0
                    
                print(f"Found {len(page_data['transcript'])} transcript lines")
                for i, line in enumerate(page_data['transcript'][:3]):  # Show first 3 lines
                    print(f"Line {i+1}: {line}")
        else:
            pytest.skip("Could not fetch page data - network issue or site unavailable")

    @pytest.mark.integration
    def test_url_building(self, live_scraper):
        """Test URL building functionality."""
        url = live_scraper.build_page_url(15, "transcript")
        expected = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1#p=15&tab=transcript"
        assert url == expected

    @pytest.mark.integration 
    def test_multiple_page_urls(self, live_scraper):
        """Test building URLs for multiple pages."""
        pages = [1, 5, 10, 20]
        
        for page in pages:
            url = live_scraper.build_page_url(page)
            assert f"#p={page}&tab=transcript" in url
            assert live_scraper.base_url in url

    @pytest.mark.integration
    @pytest.mark.slow
    def test_scrape_multiple_pages(self, live_scraper):
        """Test scraping multiple pages (with rate limiting)."""
        pages_to_test = [1, 11]  # Test fewer pages to be respectful
        results = []
        
        for page_num in pages_to_test:
            print(f"Scraping page {page_num}...")
            page_data = live_scraper.scrape_page(page_num)
            
            if page_data:
                results.append(page_data)
                print(f"Page {page_num}: {len(page_data.get('transcript', []))} transcript lines")
            
            # Be respectful - add delay between requests
            time.sleep(1)
        
        # If we got any results, verify structure
        if results:
            for result in results:
                assert 'page_number' in result
                assert 'transcript' in result  
                assert 'image' in result
                assert isinstance(result['transcript'], list)
        else:
            pytest.skip("Could not fetch any page data - network issue or site unavailable")