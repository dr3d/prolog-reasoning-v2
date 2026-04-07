import sys
from pathlib import Path

sys.path.insert(0, "src")

from write_path.validator import PredicateProposalValidator


def _validator() -> PredicateProposalValidator:
    repo_root = Path(__file__).resolve().parent.parent
    return PredicateProposalValidator(str(repo_root / "data" / "predicate_registry.json"))


def test_literal_fact_validates():
    validator = _validator()
    result = validator.evaluate(
        "parent(ann, scott).",
        kind="hard_fact",
        needs_speaker_resolution=False,
    )
    assert result["status"] == "valid"
    assert result["candidate"]["canonical_predicate"] == "parent"
    assert result["candidate"]["normalized_fact"] == "parent(ann, scott)."


def test_first_person_requires_clarification():
    validator = _validator()
    result = validator.evaluate(
        "My mother was Ann.",
        kind="hard_fact",
        needs_speaker_resolution=True,
    )
    assert result["status"] == "needs_clarification"
    assert result["candidate"]["canonical_predicate"] == "parent"
    assert "<speaker>" in result["candidate"]["arguments"]


def test_unknown_predicate_needs_clarification():
    validator = _validator()
    result = validator.evaluate(
        "enjoys(john, pizza).",
        kind="hard_fact",
        needs_speaker_resolution=False,
    )
    assert result["status"] == "needs_clarification"
    assert any("unknown predicate alias" in issue for issue in result["issues"])


def test_non_fact_kind_rejected():
    validator = _validator()
    result = validator.evaluate(
        "Who is John's parent?",
        kind="query",
        needs_speaker_resolution=False,
    )
    assert result["status"] == "reject"


def test_prolog_literal_allowed_even_if_classifier_kind_unknown():
    validator = _validator()
    result = validator.evaluate(
        "parent(ann, scott).",
        kind="unknown",
        needs_speaker_resolution=False,
    )
    assert result["status"] == "valid"


def test_alias_resolves_to_canonical_predicate():
    validator = _validator()
    result = validator.evaluate(
        "guardian_of(ann, scott).",
        kind="hard_fact",
        needs_speaker_resolution=False,
    )
    assert result["status"] == "valid"
    assert result["candidate"]["canonical_predicate"] == "parent"


def test_arity_mismatch_needs_clarification():
    validator = _validator()
    result = validator.evaluate(
        "parent(ann).",
        kind="hard_fact",
        needs_speaker_resolution=False,
    )
    assert result["status"] == "needs_clarification"
    assert any("arity mismatch" in issue for issue in result["issues"])


def test_text_fact_pattern_parses_allergy_statement():
    validator = _validator()
    result = validator.evaluate(
        "Alice is allergic to peanuts.",
        kind="hard_fact",
        needs_speaker_resolution=False,
    )
    assert result["status"] == "valid"
    assert result["candidate"]["canonical_predicate"] == "allergic_to"
    assert result["candidate"]["normalized_fact"] == "allergic_to(alice, peanuts)."


def test_tentative_prefix_keeps_fact_shape_for_clarification():
    validator = _validator()
    result = validator.evaluate(
        "Maybe my mother was Ann.",
        kind="tentative_fact",
        needs_speaker_resolution=True,
    )
    assert result["status"] == "needs_clarification"
    assert result["candidate"]["canonical_predicate"] == "parent"
    assert "<speaker>" in result["candidate"]["arguments"]
