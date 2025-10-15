"""Base transformation framework with plugin architecture."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union
from pathlib import Path
import importlib
import inspect
from datetime import datetime

from ..storage.schemas import BookStorage, PageContent
from ..core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class LineMapping:
    """Represents the mapping between original lines and transformed output."""
    
    def __init__(self):
        self.mappings: List[Dict[str, Any]] = []
    
    def add_mapping(self, original_page: int, original_line: int, 
                   transformed_location: str, context: Dict[str, Any] = None):
        """Add a line mapping entry.
        
        Args:
            original_page: Original page number
            original_line: Original line number
            transformed_location: Location in transformed output (e.g., "chapter_1_verse_3")
            context: Additional context information
        """
        mapping = {
            'original_page': original_page,
            'original_line': original_line,
            'transformed_location': transformed_location,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }
        self.mappings.append(mapping)
    
    def get_mappings_for_page(self, page_number: int) -> List[Dict[str, Any]]:
        """Get all mappings for a specific page."""
        return [m for m in self.mappings if m['original_page'] == page_number]
    
    def find_original_location(self, transformed_location: str) -> Optional[Dict[str, Any]]:
        """Find original location from transformed location."""
        for mapping in self.mappings:
            if mapping['transformed_location'] == transformed_location:
                return {
                    'page': mapping['original_page'],
                    'line': mapping['original_line'],
                    'context': mapping['context']
                }
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'mappings': self.mappings,
            'total_mappings': len(self.mappings),
            'pages_covered': len(set(m['original_page'] for m in self.mappings))
        }


class TransformationResult:
    """Result of a transformation operation."""
    
    def __init__(self, success: bool, output_format: str, content: str = None, 
                 file_path: str = None, line_mappings: LineMapping = None, 
                 metadata: Dict[str, Any] = None, errors: List[str] = None):
        self.success = success
        self.output_format = output_format
        self.content = content
        self.file_path = file_path
        self.line_mappings = line_mappings or LineMapping()
        self.metadata = metadata or {}
        self.errors = errors or []
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'output_format': self.output_format,
            'file_path': self.file_path,
            'line_mappings': self.line_mappings.to_dict(),
            'metadata': self.metadata,
            'errors': self.errors,
            'timestamp': self.timestamp,
            'content_preview': self.content[:500] + "..." if self.content and len(self.content) > 500 else self.content
        }


class BaseTransformer(ABC):
    """Base class for all content transformers."""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.output_format = "unknown"
        self.supported_content_types = ["all"]  # Override in subclasses
        self.line_mappings = LineMapping()
    
    @abstractmethod
    def transform(self, book_storage: BookStorage, output_path: Optional[Path] = None, 
                 options: Dict[str, Any] = None) -> TransformationResult:
        """Transform book content to target format.
        
        Args:
            book_storage: Source book storage object
            output_path: Optional path for output file
            options: Transformation options
            
        Returns:
            TransformationResult with success status and output
        """
        pass
    
    def is_compatible(self, book_storage: BookStorage) -> bool:
        """Check if this transformer is compatible with the book content.
        
        Args:
            book_storage: Book storage to check
            
        Returns:
            True if compatible
        """
        if "all" in self.supported_content_types:
            return True
        
        content_type = book_storage.book_metadata.content_type
        return content_type in self.supported_content_types if content_type else True
    
    def validate_input(self, book_storage: BookStorage) -> List[str]:
        """Validate input book storage for transformation.
        
        Args:
            book_storage: Book storage to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not book_storage.pages:
            errors.append("No pages found in book storage")
        
        # Check for required content
        pages_with_content = sum(1 for page in book_storage.pages 
                               if page.transcript_info.get('available'))
        
        if pages_with_content == 0:
            errors.append("No pages with transcript content found")
        
        return errors
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get transformer metadata."""
        return {
            'name': self.name,
            'output_format': self.output_format,
            'supported_content_types': self.supported_content_types,
            'version': getattr(self, 'version', '1.0')
        }


class TransformationEngine:
    """Main engine for managing and executing transformations."""
    
    def __init__(self):
        self.transformers: Dict[str, Type[BaseTransformer]] = {}
        self.transformation_history: List[Dict[str, Any]] = []
        
        # Register built-in transformers
        self._register_builtin_transformers()
    
    def register_transformer(self, transformer_class: Type[BaseTransformer]):
        """Register a transformer class.
        
        Args:
            transformer_class: Transformer class to register
        """
        if not issubclass(transformer_class, BaseTransformer):
            raise TransformationError("registration", "Transformer must inherit from BaseTransformer")
        
        # Create instance to get metadata
        instance = transformer_class()
        self.transformers[instance.output_format] = transformer_class
        
        logger.info(f"Registered transformer: {instance.name} ({instance.output_format})")
    
    def get_available_transformers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available transformers.
        
        Returns:
            Dictionary mapping format names to transformer metadata
        """
        available = {}
        
        for format_name, transformer_class in self.transformers.items():
            instance = transformer_class()
            available[format_name] = instance.get_metadata()
        
        return available
    
    def get_compatible_transformers(self, book_storage: BookStorage) -> List[str]:
        """Get list of transformers compatible with the given book.
        
        Args:
            book_storage: Book storage to check compatibility
            
        Returns:
            List of compatible transformer format names
        """
        compatible = []
        
        for format_name, transformer_class in self.transformers.items():
            instance = transformer_class()
            if instance.is_compatible(book_storage):
                compatible.append(format_name)
        
        return compatible
    
    def transform(self, book_storage: BookStorage, output_format: str, 
                 output_path: Optional[Path] = None, 
                 options: Dict[str, Any] = None) -> TransformationResult:
        """Execute a transformation.
        
        Args:
            book_storage: Source book storage
            output_format: Target output format
            output_path: Optional output file path
            options: Transformation options
            
        Returns:
            TransformationResult
        """
        if output_format not in self.transformers:
            available = list(self.transformers.keys())
            raise TransformationError("transformation", 
                                    f"Unknown format '{output_format}'. Available: {available}")
        
        transformer_class = self.transformers[output_format]
        transformer = transformer_class()
        
        # Validate compatibility
        if not transformer.is_compatible(book_storage):
            raise TransformationError("compatibility", 
                                    f"Transformer '{output_format}' not compatible with content type '{book_storage.book_metadata.content_type}'")
        
        # Validate input
        validation_errors = transformer.validate_input(book_storage)
        if validation_errors:
            raise TransformationError("validation", f"Input validation failed: {'; '.join(validation_errors)}")
        
        try:
            logger.info(f"Starting transformation to {output_format}")
            result = transformer.transform(book_storage, output_path, options or {})
            
            # Record transformation history
            history_entry = {
                'book_id': book_storage.book_metadata.book_id,
                'output_format': output_format,
                'success': result.success,
                'timestamp': result.timestamp,
                'file_path': result.file_path,
                'line_mappings_count': len(result.line_mappings.mappings),
                'errors': result.errors
            }
            self.transformation_history.append(history_entry)
            
            logger.info(f"Transformation completed: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            
            # Record failed transformation
            error_result = TransformationResult(
                success=False,
                output_format=output_format,
                errors=[str(e)]
            )
            
            history_entry = {
                'book_id': book_storage.book_metadata.book_id,
                'output_format': output_format,
                'success': False,
                'timestamp': error_result.timestamp,
                'errors': [str(e)]
            }
            self.transformation_history.append(history_entry)
            
            raise TransformationError("execution", f"Transformation failed: {str(e)}")
    
    def batch_transform(self, book_storage: BookStorage, output_formats: List[str],
                       output_directory: Path, 
                       options: Dict[str, Any] = None) -> Dict[str, TransformationResult]:
        """Execute multiple transformations in batch.
        
        Args:
            book_storage: Source book storage
            output_formats: List of target formats
            output_directory: Directory for output files
            options: Global transformation options
            
        Returns:
            Dictionary mapping format names to results
        """
        output_directory.mkdir(parents=True, exist_ok=True)
        results = {}
        
        for output_format in output_formats:
            try:
                # Generate output path
                book_id = book_storage.book_metadata.book_id
                extension = self._get_file_extension(output_format)
                output_path = output_directory / f"{book_id}.{extension}"
                
                result = self.transform(book_storage, output_format, output_path, options)
                results[output_format] = result
                
            except Exception as e:
                logger.error(f"Batch transformation failed for {output_format}: {e}")
                results[output_format] = TransformationResult(
                    success=False,
                    output_format=output_format,
                    errors=[str(e)]
                )
        
        return results
    
    def get_transformation_history(self, book_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get transformation history.
        
        Args:
            book_id: Optional filter by book ID
            
        Returns:
            List of transformation history entries
        """
        if book_id:
            return [entry for entry in self.transformation_history 
                   if entry.get('book_id') == book_id]
        
        return self.transformation_history.copy()
    
    def _register_builtin_transformers(self):
        """Register built-in transformers."""
        # Import and register built-in transformers
        from .plugins import (
            USFMTransformer, DOCXTransformer, AdvancedTEITransformer,
            ParaBibleTransformer, BibleMLTransformer
        )
        
        builtin_transformers = [
            USFMTransformer,
            DOCXTransformer, 
            AdvancedTEITransformer,
            ParaBibleTransformer,
            BibleMLTransformer
        ]
        
        for transformer_class in builtin_transformers:
            try:
                self.register_transformer(transformer_class)
            except Exception as e:
                logger.warning(f"Failed to register builtin transformer {transformer_class.__name__}: {e}")
    
    def _get_file_extension(self, output_format: str) -> str:
        """Get appropriate file extension for format."""
        extension_mapping = {
            'usfm': 'usfm',
            'docx': 'docx',
            'tei_xml': 'xml',
            'parabible_json': 'json',
            'bibleml': 'xml',
            'html': 'html',
            'epub': 'epub'
        }
        
        return extension_mapping.get(output_format, 'txt')


class TransformationRegistry:
    """Registry for managing transformation plugins."""
    
    def __init__(self):
        self.plugins_directory = Path(__file__).parent / "plugins"
        self.plugins_directory.mkdir(exist_ok=True)
    
    def discover_plugins(self) -> List[Type[BaseTransformer]]:
        """Discover transformer plugins in the plugins directory.
        
        Returns:
            List of discovered transformer classes
        """
        discovered = []
        
        if not self.plugins_directory.exists():
            return discovered
        
        # Look for Python files in plugins directory
        for plugin_file in self.plugins_directory.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip private files
            
            try:
                # Import the module
                module_name = f"gundert_portal_scraper.transformations.plugins.{plugin_file.stem}"
                module = importlib.import_module(module_name)
                
                # Find transformer classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseTransformer) and 
                        obj != BaseTransformer):
                        discovered.append(obj)
                        logger.info(f"Discovered plugin transformer: {name}")
                
            except Exception as e:
                logger.warning(f"Failed to load plugin {plugin_file.name}: {e}")
        
        return discovered
    
    def install_plugin(self, plugin_code: str, plugin_name: str) -> bool:
        """Install a new plugin from code.
        
        Args:
            plugin_code: Python code for the plugin
            plugin_name: Name for the plugin file
            
        Returns:
            True if installed successfully
        """
        try:
            plugin_file = self.plugins_directory / f"{plugin_name}.py"
            
            with open(plugin_file, 'w', encoding='utf-8') as f:
                f.write(plugin_code)
            
            logger.info(f"Installed plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install plugin {plugin_name}: {e}")
            return False