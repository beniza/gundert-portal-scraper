"""JSON content validator for ParaBible format."""

import json
import logging
from typing import Dict, List, Optional, Any

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

from .. import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class JSONValidator(BaseValidator):
    """Validator for JSON-based formats (ParaBible JSON)."""
    
    def __init__(self):
        super().__init__()
        self.validator_name = "JSONValidator"
        
        # Define ParaBible JSON schema
        self.parabible_schema = {
            "type": "object",
            "required": ["metadata", "verses"],
            "properties": {
                "metadata": {
                    "type": "object",
                    "required": ["book_id", "title"],
                    "properties": {
                        "book_id": {"type": "string"},
                        "book_code": {"type": "string"},
                        "title": {"type": "string"},
                        "language": {"type": "string"},
                        "script": {"type": "string"},
                        "source": {"type": "object"},
                        "transformation": {"type": "object"},
                        "encoding": {"type": "string"}
                    }
                },
                "verses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "chapter", "verse", "text"],
                        "properties": {
                            "id": {"type": "integer"},
                            "chapter": {"type": "integer", "minimum": 1},
                            "verse": {"type": "integer", "minimum": 1},
                            "text": {"type": "string"},
                            "source": {"type": "object"},
                            "metadata": {"type": "object"}
                        }
                    }
                },
                "chapters": {"type": "object"},
                "statistics": {"type": "object"}
            }
        }
    
    def validate_content(self, content: str, format_type: str, options: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate JSON content.
        
        Args:
            content: JSON content to validate
            format_type: Should be 'parabible_json'
            options: Optional validation options
            
        Returns:
            ValidationResult with validation issues
        """
        options = options or {}
        issues = []
        metadata = {
            'validator': self.validator_name,
            'format_type': format_type,
            'jsonschema_available': JSONSCHEMA_AVAILABLE
        }
        
        # Parse JSON
        json_data, parse_issues = self._parse_json(content)
        issues.extend(parse_issues)
        
        if json_data is not None:
            # Schema validation
            if JSONSCHEMA_AVAILABLE and format_type == 'parabible_json':
                issues.extend(self._validate_schema(json_data))
            
            # Content-specific validation
            if format_type == 'parabible_json':
                issues.extend(self._validate_parabible_content(json_data))
            
            # General checks
            issues.extend(self._check_malayalam_content(json_data))
            issues.extend(self._check_data_consistency(json_data))
            
            # Update metadata
            metadata.update(self._get_json_metadata(json_data))
        
        success = len([i for i in issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) == 0
        
        return ValidationResult(
            success=success,
            format_type=format_type,
            issues=issues,
            metadata=metadata
        )
    
    def _parse_json(self, content: str) -> tuple[Optional[Dict], List[ValidationIssue]]:
        """Parse JSON content and return data and any parsing issues."""
        issues = []
        
        try:
            data = json.loads(content)
            return data, issues
            
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                code="JSON_PARSE_ERROR",
                message=f"JSON parsing failed: {e.msg}",
                line_number=e.lineno,
                context={'column': e.colno, 'position': e.pos}
            ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                code="JSON_PARSE_EXCEPTION",
                message=f"Unexpected JSON parsing error: {e}",
                context={'exception': str(e)}
            ))
        
        return None, issues
    
    def _validate_schema(self, data: Dict) -> List[ValidationIssue]:
        """Validate JSON against schema using jsonschema."""
        issues = []
        
        if not JSONSCHEMA_AVAILABLE:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="JSONSCHEMA_UNAVAILABLE",
                message="jsonschema library not available. Schema validation skipped.",
                suggestion="Install jsonschema for comprehensive JSON validation"
            ))
            return issues
        
        try:
            jsonschema.validate(data, self.parabible_schema)
            
        except jsonschema.ValidationError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="SCHEMA_VALIDATION_ERROR",
                message=f"Schema validation failed: {e.message}",
                location=f"$.{'.'.join(str(p) for p in e.absolute_path)}" if e.absolute_path else None,
                context={'schema_path': list(e.schema_path), 'validator': e.validator}
            ))
            
        except jsonschema.SchemaError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                code="SCHEMA_ERROR",
                message=f"Schema definition error: {e.message}",
                context={'schema_error': str(e)}
            ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="SCHEMA_VALIDATION_EXCEPTION",
                message=f"Schema validation failed with exception: {e}",
                context={'exception': str(e)}
            ))
        
        return issues
    
    def _validate_parabible_content(self, data: Dict) -> List[ValidationIssue]:
        """Validate ParaBible-specific content structure."""
        issues = []
        
        # Check required top-level keys
        required_keys = ['metadata', 'verses']
        for key in required_keys:
            if key not in data:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_REQUIRED_KEY",
                    message=f"Missing required key: {key}",
                    location=f"$.{key}",
                    suggestion=f"Add '{key}' to the root object"
                ))
        
        # Validate metadata
        if 'metadata' in data:
            metadata = data['metadata']
            if not isinstance(metadata, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_METADATA_TYPE",
                    message="Metadata must be an object",
                    location="$.metadata"
                ))
            else:
                # Check required metadata fields
                required_meta = ['book_id', 'title']
                for field in required_meta:
                    if field not in metadata:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="MISSING_METADATA_FIELD",
                            message=f"Missing required metadata field: {field}",
                            location=f"$.metadata.{field}"
                        ))
        
        # Validate verses
        if 'verses' in data:
            verses = data['verses']
            if not isinstance(verses, list):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_VERSES_TYPE",
                    message="Verses must be an array",
                    location="$.verses"
                ))
            else:
                issues.extend(self._validate_verses_array(verses))
        
        # Check chapters consistency if present
        if 'chapters' in data and 'verses' in data:
            issues.extend(self._validate_chapters_consistency(data['chapters'], data['verses']))
        
        # Check statistics if present
        if 'statistics' in data:
            issues.extend(self._validate_statistics(data['statistics'], data.get('verses', [])))
        
        return issues
    
    def _validate_verses_array(self, verses: List) -> List[ValidationIssue]:
        """Validate verses array structure."""
        issues = []
        
        if not verses:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="EMPTY_VERSES_ARRAY",
                message="Verses array is empty",
                location="$.verses"
            ))
            return issues
        
        seen_ids = set()
        chapter_verse_pairs = set()
        
        for i, verse in enumerate(verses):
            if not isinstance(verse, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_VERSE_TYPE",
                    message=f"Verse at index {i} must be an object",
                    location=f"$.verses[{i}]"
                ))
                continue
            
            # Check required fields
            required_verse_fields = ['id', 'chapter', 'verse', 'text']
            for field in required_verse_fields:
                if field not in verse:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_VERSE_FIELD",
                        message=f"Verse at index {i} missing field: {field}",
                        location=f"$.verses[{i}].{field}"
                    ))
            
            # Check ID uniqueness
            if 'id' in verse:
                verse_id = verse['id']
                if verse_id in seen_ids:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="DUPLICATE_VERSE_ID",
                        message=f"Duplicate verse ID: {verse_id}",
                        location=f"$.verses[{i}].id"
                    ))
                seen_ids.add(verse_id)
            
            # Check chapter/verse numbering
            if 'chapter' in verse and 'verse' in verse:
                chapter = verse['chapter']
                verse_num = verse['verse']
                
                if not isinstance(chapter, int) or chapter < 1:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_CHAPTER_NUMBER",
                        message=f"Invalid chapter number: {chapter}",
                        location=f"$.verses[{i}].chapter"
                    ))
                
                if not isinstance(verse_num, int) or verse_num < 1:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_VERSE_NUMBER",
                        message=f"Invalid verse number: {verse_num}",
                        location=f"$.verses[{i}].verse"
                    ))
                
                # Check for duplicate chapter:verse pairs
                pair = (chapter, verse_num)
                if pair in chapter_verse_pairs:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="DUPLICATE_CHAPTER_VERSE",
                        message=f"Duplicate chapter:verse pair: {chapter}:{verse_num}",
                        location=f"$.verses[{i}]"
                    ))
                chapter_verse_pairs.add(pair)
        
        return issues
    
    def _validate_chapters_consistency(self, chapters: Dict, verses: List) -> List[ValidationIssue]:
        """Validate consistency between chapters object and verses array."""
        issues = []
        
        if not isinstance(chapters, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_CHAPTERS_TYPE",
                message="Chapters must be an object",
                location="$.chapters"
            ))
            return issues
        
        # Get chapter numbers from verses
        verse_chapters = set()
        for verse in verses:
            if isinstance(verse, dict) and 'chapter' in verse:
                verse_chapters.add(verse['chapter'])
        
        # Check that all verse chapters are in chapters object
        for chapter_num in verse_chapters:
            if str(chapter_num) not in chapters:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_CHAPTER_OBJECT",
                    message=f"Chapter {chapter_num} found in verses but not in chapters object",
                    location=f"$.chapters.{chapter_num}"
                ))
        
        return issues
    
    def _validate_statistics(self, statistics: Dict, verses: List) -> List[ValidationIssue]:
        """Validate statistics object consistency."""
        issues = []
        
        if not isinstance(statistics, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_STATISTICS_TYPE",
                message="Statistics must be an object",
                location="$.statistics"
            ))
            return issues
        
        # Check verse count consistency
        if 'total_verses' in statistics:
            claimed_count = statistics['total_verses']
            actual_count = len(verses)
            
            if claimed_count != actual_count:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="INCONSISTENT_VERSE_COUNT",
                    message=f"Statistics claim {claimed_count} verses but found {actual_count}",
                    location="$.statistics.total_verses",
                    context={'claimed': claimed_count, 'actual': actual_count}
                ))
        
        return issues
    
    def _check_malayalam_content(self, data: Dict) -> List[ValidationIssue]:
        """Check for Malayalam content in JSON data."""
        issues = []
        
        # Extract all text values
        all_text = self._extract_text_values(data)
        combined_text = ' '.join(all_text)
        
        # Check for Malayalam characters
        malayalam_range = range(0x0D00, 0x0D80)
        has_malayalam = any(ord(char) in malayalam_range for char in combined_text)
        
        if not has_malayalam:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="NO_MALAYALAM_CONTENT",
                message="No Malayalam characters detected in JSON content",
                suggestion="Verify Malayalam text encoding"
            ))
        
        # Check language metadata consistency
        metadata = data.get('metadata', {})
        if has_malayalam and metadata.get('language') != 'ml':
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="LANGUAGE_METADATA_MISMATCH",
                message="Malayalam content detected but language not set to 'ml'",
                suggestion="Set metadata.language to 'ml'",
                context={'current_language': metadata.get('language')}
            ))
        
        return issues
    
    def _check_data_consistency(self, data: Dict) -> List[ValidationIssue]:
        """Check internal data consistency."""
        issues = []
        
        verses = data.get('verses', [])
        if not verses:
            return issues
        
        # Check verse ID sequence
        verse_ids = [v.get('id') for v in verses if isinstance(v, dict) and 'id' in v]
        if verse_ids and all(isinstance(vid, int) for vid in verse_ids):
            sorted_ids = sorted(verse_ids)
            expected_ids = list(range(1, len(verse_ids) + 1))
            
            if sorted_ids != expected_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="NON_SEQUENTIAL_VERSE_IDS",
                    message="Verse IDs are not sequential starting from 1",
                    context={'expected': expected_ids[:5], 'actual': sorted_ids[:5]}
                ))
        
        return issues
    
    def _extract_text_values(self, obj: Any) -> List[str]:
        """Recursively extract all text values from a JSON object."""
        text_values = []
        
        if isinstance(obj, str):
            text_values.append(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                text_values.extend(self._extract_text_values(value))
        elif isinstance(obj, list):
            for item in obj:
                text_values.extend(self._extract_text_values(item))
        
        return text_values
    
    def _get_json_metadata(self, data: Dict) -> Dict[str, Any]:
        """Extract metadata from JSON structure."""
        metadata = {}
        
        # Count top-level keys
        metadata['top_level_keys'] = list(data.keys())
        
        # Count verses
        verses = data.get('verses', [])
        metadata['verse_count'] = len(verses)
        
        # Count chapters
        chapters = set()
        for verse in verses:
            if isinstance(verse, dict) and 'chapter' in verse:
                chapters.add(verse['chapter'])
        metadata['chapter_count'] = len(chapters)
        
        # Text statistics
        all_text = self._extract_text_values(data)
        metadata['total_text_values'] = len(all_text)
        metadata['total_characters'] = sum(len(text) for text in all_text)
        
        # Size estimation
        import sys
        metadata['estimated_size_bytes'] = sys.getsizeof(json.dumps(data, ensure_ascii=False))
        
        return metadata