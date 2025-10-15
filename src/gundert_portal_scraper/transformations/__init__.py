"""Transformation framework for content format conversion."""

from .framework import (
    BaseTransformer,
    TransformationResult,
    TransformationEngine,
    TransformationRegistry,
    LineMapping
)

try:
    from .plugins import (
        USFMTransformer,
        DOCXTransformer,
        AdvancedTEITransformer,
        ParaBibleTransformer,
        BibleMLTransformer
    )
    PLUGINS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some transformation plugins not available: {e}")
    PLUGINS_AVAILABLE = False

__all__ = [
    'BaseTransformer',
    'TransformationResult', 
    'TransformationEngine',
    'TransformationRegistry',
    'LineMapping'
]

if PLUGINS_AVAILABLE:
    __all__.extend([
        'USFMTransformer',
        'DOCXTransformer',
        'AdvancedTEITransformer',
        'ParaBibleTransformer',
        'BibleMLTransformer'
    ])


def create_transformation_engine():
    """Create a transformation engine with all available transformers.
    
    Returns:
        TransformationEngine: Configured transformation engine
    """
    return TransformationEngine()


def get_available_formats():
    """Get list of available transformation formats.
    
    Returns:
        List[str]: List of available format names
    """
    engine = create_transformation_engine()
    return list(engine.get_available_transformers().keys())