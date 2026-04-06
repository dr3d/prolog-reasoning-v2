#!/usr/bin/env python3
"""
Level-5 demo: deterministic drug-interaction triage from symbolic rules.

This is an overt logic-tool scenario where a small clinical fact set produces
non-obvious but explainable recommendations.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_skill import PrologSkill
from engine.core import Term


def atom(name: str) -> Term:
    return Term(name)


def var(name: str) -> Term:
    return Term(name, is_variable=True)


def resolve_bindings(skill: PrologSkill, query: Term, variables: list[str]) -> list[dict[str, str]]:
    """Resolve query and return selected variable bindings."""
    rows: list[dict[str, str]] = []
    for solution in skill.engine.resolve(query):
        row: dict[str, str] = {}
        for variable in variables:
            bound = solution.apply(var(variable))
            row[variable] = bound.name if bound and not bound.is_variable else str(bound)
        rows.append(row)
    return rows


def get_candidate_drugs(skill: PrologSkill, patient: str) -> list[str]:
    rows = resolve_bindings(
        skill,
        Term("candidate_drug", [atom(patient), var("Drug")]),
        ["Drug"],
    )
    return sorted({row["Drug"] for row in rows})


def triage_drug(skill: PrologSkill, patient: str, drug: str) -> tuple[str, str]:
    """Return overall status and short reason string for one candidate drug."""
    rows = resolve_bindings(
        skill,
        Term("triage", [atom(patient), atom(drug), var("Status"), var("Reason")]),
        ["Status", "Reason"],
    )
    if not rows:
        return "safe", "no derived risk flag"

    contraindicated_reasons = sorted({row["Reason"] for row in rows if row["Status"] == "contraindicated"})
    caution_reasons = sorted({row["Reason"] for row in rows if row["Status"] == "caution"})

    if contraindicated_reasons:
        return "contraindicated", ";".join(contraindicated_reasons)
    if caution_reasons:
        return "caution", ";".join(caution_reasons)
    return rows[0]["Status"], rows[0]["Reason"]


def markdown_table(rows: list[dict[str, str]]) -> str:
    headers = ["patient", "candidate_drug", "status", "reason"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[h] for h in headers) + " |")
    return "\n".join(lines)


def main() -> None:
    print("CLINICAL TRIAGE LOGIC DEMO")
    print("=" * 60)
    print("Agent decision: this is a hard-constraint safety task.")
    print("Use deterministic inference for risk triage, then summarize.")

    skill = PrologSkill()
    patient = "alice"
    drugs = get_candidate_drugs(skill, patient)

    rows: list[dict[str, str]] = []
    for drug in drugs:
        status, reason = triage_drug(skill, patient, drug)
        rows.append(
            {
                "patient": patient,
                "candidate_drug": drug,
                "status": status,
                "reason": reason,
            }
        )

    print("\nTRIAGE TABLE")
    print("-" * 60)
    print(markdown_table(rows))

    safe_rows = [row for row in rows if row["status"] == "safe"]
    contraindicated_rows = [row for row in rows if row["status"] == "contraindicated"]
    caution_rows = [row for row in rows if row["status"] == "caution"]

    print("\nCONNECT-THE-DOTS INSIGHT")
    print("-" * 60)
    if safe_rows:
        safe_names = ", ".join(sorted(row["candidate_drug"] for row in safe_rows))
        print(f"Safe candidates for {patient}: {safe_names}")
    else:
        print(f"No fully safe candidates for {patient} in this candidate set.")

    if contraindicated_rows:
        for row in contraindicated_rows:
            print(f"- contraindicated: {row['candidate_drug']} ({row['reason']})")
    if caution_rows:
        for row in caution_rows:
            print(f"- caution: {row['candidate_drug']} ({row['reason']})")

    print("\nWhy this is useful:")
    print("- one medication can be blocked for different reasons per patient")
    print("- derived risk status is reproducible and auditable")
    print("- an LLM can present this, but should not improvise the logic")


if __name__ == "__main__":
    main()
