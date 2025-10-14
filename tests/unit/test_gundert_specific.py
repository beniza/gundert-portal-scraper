"""TDD Tests for GundertBible-specific scraping functionality.

These tests should FAIL initially and drive the implementation.
"""

import pytest
import responses
from unittest.mock import Mock, patch
from gundert_bible_scraper.scraper import GundertBibleScraper
from bs4 import BeautifulSoup


class TestGundertBibleSpecificScraping:
    """Test cases for Gundert Bible website-specific functionality."""

    @pytest.fixture
    def gundert_scraper(self):
        """Create a scraper configured for Gundert Bible site."""
        return GundertBibleScraper(
            base_url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1"
        )

    @pytest.fixture
    def mock_gundert_html(self):
        """Mock HTML structure based on the actual Gundert Bible site."""
        return """
        <html>
            <body>
                <div id="viewer-tabs">
                    <div class="tab-content">
                        <div id="transcript" class="tab-pane">
                            <div id="transcript-content" class="contains-tei">
                                <p>യിസ്രയേൽ രാജാവായ ദാവീദിന്റെ പുത്രനായ</p>
                                <p>ശലോമോന്റെ സദൃശവാക്യങ്ങൾ</p>
                                <p>ജ്ഞാനവും ഉപദേശവും അറിയേണ്ടതിന്നും</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div id="viewer-window">
                    <img src="/static/images/page011.jpg" alt="Page 11" data-page="11">
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def mock_empty_transcript_html(self):
        """Mock HTML for page with no transcript."""
        return """
        <html>
            <body>
                <div id="viewer-tabs">
                    <div class="tab-content">
                        <div id="transcript" class="tab-pane">
                            <div id="transcript-empty" class="alert alert-info">
                                There is no transcription available for this page.
                            </div>
                            <div id="transcript-content" class="contains-tei"></div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """

    # TRANSCRIPT EXTRACTION TESTS (These should FAIL initially)
    
    @pytest.mark.unit
    def test_extract_transcript_from_page_success(self, gundert_scraper, mock_gundert_html):
        """Test extracting Malayalam transcript text from a page.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        soup = BeautifulSoup(mock_gundert_html, 'html.parser')
        
        # This method doesn't exist yet - should fail!
        transcript_lines = gundert_scraper.extract_transcript(soup)
        
        assert len(transcript_lines) == 3
        assert "യിസ്രയേൽ രാജാവായ ദാവീദിന്റെ പുത്രനായ" in transcript_lines
        assert "ശലോമോന്റെ സദൃശവാക്യങ്ങൾ" in transcript_lines
        assert "ജ്ഞാനവും ഉപദേശവും അറിയേണ്ടതിന്നും" in transcript_lines

    @pytest.mark.unit
    def test_extract_transcript_empty_page(self, gundert_scraper, mock_empty_transcript_html):
        """Test handling pages with no transcript available.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        soup = BeautifulSoup(mock_empty_transcript_html, 'html.parser')
        
        transcript_lines = gundert_scraper.extract_transcript(soup)
        
        assert transcript_lines == []

    @pytest.mark.unit
    def test_extract_transcript_filters_empty_lines(self, gundert_scraper):
        """Test that transcript extraction filters out empty paragraphs.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        html_with_empty = """
        <div id="transcript-content" class="contains-tei">
            <p>വാക്യം ഒന്ന്</p>
            <p></p>
            <p>   </p>
            <p>വാക്യം രണ്ട്</p>
        </div>
        """
        soup = BeautifulSoup(html_with_empty, 'html.parser')
        
        transcript_lines = gundert_scraper.extract_transcript(soup)
        
        assert len(transcript_lines) == 2
        assert "വാക്യം ഒന്ന്" in transcript_lines
        assert "വാക്യം രണ്ട്" in transcript_lines

    # IMAGE EXTRACTION TESTS (These should FAIL initially)
    
    @pytest.mark.unit
    def test_extract_image_url_from_page(self, gundert_scraper, mock_gundert_html):
        """Test extracting image URL from the viewer window.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        soup = BeautifulSoup(mock_gundert_html, 'html.parser')
        
        # This method doesn't exist yet - should fail!
        image_info = gundert_scraper.extract_image_info(soup)
        
        assert image_info is not None
        assert image_info['url'] == "/static/images/page011.jpg"
        assert image_info['page_number'] == "11"
        assert image_info['alt_text'] == "Page 11"

    @pytest.mark.unit
    def test_extract_image_info_no_image(self, gundert_scraper):
        """Test handling pages with no image in viewer window.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        html_no_image = """
        <div id="viewer-window">
            <!-- No image here -->
        </div>
        """
        soup = BeautifulSoup(html_no_image, 'html.parser')
        
        image_info = gundert_scraper.extract_image_info(soup)
        
        assert image_info is None

    # INTEGRATION TESTS WITH HTTP MOCKING
    
    @pytest.mark.integration
    @responses.activate
    def test_scrape_page_with_transcript_and_image(self, gundert_scraper, mock_gundert_html):
        """Test scraping a complete page with both transcript and image.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        responses.add(
            responses.GET,
            "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1#p=11&tab=transcript",
            body=mock_gundert_html,
            status=200
        )
        
        # This method doesn't exist yet - should fail!
        page_data = gundert_scraper.scrape_page(11)
        
        assert page_data is not None
        assert 'transcript' in page_data
        assert 'image' in page_data
        assert page_data['page_number'] == 11
        assert len(page_data['transcript']) > 0
        assert page_data['image']['url'] is not None

    @pytest.mark.integration
    def test_build_page_url(self, gundert_scraper):
        """Test URL construction for specific pages.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        # This method doesn't exist yet - should fail!
        url = gundert_scraper.build_page_url(11, tab="transcript")
        
        expected = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1#p=11&tab=transcript"
        assert url == expected

    @pytest.mark.integration
    def test_build_page_url_default_tab(self, gundert_scraper):
        """Test URL construction with default tab.
        
        This test should FAIL initially - method doesn't exist yet.
        """
        url = gundert_scraper.build_page_url(15)
        
        expected = "https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1#p=15&tab=transcript"
        assert url == expected