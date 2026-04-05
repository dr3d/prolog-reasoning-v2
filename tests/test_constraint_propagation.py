"""Tests for known-state and degree-of-freedom propagation."""

import sys

sys.path.insert(0, "src")

from engine.constraint_propagation import ConstraintPropagator, PropagationProblem
from ir.schema import (
    ConstraintRuleSpec,
    DomainConstraintSpec,
    StateAtom,
    StateDomainLinkSpec,
)


def test_known_state_transitive_propagation():
    problem = PropagationProblem(
        initial_states={StateAtom("enabled", ("sensor_a",))},
        rules=[
            ConstraintRuleSpec(
                name="enabled_implies_ready",
                antecedents=[StateAtom("enabled", ("?X",))],
                consequent=StateAtom("ready", ("?X",)),
            ),
            ConstraintRuleSpec(
                name="ready_implies_active",
                antecedents=[StateAtom("ready", ("?X",))],
                consequent=StateAtom("active", ("?X",)),
            ),
        ],
    )

    result = ConstraintPropagator().propagate(problem)

    assert StateAtom("enabled", ("sensor_a",)) in result.known_states
    assert StateAtom("ready", ("sensor_a",)) in result.known_states
    assert StateAtom("active", ("sensor_a",)) in result.known_states
    assert not result.contradictions


def test_degrees_of_freedom_domain_pruning_not_equal():
    problem = PropagationProblem(
        initial_domains={
            "X": {1},
            "Y": {1, 2, 3},
        },
        domain_constraints=[
            DomainConstraintSpec(kind="not_equal", left="X", right="Y"),
        ],
    )

    result = ConstraintPropagator().propagate(problem)

    assert result.domains["Y"] == {2, 3}
    assert result.degrees_of_freedom["X"] == 1
    assert result.degrees_of_freedom["Y"] == 2
    assert result.total_degrees_of_freedom == 1


def test_state_triggered_domain_restriction():
    problem = PropagationProblem(
        initial_states={StateAtom("mode", ("safe",))},
        initial_domains={"speed": {10, 20, 30}},
        state_domain_links=[
            StateDomainLinkSpec(
                trigger=StateAtom("mode", ("safe",)),
                variable="speed",
                allowed_values={10},
            )
        ],
    )

    result = ConstraintPropagator().propagate(problem)

    assert result.domains["speed"] == {10}
    assert result.degrees_of_freedom["speed"] == 1
    assert result.total_degrees_of_freedom == 0


def test_domain_contradiction_is_reported():
    problem = PropagationProblem(
        initial_domains={"X": {1}},
        domain_constraints=[
            DomainConstraintSpec(kind="forbidden_values", left="X", values={1}),
        ],
    )

    result = ConstraintPropagator().propagate(problem)

    assert result.domains["X"] == set()
    assert any("Domain contradiction" in c for c in result.contradictions)
