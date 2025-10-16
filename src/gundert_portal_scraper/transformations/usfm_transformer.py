"""
USFM (Unified Standard Format Marker) Transformer

Converts extracted JSON content to USFM format for Bible translation projects.
Handles Malayalam text with proper Unicode encoding and USFM markers.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


# Malayalam digit mapping
MALAYALAM_DIGITS = {
    '൦': '0', '൧': '1', '൨': '2', '൩': '3', '൪': '4',
    '൫': '5', '൬': '6', '൭': '7', '൮': '8', '൯': '9'
}


def malayalam_to_arabic(text: str) -> str:
    """Convert Malayalam digits to Arabic numerals."""
    for mal, arab in MALAYALAM_DIGITS.items():
        text = text.replace(mal, arab)
    return text


def is_page_header(line: str) -> bool:
    """Check if line is a page header/footer that should be skipped."""
    # Check for patterns like "6 Psalms, II." or "സങ്കീൎത്തനങ്ങൾ ൨ ."
    if 'Psalms' in line and (',' in line or '  ' in line):
        return True
    # Check for simple page numbering patterns
    converted = malayalam_to_arabic(line)
    if re.match(r'^\d+\s+(Psalms|സങ്കീ)', converted):
        return True
    return False


def extract_verse_number(line: str) -> Optional[int]:
    """
    Extract verse number from a line of text.
    
    Handles both Malayalam (൧, ൨, etc.) and Arabic (1, 2, etc.) numerals.
    Returns None if no verse number is found.
    """
    # Skip if it looks like a page header
    if is_page_header(line):
        return None
    
    # Convert Malayalam digits to Arabic first
    converted = malayalam_to_arabic(line)
    
    # Look for verse number at start of line
    # Pattern: optional whitespace, number, space or punctuation
    match = re.match(r'^\s*(\d+)\s+', converted)
    if match:
        verse_num = int(match.group(1))
        # Sanity check: verse numbers shouldn't be too large
        if verse_num < 200:  # Longest psalm has ~176 verses
            return verse_num
    
    return None


def extract_psalm_number(line: str) -> Optional[int]:
    """
    Extract psalm number from heading line.
    
    Examples:
    - "൧. സങ്കീർത്തനം." → 1
    - "൨ . സങ്കീർത്തനം." → 2
    """
    # Convert Malayalam digits
    converted = malayalam_to_arabic(line)
    
    # Look for pattern: number followed by dot and "സങ്കീർത്തനം"
    if 'സങ്കീർത്തനം' in line or 'സങ്കീൎത്തനം' in line:
        match = re.search(r'(\d+)\s*\.?\s*സങ്കീ', converted)
        if match:
            return int(match.group(1))
    
    return None


class USFMTransformer:
    """Transform extracted JSON content to USFM format."""
    
    # USFM book code for Psalms
    BOOK_CODE = "PSA"
    BOOK_NAME_MALAYALAM = "സങ്കീർത്തനങ്ങൾ"
    
    def __init__(self):
        """Initialize the USFM transformer."""
        self.current_chapter = 0
        self.current_verse = 0
        self.verses_buffer: List[tuple[int, str]] = []  # (verse_num, text)
        self.in_psalm = False
        
    def transform(self, json_path: str, output_path: Optional[str] = None) -> str:
        """
        Transform extracted JSON to USFM format.
        
        Args:
            json_path: Path to input JSON file
            output_path: Optional path to save USFM output
            
        Returns:
            USFM formatted string
        """
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Generate USFM content
        usfm_content = self._generate_usfm(data)
        
        # Save if output path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(usfm_content, encoding='utf-8')
        
        return usfm_content
    
    def _generate_usfm(self, data: Dict[str, Any]) -> str:
        """Generate USFM content from JSON data."""
        lines = []
        
        # Add USFM header
        lines.extend(self._generate_header(data.get('metadata', {})))
        
        # Process pages
        pages = data.get('pages', [])
        for page in pages:
            self._process_page(page, lines)
        
        # Add final newline
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_header(self, metadata: Dict[str, Any]) -> List[str]:
        """Generate USFM file header."""
        lines = [
            "\\id PSA Malayalam: Gundert's Translation (1880)",
            "\\usfm 3.0",
            f"\\ide UTF-8",
            f"\\h {self.BOOK_NAME_MALAYALAM}",
            f"\\toc1 {self.BOOK_NAME_MALAYALAM}",
            f"\\toc2 സങ്കീർത്തനങ്ങൾ",
            f"\\toc3 സങ്കീ",
            f"\\mt1 {self.BOOK_NAME_MALAYALAM}",
            ""
        ]
        
        # Add extraction metadata as comment
        if metadata:
            lines.append(f"\\rem Extracted from: {metadata.get('book_id', 'unknown')}")
            lines.append(f"\\rem Extraction date: {metadata.get('extraction_date', 'unknown')}")
            lines.append(f"\\rem Total pages: {metadata.get('total_pages', 'unknown')}")
            lines.append("")
        
        return lines
    
    def _process_page(self, page: Dict[str, Any], lines: List[str]):
        """Process a single page and extract psalms/verses."""
        page_lines = page.get('lines', [])
        
        for line_text in page_lines:
            # Skip empty lines
            if not line_text.strip():
                continue
            
            # Skip page headers/footers
            if is_page_header(line_text):
                continue
            
            # Skip lines that are purely English headers
            if line_text.strip() in ['THE', 'BOOK OF PSALMS', 'BOOK OF PSALMS.']:
                continue
            
            # Check for new psalm
            psalm_num = extract_psalm_number(line_text)
            if psalm_num is not None:
                # Flush any buffered verses from previous psalm
                self._flush_verses(lines)
                
                # Start new chapter (psalm)
                self.current_chapter = psalm_num
                self.current_verse = 0
                self.in_psalm = True
                lines.append(f"\\c {psalm_num}")
                continue
            
            # Check for verse number
            verse_num = extract_verse_number(line_text)
            if verse_num is not None and self.in_psalm:
                # Flush previous verse if exists
                if self.verses_buffer:
                    self._flush_verses(lines)
                
                # Extract verse text (remove verse number)
                verse_text = re.sub(r'^\s*[൦-൯\d]+\s+', '', line_text).strip()
                
                # Skip if verse text is empty or just a page reference
                if not verse_text or verse_text.startswith('Psalms'):
                    continue
                
                # Start new verse
                self.current_verse = verse_num
                self.verses_buffer = [(verse_num, verse_text)]
                continue
            
            # Continue current verse (multi-line verse)
            if self.in_psalm and self.verses_buffer:
                # This line is a continuation of the current verse
                self.verses_buffer.append((self.current_verse, line_text.strip()))
            elif self.in_psalm and self.current_chapter > 0:
                # Line without verse number in psalm context
                # Could be psalm title or description - add as \d (descriptive title)
                if any(keyword in line_text for keyword in ['ദാവിദ', 'സംഗീതപ്രമാണി', 'കാണ്ഡം', 'കീൎത്തന']):
                    lines.append(f"\\d {line_text.strip()}")
    
    def _flush_verses(self, lines: List[str]):
        """Flush buffered verses to output."""
        if not self.verses_buffer:
            return
        
        # Group verse parts
        verse_num = self.verses_buffer[0][0]
        verse_parts = [text for _, text in self.verses_buffer]
        
        # Join verse parts with space
        verse_text = " ".join(verse_parts)
        
        # Add verse marker and text
        lines.append(f"\\v {verse_num} {verse_text}")
        
        # Clear buffer
        self.verses_buffer = []
    
    def transform_directory(self, json_dir: str, output_dir: str, file_pattern: str = "*.json"):
        """
        Transform all JSON files in a directory to USFM format.
        
        Args:
            json_dir: Directory containing JSON files
            output_dir: Directory to save USFM files
            file_pattern: Glob pattern for JSON files (default: "*.json")
        """
        json_path = Path(json_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for json_file in json_path.glob(file_pattern):
            # Generate output filename
            usfm_file = output_path / f"{json_file.stem}.usfm"
            
            # Transform and save
            print(f"Transforming {json_file.name} → {usfm_file.name}")
            self.transform(str(json_file), str(usfm_file))
            print(f"  ✓ Saved to {usfm_file}")


def main():
    """Command-line entry point for USFM transformer."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m gundert_portal_scraper.transformations.usfm_transformer <json_file> [output_file]")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not output_path:
        output_path = Path(json_path).with_suffix('.usfm')
    
    transformer = USFMTransformer()
    usfm_content = transformer.transform(json_path, output_path)
    
    print(f"✓ USFM file generated: {output_path}")
    print(f"  Total characters: {len(usfm_content)}")


if __name__ == "__main__":
    main()
