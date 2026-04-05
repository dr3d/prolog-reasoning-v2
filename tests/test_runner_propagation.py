"""Tests for propagation execution through runner utilities."""

import sys

sys.path.insert(0, "src")

from engine.runner import execute_propagation


def test_execute_propagation_returns_known_states_and_domains():
    spec = {
        "initial_states": [
            {"predicate": "enabled", "args": ["sensor_a"]}
        ],
        "rules": [
            {
                "name": "enabled_implies_ready",
                "antecedents": [
                    {"predicate": "enabled", "args": ["?X"]}
                ],
                "consequent": {"predicate": "ready", "args": ["?X"]}
            }
        ],
        "initial_domains": {
            "speed": [10, 20, 30]
        },
        "state_domain_links": [
            {
                "trigger": {"predicate": "ready", "args": ["sensor_a"]},
                "variable": "speed",
                "allowed_values": [10]
            }
        ]
    }

    result = execute_propagation(spec)

    states = {(s["predicate"], tuple(s["args"])) for s in result["known_states"]}
    assert ("enabled", ("sensor_a",)) in states
    assert ("ready", ("sensor_a",)) in states

    assert result["domains"]["speed"] == [10]
    assert result["degrees_of_freedom"]["speed"] == 1
    assert result["total_degrees_of_freedom"] == 0
