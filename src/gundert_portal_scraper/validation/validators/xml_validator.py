"""XML content validators for TEI and BibleML formats."""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

from .. import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class XMLValidator(BaseValidator):
    """Validator for XML-based formats (TEI XML, BibleML/OSIS)."""
    
    def __init__(self):
        super().__init__()
        self.validator_name = "XMLValidator"
        
        # Define expected root elements for different formats
        self.format_roots = {
            'tei_xml': 'TEI',
            'bibleml': 'osis'
        }
        
        # Define expected namespaces
        self.format_namespaces = {
            'tei_xml': 'http://www.tei-c.org/ns/1.0',
            'bibleml': 'http://www.bibletechnologies.net/2003/OSIS/namespace'
        }
    
    def validate_content(self, content: str, format_type: str, options: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate XML content.
        
        Args:
            content: XML content to validate
            format_type: 'tei_xml' or 'bibleml'
            options: Optional validation options
            
        Returns:
            ValidationResult with validation issues
        """
        options = options or {}
        issues = []
        metadata = {
            'validator': self.validator_name,
            'format_type': format_type,
            'lxml_available': LXML_AVAILABLE
        }
        
        # Basic XML well-formedness check
        xml_tree, parse_issues = self._parse_xml(content)
        issues.extend(parse_issues)
        
        if xml_tree is not None:
            # Format-specific validation
            if format_type == 'tei_xml':
                issues.extend(self._validate_tei_xml(xml_tree, content))
            elif format_type == 'bibleml':
                issues.extend(self._validate_bibleml(xml_tree, content))
            
            # General XML structure checks
            issues.extend(self._check_xml_structure(xml_tree, format_type))
            issues.extend(self._check_malayalam_content(xml_tree))
            
            # Update metadata with XML info
            metadata.update(self._get_xml_metadata(xml_tree))
        
        success = len([i for i in issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) == 0
        
        return ValidationResult(
            success=success,
            format_type=format_type,
            issues=issues,
            metadata=metadata
        )
    
    def _parse_xml(self, content: str) -> tuple[Optional[ET.Element], List[ValidationIssue]]:
        """Parse XML content and return tree and any parsing issues."""
        issues = []
        
        try:
            # Try parsing with ElementTree first
            root = ET.fromstring(content)
            return root, issues
            
        except ET.ParseError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                code="XML_PARSE_ERROR",
                message=f"XML parsing failed: {e}",
                line_number=getattr(e, 'lineno', None),
                context={'parser_error': str(e)}
            ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                code="XML_PARSE_EXCEPTION",
                message=f"Unexpected XML parsing error: {e}",
                context={'exception': str(e)}
            ))
        
        return None, issues
    
    def _validate_tei_xml(self, root: ET.Element, content: str) -> List[ValidationIssue]:
        """Validate TEI XML specific structure."""
        issues = []
        
        # Check root element
        if root.tag != 'TEI' and not root.tag.endswith('}TEI'):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="TEI_INVALID_ROOT",
                message=f"TEI XML root should be 'TEI', found '{root.tag}'",
                suggestion="Ensure root element is <TEI>"
            ))
        
        # Check for required TEI structure
        tei_header = root.find('.//{http://www.tei-c.org/ns/1.0}teiHeader') or root.find('.//teiHeader')
        if tei_header is None:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="TEI_MISSING_HEADER",
                message="TEI XML missing required teiHeader element",
                suggestion="Add <teiHeader> element with metadata"
            ))
        
        text_element = root.find('.//{http://www.tei-c.org/ns/1.0}text') or root.find('.//text')
        if text_element is None:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="TEI_MISSING_TEXT",
                message="TEI XML missing required text element",
                suggestion="Add <text> element containing the document content"
            ))
        
        # Check for recommended elements
        if tei_header is not None:
            file_desc = tei_header.find('.//{http://www.tei-c.org/ns/1.0}fileDesc') or tei_header.find('.//fileDesc')
            if file_desc is None:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="TEI_MISSING_FILEDESC",
                    message="TEI header missing recommended fileDesc element",
                    suggestion="Add <fileDesc> for better metadata"
                ))
        
        return issues
    
    def _validate_bibleml(self, root: ET.Element, content: str) -> List[ValidationIssue]:
        """Validate BibleML/OSIS specific structure."""
        issues = []
        
        # Check root element
        if root.tag != 'osis' and not root.tag.endswith('}osis'):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="OSIS_INVALID_ROOT",
                message=f"OSIS XML root should be 'osis', found '{root.tag}'",
                suggestion="Ensure root element is <osis>"
            ))
        
        # Check for required OSIS structure
        osis_text = root.find('.//{http://www.bibletechnologies.net/2003/OSIS/namespace}osisText') or root.find('.//osisText')
        if osis_text is None:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="OSIS_MISSING_TEXT",
                message="OSIS XML missing required osisText element",
                suggestion="Add <osisText> element"
            ))
        
        # Check for header
        header = root.find('.//{http://www.bibletechnologies.net/2003/OSIS/namespace}header') or root.find('.//header')
        if header is None:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="OSIS_MISSING_HEADER",
                message="OSIS XML missing recommended header element",
                suggestion="Add <header> with work information"
            ))
        
        # Check verses structure
        verses = root.findall('.//{http://www.bibletechnologies.net/2003/OSIS/namespace}verse') or root.findall('.//verse')
        if not verses:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="OSIS_NO_VERSES",
                message="No verse elements found in OSIS document",
                suggestion="Add <verse> elements for biblical content"
            ))
        else:
            # Check verse numbering
            for i, verse in enumerate(verses):
                verse_n = verse.get('n')
                if not verse_n:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="OSIS_VERSE_NO_NUMBER",
                        message=f"Verse element missing 'n' attribute",
                        location=f"verse index {i}",
                        suggestion="Add 'n' attribute with verse number"
                    ))
        
        return issues
    
    def _check_xml_structure(self, root: ET.Element, format_type: str) -> List[ValidationIssue]:
        """Check general XML structure issues."""
        issues = []
        
        # Check namespace declaration
        expected_ns = self.format_namespaces.get(format_type)
        if expected_ns:
            # Check if namespace is declared (this is a simplified check)
            root_tag = root.tag
            if expected_ns not in root_tag and 'xmlns' not in root.attrib:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_NAMESPACE",
                    message=f"Expected namespace '{expected_ns}' not found",
                    suggestion=f"Add xmlns=\"{expected_ns}\" to root element"
                ))
        
        # Check for empty elements that might indicate issues
        empty_elements = []
        for elem in root.iter():
            if elem.text is None and len(elem) == 0 and len(elem.attrib) == 0:
                empty_elements.append(elem.tag)
        
        if empty_elements:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="EMPTY_ELEMENTS",
                message=f"Found {len(empty_elements)} empty elements",
                context={'empty_elements': empty_elements[:10]}  # Limit to first 10
            ))
        
        return issues
    
    def _check_malayalam_content(self, root: ET.Element) -> List[ValidationIssue]:
        """Check for Malayalam content in XML."""
        issues = []
        
        # Get all text content
        all_text = []
        for elem in root.iter():
            if elem.text:
                all_text.append(elem.text)
            if elem.tail:
                all_text.append(elem.tail)
        
        combined_text = ' '.join(all_text)
        
        # Check for Malayalam characters
        malayalam_range = range(0x0D00, 0x0D80)
        has_malayalam = any(ord(char) in malayalam_range for char in combined_text)
        
        if not has_malayalam:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="NO_MALAYALAM_CONTENT",
                message="No Malayalam characters detected in XML content",
                suggestion="Verify Malayalam text encoding"
            ))
        
        # Check xml:lang attribute
        lang_attr = root.get('{http://www.w3.org/XML/1998/namespace}lang') or root.get('xml:lang')
        if has_malayalam and lang_attr != 'ml':
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="MISSING_MALAYALAM_LANG",
                message="Malayalam content detected but xml:lang not set to 'ml'",
                suggestion="Add xml:lang=\"ml\" to root element",
                context={'current_lang': lang_attr}
            ))
        
        return issues
    
    def _get_xml_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Extract metadata from XML structure."""
        metadata = {}
        
        # Count elements by type
        element_counts = {}
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            element_counts[tag] = element_counts.get(tag, 0) + 1
        
        metadata['element_counts'] = element_counts
        metadata['total_elements'] = len(list(root.iter()))
        
        # Get text statistics
        all_text = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                all_text.append(elem.text.strip())
        
        metadata['text_elements'] = len(all_text)
        metadata['total_characters'] = sum(len(text) for text in all_text)
        
        # Check for attributes
        total_attributes = sum(len(elem.attrib) for elem in root.iter())
        metadata['total_attributes'] = total_attributes
        
        return metadata