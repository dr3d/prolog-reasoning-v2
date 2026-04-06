#!/usr/bin/env python3
"""
Demonstrate overt logic-tool use with a tiny family tree.

This script is meant to feel like what an agent would do on purpose:
load a deterministic reasoning tool, set up a small world, and query it for
exact consequences that are easy for plain LLMs to muddle over time.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engine.core import Clause, PrologEngine, Term


def atom(name: str) -> Term:
    return Term(name)


def var(name: str) -> Term:
    return Term(name, is_variable=True)


def add_family_tree(engine: PrologEngine) -> None:
    """Load a tiny family tree into the engine."""
    facts = [
        Clause(Term("parent", [atom("ann"), atom("bob")])),
        Clause(Term("parent", [atom("bob"), atom("clara")])),
        Clause(Term("parent", [atom("ann"), atom("dana")])),
        Clause(Term("parent", [atom("dana"), atom("evan")])),
    ]

    rules = [
        Clause(
            Term("ancestor", [var("X"), var("Y")]),
            [Term("parent", [var("X"), var("Y")])],
        ),
        Clause(
            Term("ancestor", [var("X"), var("Y")]),
            [
                Term("parent", [var("X"), var("Z")]),
                Term("ancestor", [var("Z"), var("Y")]),
            ],
        ),
        Clause(
            Term("sibling", [var("X"), var("Y")]),
            [
                Term("parent", [var("P"), var("X")]),
                Term("parent", [var("P"), var("Y")]),
                Term("\\=", [var("X"), var("Y")]),
            ],
        ),
    ]

    for clause in facts + rules:
        engine.add_clause(clause)


def query_variables(term: Term) -> list[str]:
    """Collect variable names from a query term."""
    names: list[str] = []

    def walk(node: Term) -> None:
        if node.is_variable and node.name not in names:
            names.append(node.name)
        for arg in node.args:
            walk(arg)

    walk(term)
    return names


def pretty_solution(query: Term, solution) -> str:
    """Render only the variables that appear in the original query."""
    names = query_variables(query)
    if not names:
        return "TRUE"

    bindings = []
    for name in names:
        value = solution.apply(var(name))
        bindings.append(f"{name} = {value}")
    return ", ".join(bindings)


def run_query(engine: PrologEngine, query: Term, label: str) -> None:
    """Resolve one query and print an agent-friendly explanation."""
    print(f"\n{label}")
    print(f"Query: {query}")
    solutions = engine.resolve(query)

    if not solutions:
        print("Result: no solutions")
        return

    print(f"Result: {len(solutions)} solution(s)")
    for index, solution in enumerate(solutions, start=1):
        print(f"  {index}. {pretty_solution(query, solution)}")


def main() -> None:
    print("FAMILY TREE LOGIC TOOL DEMO")
    print("=" * 60)
    print("Agent decision: this is a relationship problem, so use the")
    print("deterministic logic layer instead of freehand language-model reasoning.")

    engine = PrologEngine(max_depth=100)
    add_family_tree(engine)

    print("\nLoaded facts:")
    print("  parent(ann, bob).")
    print("  parent(bob, clara).")
    print("  parent(ann, dana).")
    print("  parent(dana, evan).")

    print("\nLoaded rules:")
    print("  ancestor(X, Y) :- parent(X, Y).")
    print("  ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).")
    print("  sibling(X, Y) :- parent(P, X), parent(P, Y), X \\= Y.")

    run_query(
        engine,
        Term("ancestor", [atom("ann"), atom("clara")]),
        "1. Ask whether Ann is Clara's ancestor",
    )
    run_query(
        engine,
        Term("ancestor", [atom("ann"), var("X")]),
        "2. Ask for all of Ann's descendants",
    )
    run_query(
        engine,
        Term("sibling", [atom("bob"), atom("dana")]),
        "3. Ask whether Bob and Dana are siblings",
    )
    run_query(
        engine,
        Term("sibling", [atom("clara"), atom("dana")]),
        "4. Ask whether Clara and Dana are siblings",
    )

    print("\nWhy this is useful:")
    print("- ancestry is computed exactly, not guessed")
    print("- sibling logic is reproducible across repeated queries")
    print("- the same facts and rules always produce the same result")


if __name__ == "__main__":
    main()
