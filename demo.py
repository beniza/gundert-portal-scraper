#!/usr/bin/env python3
"""Demo script showing Gundert Bible scraping functionality."""

from gundert_bible_scraper.scraper import GundertBibleScraper
import json
import time


def main():
    """Demonstrate scraping the Gundert Bible."""
    print("🕮 Gundert Bible Scraper Demo")
    print("=" * 40)
    
    # Initialize scraper
    scraper = GundertBibleScraper(
        base_url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1",
        timeout=30
    )
    
    print(f"📍 Base URL: {scraper.base_url}")
    print()
    
    # Test URL building
    test_page = 11
    url = scraper.build_page_url(test_page, "transcript")
    print(f"🔗 Built URL for page {test_page}: {url}")
    print()
    
    # Try to scrape a page
    print(f"📖 Attempting to scrape page {test_page}...")
    try:
        page_data = scraper.scrape_page(test_page)
        
        if page_data:
            print("✅ Successfully scraped page!")
            print(f"📄 Page Number: {page_data['page_number']}")
            
            # Show transcript data
            transcript = page_data.get('transcript', [])
            print(f"📝 Transcript Lines: {len(transcript)}")
            
            if transcript:
                print("\n📖 First few transcript lines:")
                for i, line in enumerate(transcript[:5], 1):
                    print(f"   {i}. {line}")
                    
                if len(transcript) > 5:
                    print(f"   ... and {len(transcript) - 5} more lines")
            else:
                print("⚠️  No transcript content found on this page")
            
            # Show image data
            image_info = page_data.get('image')
            print(f"\n🖼️  Image Information:")
            if image_info:
                print(f"   URL: {image_info.get('url', 'N/A')}")
                print(f"   Alt Text: {image_info.get('alt_text', 'N/A')}")
                print(f"   Page Number: {image_info.get('page_number', 'N/A')}")
            else:
                print("   No image information found")
                
            # Save to JSON file
            output_file = f"page_{test_page}_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Data saved to: {output_file}")
            
        else:
            print("❌ Failed to scrape page - check network connection")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        print("This might be due to:")
        print("- Network connectivity issues")
        print("- Website structure changes")
        print("- Rate limiting")
    
    print("\n🏁 Demo completed!")


if __name__ == "__main__":
    main()