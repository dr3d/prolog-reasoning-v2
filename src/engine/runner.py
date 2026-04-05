#!/usr/bin/env python3
"""
Prolog Engine Runner - Standalone interface for executing Prolog queries.

Usage:
    python runner.py "parent(john, X)." --kb prolog/family.pl
    python runner.py "allowed(alice, write)." 
    python runner.py --manifest --kb prolog/core.pl
"""

import sys
import json
import argparse
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.constraint_propagation import ConstraintPropagator, PropagationProblem
from ir.schema import (
    ConstraintRuleSpec,
    DomainConstraintSpec,
    StateAtom,
    StateDomainLinkSpec,
)

# Placeholder for actual engine implementation
# TODO: Import actual engine when implemented
# from engine import PrologEngine


def load_kb(kb_path):
    """Load knowledge base from .pl file."""
    if not kb_path:
        return {}
    
    path = Path(kb_path)
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base not found: {kb_path}")
    
    # TODO: Parse .pl file into facts and rules
    with open(path, 'r') as f:
        content = f.read()
    
    return {"raw": content}


def execute_query(query, kb=None):
    """
    Execute a Prolog query against the knowledge base.
    
    Returns:
        dict with keys:
            - success (bool)
            - bindings (list of dicts)
            - trace (optional execution trace)
            - proof (optional proof chain)
    """
    # TODO: Implement actual query execution
    return {
        "success": True,
        "bindings": [{}],
        "trace": [],
        "proof": []
    }


def generate_manifest(kb_path):
    """Generate a manifest of the knowledge base."""
    kb = load_kb(kb_path)
    
    # TODO: Parse KB and extract facts/rules
    manifest = {
        "facts_count": 0,
        "rules_count": 0,
        "predicates": [],
        "entities": []
    }
    
    return manifest


def _parse_state_atom(raw):
    """Parse state atom from dict or list form."""
    if isinstance(raw, dict):
        predicate = raw.get("predicate")
        args = tuple(raw.get("args", []))
        return StateAtom(predicate=predicate, args=args)

    if isinstance(raw, list) and raw:
        predicate = raw[0]
        args = tuple(raw[1:])
        return StateAtom(predicate=predicate, args=args)

    raise ValueError(f"Invalid state atom format: {raw}")


def _parse_rule(raw):
    """Parse deterministic rule spec from JSON dict."""
    return ConstraintRuleSpec(
        name=raw.get("name", "rule"),
        antecedents=[_parse_state_atom(a) for a in raw.get("antecedents", [])],
        consequent=_parse_state_atom(raw["consequent"]),
    )


def _parse_domain_constraint(raw):
    """Parse domain constraint spec from JSON dict."""
    values = raw.get("values")
    return DomainConstraintSpec(
        kind=raw["kind"],
        left=raw["left"],
        right=raw.get("right"),
        values=set(values) if values is not None else None,
        when_value=raw.get("when_value"),
    )


def _parse_state_domain_link(raw):
    """Parse state-triggered domain narrowing link from JSON dict."""
    return StateDomainLinkSpec(
        trigger=_parse_state_atom(raw["trigger"]),
        variable=raw["variable"],
        allowed_values=set(raw.get("allowed_values", [])),
    )


def build_propagation_problem(spec):
    """Build PropagationProblem from a JSON-compatible dict."""
    return PropagationProblem(
        initial_states={_parse_state_atom(s) for s in spec.get("initial_states", [])},
        rules=[_parse_rule(r) for r in spec.get("rules", [])],
        initial_domains={
            var: set(values) for var, values in spec.get("initial_domains", {}).items()
        },
        domain_constraints=[
            _parse_domain_constraint(c) for c in spec.get("domain_constraints", [])
        ],
        state_domain_links=[
            _parse_state_domain_link(link) for link in spec.get("state_domain_links", [])
        ],
    )


def execute_propagation(spec, max_iterations=100):
    """Execute propagation from a dict spec and return JSON-serializable result."""
    problem = build_propagation_problem(spec)
    result = ConstraintPropagator(max_iterations=max_iterations).propagate(problem)

    known_states = [
        {"predicate": atom.predicate, "args": list(atom.args)}
        for atom in sorted(result.known_states, key=lambda a: (a.predicate, a.args))
    ]
    domains = {var: sorted(list(values)) for var, values in sorted(result.domains.items())}

    return {
        "known_states": known_states,
        "domains": domains,
        "degrees_of_freedom": result.degrees_of_freedom,
        "total_degrees_of_freedom": result.total_degrees_of_freedom,
        "contradictions": result.contradictions,
        "iterations": result.iterations,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Prolog reasoning engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py "parent(john, X)." --kb prolog/family.pl
  python runner.py "allowed(alice, write)."
  python runner.py --manifest --kb prolog/core.pl
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Prolog query to execute (e.g., 'parent(john, X).')"
    )
    parser.add_argument(
        "--kb",
        help="Path to knowledge base .pl file (default: all loaded)"
    )
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Generate manifest of KB instead of executing query"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate KB syntax"
    )
    parser.add_argument(
        "--assert",
        dest="assert_fact",
        help="Assert a new fact into KB"
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Run state/domain constraint propagation from JSON spec"
    )
    parser.add_argument(
        "--problem-json",
        help="Path to propagation problem JSON file"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Max propagation iterations (default: 100)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.manifest:
            manifest = generate_manifest(args.kb)
            print(json.dumps(manifest, indent=2))
            return 0
        
        if args.validate:
            kb = load_kb(args.kb)
            # TODO: Validate syntax
            print(json.dumps({"valid": True, "errors": []}))
            return 0
        
        if args.assert_fact:
            # TODO: Assert fact into KB
            result = {"success": True}
            print(json.dumps(result))
            return 0

        if args.propagate:
            if not args.problem_json:
                print(json.dumps({"error": "--problem-json is required with --propagate"}), file=sys.stderr)
                return 1

            problem_path = Path(args.problem_json)
            if not problem_path.exists():
                print(json.dumps({"error": f"Propagation problem not found: {args.problem_json}"}), file=sys.stderr)
                return 1

            with open(problem_path, "r", encoding="utf-8") as f:
                spec = json.load(f)

            result = execute_propagation(spec, max_iterations=args.max_iterations)
            print(json.dumps(result, indent=2))
            return 0
        
        if not args.query:
            parser.print_help()
            return 1
        
        kb = load_kb(args.kb)
        result = execute_query(args.query, kb)
        print(json.dumps(result, indent=2))
        return 0
        
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
