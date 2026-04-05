"""
Test suite for Semantic Grounding and Validation components.

Tests success and failure scenarios for:
- Semantic parsing
- IR validation
- Semantic validator
- Integrated skill functionality

Run: pytest tests/test_semantic.py -v
"""

import sys
import pytest
from unittest.mock import Mock

sys.path.insert(0, "src")

from parser.semantic import SemanticGrounder, SemanticPrologSkill, ParsedQuery, QueryIntent
from validator import SemanticValidator, ValidationResult, ValidationError
from ir.schema import QueryIR, AssertionIR, RuleIR


class TestSemanticValidator:
    """Test Semantic Validator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SemanticValidator(kb_entities={"john", "alice", "bob", "admin", "read", "write"})

    def test_valid_query_validation(self):
        """Test validation of a valid query."""
        ir = QueryIR(predicate="parent", args=["john", "X"], confidence=0.9)
        nl_input = "Who is John's parent?"

        result = self.validator.validate_ir(ir, nl_input)

        assert result.is_valid
        assert result.confidence == 1.0
        assert len(result.issues) == 0

    def test_undefined_entity_validation(self):
        """Test validation catches undefined entities."""
        ir = QueryIR(predicate="parent", args=["charlie", "X"], confidence=0.9)
        nl_input = "Who is Charlie's parent?"

        result = self.validator.validate_ir(ir, nl_input)

        assert not result.is_valid
        assert result.confidence < 1.0
        assert len(result.issues) > 0

        # Check for undefined entity error
        entity_errors = [issue for issue in result.issues if issue.error_type == ValidationError.UNDEFINED_ENTITY]
        assert len(entity_errors) > 0
        assert "charlie" in entity_errors[0].message

    def test_ungrounded_predicate_validation(self):
        """Test validation warns about ungrounded predicates."""
        ir = QueryIR(predicate="can_fly", args=["alice", "X"], confidence=0.8)
        nl_input = "Can Alice fly?"

        result = self.validator.validate_ir(ir, nl_input)

        assert result.is_valid  # Warning, not error
        assert result.confidence < 1.0
        assert len(result.issues) > 0

        # Check for ungrounded predicate warning
        predicate_warnings = [issue for issue in result.issues if issue.error_type == ValidationError.UNGROUNDED_PREDICATE]
        assert len(predicate_warnings) > 0

    def test_assertion_validation(self):
        """Test validation of assertions."""
        ir = AssertionIR(predicate="parent", args=["john", "alice"], confidence=0.95)
        nl_input = "John is Alice's parent."

        result = self.validator.validate_ir(ir, nl_input)

        assert result.is_valid
        assert result.confidence == 1.0

    def test_rule_validation(self):
        """Test validation of rules."""
        ir = RuleIR(predicate="ancestor", args=["X", "Y"], body="parent(X, Y)", confidence=0.8)
        nl_input = "An ancestor is a parent."

        result = self.validator.validate_ir(ir, nl_input)

        assert result.is_valid
        assert result.confidence == 1.0


class TestSemanticGrounder:
    """Test Semantic Grounder functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.grounder = SemanticGrounder()

    def test_parse_valid_family_query(self):
        """Test parsing a valid family relationship query."""
        query = "Who is John's parent?"
        parsed = self.grounder.ground_query(query)

        assert parsed.intent == QueryIntent.VARIABLE_QUERY
        assert parsed.ir.predicate == "parent"
        assert parsed.ir.args == ["john", "X"]
        assert parsed.confidence > 0.8
        assert parsed.domain == "family"

    def test_parse_valid_access_query(self):
        """Test parsing a valid access control query."""
        query = "Is Alice allowed to read?"
        parsed = self.grounder.ground_query(query)

        assert parsed.intent == QueryIntent.FACT_CHECK
        assert parsed.ir.predicate == "allowed"
        assert parsed.ir.args == ["alice", "read"]
        assert parsed.confidence > 0.9
        assert parsed.domain == "access"

    def test_parse_assertion(self):
        """Test parsing an assertion."""
        query = "John is Alice's parent."
        parsed = self.grounder.ground_query(query)

        assert parsed.intent == QueryIntent.ASSERTION
        assert parsed.ir.predicate == "parent"
        assert parsed.ir.args == ["john", "alice"]
        assert parsed.confidence > 0.9

    def test_parse_unknown_query(self):
        """Test parsing falls back for unknown queries."""
        query = "What is the meaning of life?"
        parsed = self.grounder.ground_query(query)

        assert parsed.intent == QueryIntent.VARIABLE_QUERY
        assert parsed.ir.predicate == "unknown"
        assert parsed.confidence < 0.2

    def test_prolog_conversion(self):
        """Test conversion to Prolog syntax."""
        parsed = ParsedQuery(
            intent=QueryIntent.VARIABLE_QUERY,
            ir=QueryIR(predicate="parent", args=["john", "X"]),
            confidence=0.9,
            raw_query="Who is John's parent?"
        )

        prolog = self.grounder.to_prolog_query(parsed)
        assert prolog == "parent(john, X)."


class TestSemanticPrologSkill:
    """Test integrated Semantic Prolog Skill."""

    def setup_method(self):
        """Set up test fixtures."""
        self.skill = SemanticPrologSkill()

    def test_valid_query_success(self):
        """Test successful execution of valid query."""
        result = self.skill.query_nl("Who is John's parent?")

        assert result["success"]
        assert result["parsing_confidence"] > 0.8
        assert result["validation_confidence"] == 1.0
        assert "alice" in str(result["bindings"])
        assert "validation_errors" not in result

    def test_invalid_query_validation_failure(self):
        """Test validation failure blocks execution."""
        result = self.skill.query_nl("Who is Charlie's parent?")

        assert not result["success"]
        assert "validation_errors" in result
        assert len(result["validation_errors"]) > 0
        assert result["validation_confidence"] < 1.0
        assert "charlie" in result["validation_errors"][0]["message"]

    def test_access_control_query(self):
        """Test access control queries work."""
        result = self.skill.query_nl("Is Alice allowed to read?")

        assert result["success"]
        assert result["domain"] == "access"
        assert result["parsing_confidence"] > 0.9

    def test_fallback_query_handling(self):
        """Test fallback handling for unknown queries."""
        result = self.skill.query_nl("What is the weather?")

        # Should still attempt validation but likely fail or have low confidence
        assert "validation_confidence" in result
        assert result["parsing_confidence"] < 0.2


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.skill = SemanticPrologSkill()

    def test_family_relationships_workflow(self):
        """Test complete workflow for family relationships."""
        # Valid query
        result1 = self.skill.query_nl("Who is John's parent?")
        assert result1["success"]
        assert str(result1["bindings"]["X"]) == "alice"

        # Another valid query
        result2 = self.skill.query_nl("Is Alice allowed to read?")
        assert result2["success"]

        # Invalid query should be caught
        result3 = self.skill.query_nl("Who is Charlie's parent?")
        assert not result3["success"]
        assert "validation_errors" in result3

    def test_validation_prevents_bad_execution(self):
        """Test that validation prevents execution of problematic queries."""
        # This should be caught by validation
        result = self.skill.query_nl("Can Superman fly to the moon?")

        # Should either fail validation or have very low confidence
        assert ("validation_errors" in result or
                result["validation_confidence"] < 0.5 or
                result["parsing_confidence"] < 0.2)

    def test_confidence_degradation(self):
        """Test that confidence degrades appropriately for issues."""
        # Valid query - high confidence
        valid = self.skill.query_nl("Who is John's parent?")
        assert valid["validation_confidence"] == 1.0
        assert valid["parsing_confidence"] > 0.8

        # Invalid query - lower confidence
        invalid = self.skill.query_nl("Who is Charlie's parent?")
        assert invalid["validation_confidence"] < 1.0
        assert invalid["parsing_confidence"] > 0.8  # Parsing worked, validation failed

        # Unknown query - low parsing confidence
        unknown = self.skill.query_nl("What is quantum physics?")
        assert unknown["parsing_confidence"] < 0.2


if __name__ == "__main__":
    pytest.main([__file__])