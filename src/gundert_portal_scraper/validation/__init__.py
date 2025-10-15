"""Content validation framework for transformed outputs."""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in content."""
    
    severity: ValidationSeverity
    code: str
    message: str
    location: Optional[str] = None
    line_number: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'severity': self.severity.value,
            'code': self.code,
            'message': self.message,
            'location': self.location,
            'line_number': self.line_number,
            'context': self.context,
            'suggestion': self.suggestion
        }


@dataclass
class ValidationResult:
    """Results of content validation."""
    
    success: bool
    format_type: str
    issues: List[ValidationIssue]
    metadata: Dict[str, Any]
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for issue in self.issues if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL])
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)
    
    @property
    def info_count(self) -> int:
        """Count of info-level issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.INFO)
    
    @property
    def is_valid(self) -> bool:
        """Check if content is considered valid (no critical/error issues)."""
        return self.error_count == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'success': self.success,
            'format_type': self.format_type,
            'is_valid': self.is_valid,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'issues': [issue.to_dict() for issue in self.issues],
            'metadata': self.metadata
        }


class BaseValidator:
    """Base class for content validators."""
    
    def __init__(self):
        self.supported_formats: List[str] = []
        self.validator_name = self.__class__.__name__
        self.version = "1.0"
    
    def validate_content(self, content: str, format_type: str, options: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate string content.
        
        Args:
            content: Content to validate
            format_type: Type of format being validated
            options: Optional validation options
            
        Returns:
            ValidationResult with issues found
        """
        raise NotImplementedError("Subclasses must implement validate_content")
    
    def validate_file(self, file_path: Path, format_type: str, options: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate file content.
        
        Args:
            file_path: Path to file to validate
            format_type: Type of format being validated
            options: Optional validation options
            
        Returns:
            ValidationResult with issues found
        """
        # Special handling for binary formats
        if format_type == 'docx':
            # DOCX files are binary and need special handling
            return self.validate_docx_file(file_path, format_type, options)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.validate_content(content, format_type, options)
        except Exception as e:
            return ValidationResult(
                success=False,
                format_type=format_type,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    code="FILE_READ_ERROR",
                    message=f"Could not read file: {e}",
                    location=str(file_path)
                )],
                metadata={'validator': self.validator_name, 'file_path': str(file_path)}
            )
    
    def validate_docx_file(self, file_path: Path, format_type: str, options: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Special handling for DOCX file validation."""
        # For DOCX, delegate directly to the validator's validate_file method
        if format_type in self.format_mappings:
            validator_names = self.format_mappings[format_type]
            if validator_names:
                validator = self.validators[validator_names[0]]
                return validator.validate_file(file_path, format_type, options)
        
        return ValidationResult(
            success=False,
            format_type=format_type,
            issues=[ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="NO_VALIDATOR",
                message=f"No validator available for DOCX format"
            )],
            metadata={'file_path': str(file_path)}
        )
    
    def supports_format(self, format_type: str) -> bool:
        """Check if this validator supports the given format."""
        return format_type in self.supported_formats


class ValidationEngine:
    """Main validation engine that coordinates multiple validators."""
    
    def __init__(self):
        self.validators: Dict[str, BaseValidator] = {}
        self.format_mappings: Dict[str, List[str]] = {}
    
    def register_validator(self, validator: BaseValidator, formats: List[str]):
        """Register a validator for specific formats.
        
        Args:
            validator: Validator instance
            formats: List of formats this validator handles
        """
        validator.supported_formats = formats
        self.validators[validator.validator_name] = validator
        
        for format_type in formats:
            if format_type not in self.format_mappings:
                self.format_mappings[format_type] = []
            self.format_mappings[format_type].append(validator.validator_name)
        
        logger.info(f"Registered {validator.validator_name} for formats: {formats}")
    
    def validate_content(self, content: str, format_type: str, options: Optional[Dict[str, Any]] = None) -> List[ValidationResult]:
        """Validate content using all applicable validators.
        
        Args:
            content: Content to validate
            format_type: Format type
            options: Optional validation options
            
        Returns:
            List of ValidationResult from all applicable validators
        """
        results = []
        
        if format_type not in self.format_mappings:
            logger.warning(f"No validators registered for format: {format_type}")
            return [ValidationResult(
                success=False,
                format_type=format_type,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="NO_VALIDATOR",
                    message=f"No validators available for format: {format_type}"
                )],
                metadata={'available_formats': list(self.format_mappings.keys())}
            )]
        
        for validator_name in self.format_mappings[format_type]:
            validator = self.validators[validator_name]
            try:
                result = validator.validate_content(content, format_type, options)
                results.append(result)
            except Exception as e:
                logger.error(f"Validation failed with {validator_name}: {e}")
                results.append(ValidationResult(
                    success=False,
                    format_type=format_type,
                    issues=[ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="VALIDATOR_ERROR",
                        message=f"Validator {validator_name} failed: {e}"
                    )],
                    metadata={'validator': validator_name, 'error': str(e)}
                ))
        
        return results
    
    def validate_file(self, file_path: Path, format_type: str, options: Optional[Dict[str, Any]] = None) -> List[ValidationResult]:
        """Validate file using all applicable validators.
        
        Args:
            file_path: Path to file to validate
            format_type: Format type
            options: Optional validation options
            
        Returns:
            List of ValidationResult from all applicable validators
        """
        results = []
        
        if format_type not in self.format_mappings:
            logger.warning(f"No validators registered for format: {format_type}")
            return [ValidationResult(
                success=False,
                format_type=format_type,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="NO_VALIDATOR",
                    message=f"No validators available for format: {format_type}"
                )],
                metadata={'available_formats': list(self.format_mappings.keys())}
            )]
        
        for validator_name in self.format_mappings[format_type]:
            validator = self.validators[validator_name]
            try:
                # Use validator's validate_file method for proper handling
                result = validator.validate_file(file_path, format_type, options)
                results.append(result)
            except Exception as e:
                logger.error(f"File validation failed with {validator_name}: {e}")
                results.append(ValidationResult(
                    success=False,
                    format_type=format_type,
                    issues=[ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="VALIDATOR_ERROR",
                        message=f"Validator {validator_name} failed: {e}"
                    )],
                    metadata={'validator': validator_name, 'error': str(e), 'file_path': str(file_path)}
                ))
        
        return results
    
    def get_supported_formats(self) -> List[str]:
        """Get list of all supported formats."""
        return list(self.format_mappings.keys())
    
    def get_validators_for_format(self, format_type: str) -> List[str]:
        """Get list of validator names for a format."""
        return self.format_mappings.get(format_type, [])


def create_validation_engine() -> ValidationEngine:
    """Create and configure the validation engine with all available validators."""
    engine = ValidationEngine()
    
    # Import and register validators
    try:
        from .validators.usfm_validator import USFMValidator
        engine.register_validator(USFMValidator(), ['usfm'])
    except ImportError:
        logger.warning("USFM validator not available")
    
    try:
        from .validators.xml_validator import XMLValidator
        engine.register_validator(XMLValidator(), ['tei_xml', 'bibleml'])
    except ImportError:
        logger.warning("XML validator not available")
    
    try:
        from .validators.json_validator import JSONValidator
        engine.register_validator(JSONValidator(), ['parabible_json'])
    except ImportError:
        logger.warning("JSON validator not available")
    
    try:
        from .validators.docx_validator import DOCXValidator
        engine.register_validator(DOCXValidator(), ['docx'])
    except ImportError:
        logger.warning("DOCX validator not available")
    
    return engine