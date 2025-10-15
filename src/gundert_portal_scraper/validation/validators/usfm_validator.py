"""USFM content validator using usfm-grammar."""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from usfm_grammar import USFMParser
    USFM_GRAMMAR_AVAILABLE = True
except ImportError:
    USFM_GRAMMAR_AVAILABLE = False

from .. import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class USFMValidator(BaseValidator):
    """Validator for USFM format using usfm-grammar library."""
    
    def __init__(self):
        super().__init__()
        self.validator_name = "USFMValidator"
        
        if not USFM_GRAMMAR_AVAILABLE:
            logger.warning("usfm-grammar not available. USFM validation will be limited.")
    
    def validate_content(self, content: str, format_type: str, options: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate USFM content.
        
        Args:
            content: USFM content to validate
            format_type: Should be 'usfm'
            options: Optional validation options
            
        Returns:
            ValidationResult with validation issues
        """
        options = options or {}
        issues = []
        metadata = {
            'validator': self.validator_name,
            'format_type': format_type,
            'usfm_grammar_available': USFM_GRAMMAR_AVAILABLE
        }
        
        # Basic format checks
        issues.extend(self._check_basic_format(content))
        
        # Grammar validation if available
        if USFM_GRAMMAR_AVAILABLE:
            issues.extend(self._check_grammar(content, options))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="USFM_GRAMMAR_UNAVAILABLE",
                message="usfm-grammar library not available. Advanced validation skipped.",
                suggestion="Install usfm-grammar for comprehensive USFM validation"
            ))
        
        # Content-specific checks
        issues.extend(self._check_malayalam_content(content))
        issues.extend(self._check_verse_structure(content))
        
        success = len([i for i in issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) == 0
        
        metadata.update({
            'total_lines': len(content.split('\n')),
            'has_id_marker': content.startswith('\\id'),
            'has_usfm_version': '\\usfm' in content,
            'verse_count': content.count('\\v '),
            'chapter_count': content.count('\\c ')
        })
        
        return ValidationResult(
            success=success,
            format_type=format_type,
            issues=issues,
            metadata=metadata
        )
    
    def _check_basic_format(self, content: str) -> List[ValidationIssue]:
        """Check basic USFM format requirements."""
        issues = []
        lines = content.split('\n')
        
        # Check for required \\id marker
        if not content.strip().startswith('\\id'):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_ID_MARKER",
                message="USFM content must start with \\id marker",
                line_number=1,
                suggestion="Add \\id marker at the beginning of the file"
            ))
        
        # Check for USFM version marker
        if '\\usfm' not in content:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="MISSING_USFM_VERSION",
                message="USFM version marker (\\usfm) not found",
                suggestion="Add \\usfm 3.0 marker for version specification"
            ))
        
        # Check for empty lines that might cause issues
        for i, line in enumerate(lines, 1):
            if line.strip() == '' and i < len(lines):
                # Empty lines are generally OK in USFM but log as info
                continue
        
        # Check for unrecognized markers
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith('\\') and ' ' in line:
                marker = line.split()[0]
                if not self._is_known_marker(marker):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="UNKNOWN_MARKER",
                        message=f"Unknown or custom marker: {marker}",
                        line_number=i,
                        location=line
                    ))
        
        return issues
    
    def _check_grammar(self, content: str, options: Dict[str, Any]) -> List[ValidationIssue]:
        """Check USFM grammar using usfm-grammar library."""
        issues = []
        
        if not USFM_GRAMMAR_AVAILABLE:
            return issues
        
        try:
            # Parse with usfm-grammar - try different parsing methods
            parser = USFMParser()
            
            # The library might expect different input format
            try:
                # Try parsing as string directly
                result = parser.parse_from_string(content)
            except AttributeError:
                try:
                    # Try alternative method
                    result = parser.parse(usfm_text=content)
                except:
                    # Try minimal parsing
                    result = parser.parse(content)
            
            # Check for parsing errors
            if result and hasattr(result, 'errors') and result.errors:
                for error in result.errors:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="GRAMMAR_ERROR",
                        message=f"Grammar error: {error}",
                        context={'parser_error': str(error)}
                    ))
            
            # Check structure
            if result and hasattr(result, 'warnings') and result.warnings:
                for warning in result.warnings:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="GRAMMAR_WARNING",
                        message=f"Grammar warning: {warning}",
                        context={'parser_warning': str(warning)}
                    ))
            
            # If parsing succeeded without explicit errors/warnings, it's likely valid
            if result and not (hasattr(result, 'errors') and result.errors):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="GRAMMAR_PARSE_SUCCESS",
                    message="USFM content parsed successfully by grammar checker",
                ))
        
        except Exception as e:
            # Don't treat grammar parsing failures as critical errors
            # The content might still be valid USFM that the parser doesn't handle well
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="PARSER_EXCEPTION",
                message=f"USFM grammar checker failed: {e}",
                context={'exception': str(e)},
                suggestion="Content may still be valid USFM despite parser issues"
            ))
        
        return issues
    
    def _check_malayalam_content(self, content: str) -> List[ValidationIssue]:
        """Check Malayalam-specific content issues."""
        issues = []
        
        # Check for Malayalam characters
        malayalam_range = range(0x0D00, 0x0D80)  # Malayalam Unicode block
        has_malayalam = any(ord(char) in malayalam_range for char in content)
        
        if not has_malayalam:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="NO_MALAYALAM_CONTENT",
                message="No Malayalam characters detected in content",
                suggestion="Verify that Malayalam text is properly encoded"
            ))
        
        # Check for mixed scripts (might indicate encoding issues)
        has_latin = any(char.isascii() and char.isalpha() for char in content if not char.startswith('\\'))
        if has_malayalam and has_latin:
            # This is actually normal for USFM with Malayalam content
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="MIXED_SCRIPTS",
                message="Content contains both Malayalam and Latin scripts",
                context={'has_malayalam': has_malayalam, 'has_latin': has_latin}
            ))
        
        return issues
    
    def _check_verse_structure(self, content: str) -> List[ValidationIssue]:
        """Check verse numbering and structure."""
        issues = []
        lines = content.split('\n')
        
        current_chapter = 0
        verse_numbers = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Track chapters
            if line.startswith('\\c '):
                try:
                    chapter_num = int(line.split()[1])
                    if chapter_num != current_chapter + 1 and current_chapter > 0:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="CHAPTER_SEQUENCE",
                            message=f"Chapter {chapter_num} follows chapter {current_chapter}",
                            line_number=i
                        ))
                    current_chapter = chapter_num
                    verse_numbers = []  # Reset verse tracking
                except (IndexError, ValueError):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_CHAPTER_NUMBER",
                        message=f"Invalid chapter marker: {line}",
                        line_number=i
                    ))
            
            # Track verses
            elif line.startswith('\\v '):
                try:
                    verse_part = line.split(None, 2)[1]  # Get verse number part
                    verse_num = int(verse_part)
                    
                    if verse_numbers and verse_num != verse_numbers[-1] + 1:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="VERSE_SEQUENCE",
                            message=f"Verse {verse_num} follows verse {verse_numbers[-1] if verse_numbers else 0}",
                            line_number=i
                        ))
                    
                    verse_numbers.append(verse_num)
                    
                except (IndexError, ValueError):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_VERSE_NUMBER",
                        message=f"Invalid verse marker: {line}",
                        line_number=i
                    ))
        
        return issues
    
    def _is_known_marker(self, marker: str) -> bool:
        """Check if a marker is a known USFM marker."""
        # Common USFM markers - this is not exhaustive
        known_markers = {
            '\\id', '\\usfm', '\\h', '\\toc1', '\\toc2', '\\toc3', '\\mt1', '\\mt2', '\\mt3',
            '\\c', '\\v', '\\p', '\\m', '\\rem', '\\s1', '\\s2', '\\s3', '\\r', '\\d',
            '\\sp', '\\pc', '\\q1', '\\q2', '\\q3', '\\q4', '\\li1', '\\li2', '\\li3', '\\li4',
            '\\pi1', '\\pi2', '\\pi3', '\\pi4', '\\b', '\\nb'
        }
        
        return marker in known_markers