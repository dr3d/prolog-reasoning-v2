#!/usr/bin/env python3
"""
Level-3 demo: derive a spreadsheet-style table from symbolic rules.

This shows a practical "agent logic coprocessor" scenario: compute deterministic
rows from facts + rules and emit table-shaped output.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_skill import PrologSkill
from engine.core import Term


def atom(name: str) -> Term:
    return Term(name)


def var(name: str) -> Term:
    return Term(name, is_variable=True)


def unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted(set(values))


def resolve_values(skill: PrologSkill, predicate: str, subject: str, variable_name: str) -> list[str]:
    """
    Resolve all values for predicate(subject, Variable).

    Example:
      resolve_values(skill, "allowed", "alice", "Action")
      -> ["read", "write"]
    """
    query = Term(predicate, [atom(subject), var(variable_name)])
    solutions = skill.engine.resolve(query)
    values: list[str] = []

    for solution in solutions:
        bound = solution.apply(var(variable_name))
        if bound and not bound.is_variable:
            values.append(bound.name)

    return unique_sorted(values)


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def format_csv(rows: list[dict[str, str]]) -> str:
    headers = ["user", "roles", "derived_permissions", "can_read", "can_write", "violation_flag"]
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(row[h] for h in headers))
    return "\n".join(lines)


def format_markdown(rows: list[dict[str, str]]) -> str:
    headers = ["user", "roles", "derived_permissions", "can_read", "can_write", "violation_flag"]
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    out = ["| " + " | ".join(headers) + " |", sep]
    for row in rows:
        out.append("| " + " | ".join(row[h] for h in headers) + " |")
    return "\n".join(out)


def main() -> None:
    print("RULE-DERIVED TABLE DEMO")
    print("=" * 60)
    print("Agent decision: this is a deterministic policy/table problem.")
    print("Use symbolic inference to build rows instead of guessing spreadsheet values.")

    skill = PrologSkill()
    users = ["alice", "bob", "john"]

    rows: list[dict[str, str]] = []
    for user in users:
        roles = resolve_values(skill, "role", user, "Role")
        permissions = resolve_values(skill, "allowed", user, "Action")

        can_read = "read" in permissions
        can_write = "write" in permissions

        if not can_read:
            violation_flag = "missing_read_access"
        elif not can_write:
            violation_flag = "missing_write_access"
        else:
            violation_flag = "none"

        rows.append(
            {
                "user": user,
                "roles": ";".join(roles) if roles else "none",
                "derived_permissions": ";".join(permissions) if permissions else "none",
                "can_read": bool_text(can_read),
                "can_write": bool_text(can_write),
                "violation_flag": violation_flag,
            }
        )

    print("\nMARKDOWN TABLE")
    print("-" * 60)
    print(format_markdown(rows))

    print("\nCSV")
    print("-" * 60)
    print(format_csv(rows))

    print("\nWhy this is useful:")
    print("- rows are derived from rules, not improvised")
    print("- changes in facts/rules automatically change table outputs")
    print("- each row can be explained by the same deterministic engine")


if __name__ == "__main__":
    main()
