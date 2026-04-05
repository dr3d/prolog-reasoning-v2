"""
Test suite for Failure Explanation Layer.

Test that failures are explained clearly and helpfully for newcomers.

Run: pytest tests/test_failures.py -v
"""

import sys
import pytest

sys.path.insert(0, "src")

from explain.failure_translator import FailureTranslator, FailureType, FailureExplanation
from validator import ValidationIssue, ValidationError


class TestFailureTranslator:
    """Test FailureTranslator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = FailureTranslator(
            kb_entities={"john", "alice", "bob", "admin", "read", "write"}
        )

    def test_explain_undefined_entity(self):
        """Test explanation of undefined entity error."""
        issue = ValidationIssue(
            error_type=ValidationError.UNDEFINED_ENTITY,
            message="Entity 'charlie' is not mentioned in input or known in KB",
            suggestion="Add definition for 'charlie' or clarify in query"
        )

        explanation = self.translator.explain_validation_error(issue)

        assert not explanation.failure_type == FailureType.SYNTAX_ERROR
        assert "charlie" in explanation.core_message.lower() or "charlie" in str(explanation)
        assert explanation.confidence == 0.9

    def test_undefined_entity_with_did_you_mean(self):
        """Test that similar entities are suggested."""
        issue = ValidationIssue(
            error_type=ValidationError.UNDEFINED_ENTITY,
            message="Entity 'alice_smith' is not mentioned in input or known in KB"
        )

        explanation = self.translator.explain_validation_error(issue)

        # Should suggest Alice since it's similar
        assert "alice" in explanation.suggestion.lower() or "Alice" in explanation.suggestion

    def test_explain_ungrounded_predicate(self):
        """Test explanation of ungrounded predicate warning."""
        issue = ValidationIssue(
            error_type=ValidationError.UNGROUNDED_PREDICATE,
            message="Predicate 'can_fly' not clearly mentioned in input",
            severity="warning"
        )

        explanation = self.translator.explain_validation_error(issue)

        assert explanation.failure_type == FailureType.UNGROUNDED_PREDICATE
        assert explanation.confidence == 0.7

    def test_explain_query_failure(self):
        """Test explanation for query that returned no solutions."""
        query = "parent(charlie, X)"
        
        explanation = self.translator.explain_query_failure(query)

        assert explanation.failure_type == FailureType.QUERY_FAILED
        assert "parent" in explanation.detailed_explanation.lower()
        assert explanation.suggestion  # Should have a suggestion

    def test_explain_timeout(self):
        """Test explanation for timeout."""
        query = "ancestor(X, Y)"
        depth_limit = 100

        explanation = self.translator.explain_timeout(query, depth_limit)

        assert explanation.failure_type == FailureType.TIMEOUT
        assert "too long" in explanation.core_message.lower()
        assert "100" in str(explanation)

    def test_explain_ambiguous_input(self):
        """Test explanation for ambiguous input."""
        input_str = "Is she the parent?"
        options = [
            "Is Alice the parent of someone?",
            "Is Alice a parent?"
        ]

        explanation = self.translator.explain_ambiguous_input(input_str, options)

        assert explanation.failure_type == FailureType.AMBIGUOUS_INPUT
        assert "not sure" in explanation.core_message.lower()
        assert explanation.confidence == 0.5

    def test_format_for_human(self):
        """Test human-friendly formatting."""
        explanation = FailureExplanation(
            failure_type=FailureType.UNDEFINED_ENTITY,
            core_message="I don't know who Charlie is",
            detailed_explanation="Charlie wasn't mentioned",
            suggestion="Tell me about Charlie first"
        )

        formatted = self.translator.format_for_human(explanation)

        assert "❌" in formatted  # Should have emoji
        assert "I don't know" in formatted
        assert "💡" in formatted  # Should have suggestion emoji

    def test_format_for_llm(self):
        """Test LLM-friendly formatting."""
        explanation = FailureExplanation(
            failure_type=FailureType.UNDEFINED_ENTITY,
            core_message="I don't know who Charlie is",
            detailed_explanation="Charlie wasn't mentioned",
            suggestion="Tell me about Charlie first",
            confidence=0.9
        )

        formatted = self.translator.format_for_llm(explanation)

        assert "FAILURE:" in formatted
        assert "undefined_entity" in formatted
        assert "Confidence: 0.90" in formatted

    def test_extract_entity_name_from_message(self):
        """Test entity name extraction from error messages."""
        message = "Entity 'charlie' is not mentioned"
        
        entity = self.translator._extract_entity_name(message)
        
        assert entity == "charlie"

    def test_find_similar_entities_exact_match(self):
        """Test finding exact matches of entities."""
        similar = self.translator._find_similar_entities("alice", self.translator.kb_entities)
        
        assert "alice" in similar

    def test_find_similar_entities_substring(self):
        """Test finding substring matches."""
        similar = self.translator._find_similar_entities("alic", self.translator.kb_entities)
        
        assert "alice" in similar

    def test_find_similar_entities_first_letter(self):
        """Test finding similar by first letter."""
        similar = self.translator._find_similar_entities("alex", self.translator.kb_entities)
        
        # Should find alice (starts with 'a')
        assert any(s.startswith('a') for s in similar)

    def test_no_similar_entities(self):
        """Test when no similar entities exist."""
        similar = self.translator._find_similar_entities("xyz", self.translator.kb_entities)
        
        assert len(similar) == 0


class TestFailureExplanationIntegration:
    """Test failure explanations in context of actual errors."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = FailureTranslator(
            kb_entities={"john", "alice", "bob", "admin", "read", "write"}
        )

    def test_undefined_entity_full_explanation(self):
        """Test complete flow for undefined entity."""
        issue = ValidationIssue(
            error_type=ValidationError.UNDEFINED_ENTITY,
            message="Entity 'david' is not mentioned in input or known in KB",
            suggestion="Add definition for 'david'"
        )

        explanation = self.translator.explain_validation_error(issue)
        human_format = self.translator.format_for_human(explanation)
        llm_format = self.translator.format_for_llm(explanation)

        # Check both formats work
        assert "❌" in human_format
        assert "FAILURE:" in llm_format
        assert explanation.suggestion

    def test_query_failure_with_unknown_predicate(self):
        """Test query failure explanation with unknown predicate."""
        explanation = self.translator.explain_query_failure("can_fly(alice, X)")

        assert explanation.failure_type == FailureType.QUERY_FAILED
        assert "can_fly" in explanation.detailed_explanation.lower()
        assert explanation.suggestion

    def test_helpful_suggestions_provided(self):
        """Test that all failure explanations include suggestions."""
        issues = [
            ValidationIssue(
                error_type=ValidationError.UNDEFINED_ENTITY,
                message="Entity 'unknown' is not mentioned"
            ),
            ValidationIssue(
                error_type=ValidationError.UNGROUNDED_PREDICATE,
                message="Predicate 'weird_thing' not grounded"
            ),
        ]

        for issue in issues:
            explanation = self.translator.explain_validation_error(issue)
            assert explanation.suggestion, f"No suggestion for {issue.error_type}"
            assert len(explanation.suggestion) > 10  # Should be substantial


if __name__ == "__main__":
    pytest.main([__file__, "-v"])