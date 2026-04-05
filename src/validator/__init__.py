#!/usr/bin/env python3
"""
Semantic Validation Layer.

Provides validation of IR representations to ensure proper grounding
in natural language inputs and knowledge base context.
"""

from .semantic_validator import SemanticValidator, ValidationResult, ValidationIssue, ValidationError

__all__ = [
    'SemanticValidator',
    'ValidationResult', 
    'ValidationIssue',
    'ValidationError'
]