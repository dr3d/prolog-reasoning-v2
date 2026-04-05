#!/usr/bin/env python3
"""
Semantic Validator for Prolog Reasoning.

Validates IR representations before Prolog execution to ensure:
- Predicates are grounded in input
- Entities are consistent
- Constraints are fully captured

Prevents "false certainty" from incorrect symbolic representations.
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ir.schema import IR, QueryIR, AssertionIR, RuleIR


class ValidationError(Enum):
    """Types of validation errors."""
    UNDEFINED_ENTITY = "undefined_entity"
    UNGROUNDED_PREDICATE = "ungrounded_predicate"
    INCONSISTENT_FACTS = "inconsistent_facts"
    MISSING_CONSTRAINT = "missing_constraint"
    AMBIGUOUS_REFERENCE = "ambiguous_reference"


@dataclass
class ValidationIssue:
    """A validation issue found in IR."""
    error_type: ValidationError
    message: str
    severity: str = "error"  # "error", "warning"
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of semantic validation."""
    is_valid: bool
    issues: List[ValidationIssue]
    confidence: float  # 0.0-1.0


class SemanticValidator:
    """
    Validates semantic grounding of IR representations.
    
    Checks that symbolic representations are properly grounded in the
    original natural language input and knowledge base context.
    """
    
    def __init__(self, kb_entities: Optional[Set[str]] = None):
        """
        Initialize validator.
        
        Args:
            kb_entities: Known entities from knowledge base
        """
        self.kb_entities = kb_entities or set()
        
    def validate_ir(self, ir: IR, nl_input: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate IR representation against natural language input.
        
        Args:
            ir: The IR to validate
            nl_input: Original natural language query/input
            context: Additional context (e.g., previous conversation)
            
        Returns:
            ValidationResult with issues and confidence
        """
        issues = []
        confidence = 1.0
        
        # Extract entities and predicates from NL input
        nl_entities = self._extract_entities_from_nl(nl_input)
        nl_predicates = self._extract_predicates_from_nl(nl_input)
        
        # Validate based on IR type
        if isinstance(ir, QueryIR):
            issues.extend(self._validate_query_ir(ir, nl_entities, nl_predicates))
        elif isinstance(ir, AssertionIR):
            issues.extend(self._validate_assertion_ir(ir, nl_entities, nl_predicates))
        elif isinstance(ir, RuleIR):
            issues.extend(self._validate_rule_ir(ir, nl_entities, nl_predicates))
        
        # Check for undefined entities
        ir_entities = self._extract_entities_from_ir(ir)
        undefined = ir_entities - (nl_entities | self.kb_entities)
        for entity in undefined:
            issues.append(ValidationIssue(
                ValidationError.UNDEFINED_ENTITY,
                f"Entity '{entity}' is not mentioned in input or known in KB",
                suggestion=f"Add definition for '{entity}' or clarify in query"
            ))
            confidence *= 0.7
        
        # Check for ungrounded predicates
        if not nl_predicates and hasattr(ir, 'predicate'):
            # If no predicates in NL but IR has one, it might be ungrounded
            issues.append(ValidationIssue(
                ValidationError.UNGROUNDED_PREDICATE,
                f"Predicate '{ir.predicate}' not clearly grounded in input",
                severity="warning",
                suggestion="Ensure the predicate is explicitly mentioned or implied"
            ))
            confidence *= 0.8
        
        # Calculate overall validity
        is_valid = not any(issue.severity == "error" for issue in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence=confidence
        )
    
    def _extract_entities_from_nl(self, nl_input: str) -> Set[str]:
        """Extract entity names from natural language input."""
        # Simple extraction - in practice, use NLP or LLM
        words = set(nl_input.lower().split())
        # Filter for likely entities (proper nouns, etc.)
        entities = {word for word in words if len(word) > 2 and word not in {
            'the', 'and', 'are', 'who', 'what', 'how', 'when', 'where', 'why',
            'is', 'has', 'can', 'does', 'will', 'should', 'would', 'could'
        }}
        return entities
    
    def _extract_predicates_from_nl(self, nl_input: str) -> Set[str]:
        """Extract predicate hints from natural language input."""
        predicates = set()
        nl_lower = nl_input.lower()
        
        # Common predicate indicators
        if 'parent' in nl_lower:
            predicates.add('parent')
        if 'ancestor' in nl_lower:
            predicates.add('ancestor')
        if 'allowed' in nl_lower or 'permission' in nl_lower:
            predicates.add('allowed')
        if 'sibling' in nl_lower:
            predicates.add('sibling')
        if 'cross' in nl_lower or 'bridge' in nl_lower:
            predicates.add('can_cross')
            
        return predicates
    
    def _extract_entities_from_ir(self, ir: IR) -> Set[str]:
        """Extract entities from IR structure."""
        entities = set()
        
        def extract_from_arg(arg):
            if isinstance(arg, str) and not arg.startswith('?') and not (len(arg) == 1 and arg.isupper()):
                entities.add(arg.lower())
            elif isinstance(arg, dict) and 'term' in arg:
                # Nested term
                entities.add(arg['term'].lower())
                for sub_arg in arg.get('args', []):
                    extract_from_arg(sub_arg)
        
        for arg in ir.args:
            extract_from_arg(arg)
            
        return entities
    
    def _validate_query_ir(self, ir: QueryIR, nl_entities: Set[str], nl_predicates: Set[str]) -> List[ValidationIssue]:
        """Validate QueryIR specific rules."""
        issues = []
        
        # Check if query predicate is hinted in NL
        if ir.predicate not in nl_predicates:
            issues.append(ValidationIssue(
                ValidationError.UNGROUNDED_PREDICATE,
                f"Query predicate '{ir.predicate}' not clearly mentioned in input",
                severity="warning"
            ))
        
        return issues
    
    def _validate_assertion_ir(self, ir: AssertionIR, nl_entities: Set[str], nl_predicates: Set[str]) -> List[ValidationIssue]:
        """Validate AssertionIR specific rules."""
        issues = []
        
        # Assertions should be clearly stated
        if ir.predicate not in nl_predicates:
            issues.append(ValidationIssue(
                ValidationError.UNGROUNDED_PREDICATE,
                f"Assertion predicate '{ir.predicate}' not grounded in input",
                suggestion="Rephrase to clearly state the fact"
            ))
        
        return issues
    
    def _validate_rule_ir(self, ir: RuleIR, nl_entities: Set[str], nl_predicates: Set[str]) -> List[ValidationIssue]:
        """Validate RuleIR specific rules."""
        issues = []
        
        # Rules should have predicates mentioned
        rule_predicates = {ir.predicate}
        if ir.body:
            # Extract predicates from body (simple parsing)
            body_predicates = set()
            # Split by commas and parentheses to find predicates
            import re
            predicates = re.findall(r'\b\w+\s*\(', ir.body)
            body_predicates = {p.strip()[:-1] for p in predicates}  # Remove '('
            rule_predicates.update(body_predicates)
        
        unmentioned = rule_predicates - nl_predicates
        if unmentioned:
            issues.append(ValidationIssue(
                ValidationError.MISSING_CONSTRAINT,
                f"Rule uses predicates not mentioned in input: {unmentioned}",
                severity="warning"
            ))
        
        return issues