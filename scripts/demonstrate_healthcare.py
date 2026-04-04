#!/usr/bin/env python3
"""
Healthcare Medication Safety Demo

Demonstrates how Prolog reasoning prevents medication errors that could harm patients.
This shows the real-world impact of deterministic reasoning in critical domains.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engine.core import PrologEngine, Term, Clause
from explain.explanation import ExplanationGenerator


def setup_healthcare_kb():
    """Set up a realistic healthcare knowledge base."""
    engine = PrologEngine()
    tracer = ExplanationGenerator()

    # Patient data
    engine.add_clause(Clause(Term("patient", [Term("john_smith"), Term("id_12345")])))
    engine.add_clause(Clause(Term("age", [Term("john_smith"), Term("65", is_number=True)])))
    engine.add_clause(Clause(Term("condition", [Term("john_smith"), Term("diabetes")])))
    engine.add_clause(Clause(Term("condition", [Term("john_smith"), Term("hypertension")])))

    # Current medications
    engine.add_clause(Clause(Term("takes_medication", [Term("john_smith"), Term("metformin"), Term("500", is_number=True), Term("bid")])))
    engine.add_clause(Clause(Term("takes_medication", [Term("john_smith"), Term("lisinopril"), Term("10", is_number=True), Term("daily")])))
    engine.add_clause(Clause(Term("takes_medication", [Term("john_smith"), Term("aspirin"), Term("81", is_number=True), Term("daily")])))

    # Allergies
    engine.add_clause(Clause(Term("allergy", [Term("john_smith"), Term("penicillin"), Term("severe")])))
    engine.add_clause(Clause(Term("allergy", [Term("john_smith"), Term("sulfa_drugs"), Term("moderate")])))

    # Lab results
    engine.add_clause(Clause(Term("lab_result", [Term("john_smith"), Term("creatinine"), Term("1.8", is_number=True), Term("2024-01-15")])))
    engine.add_clause(Clause(Term("lab_result", [Term("john_smith"), Term("egfr"), Term("45", is_number=True), Term("2024-01-15")])))

    # Drug interaction rules
    engine.add_clause(Clause(
        Term("interacts", [Term("Drug1", is_variable=True), Term("Drug2", is_variable=True)]),
        [Term("both_diabetes_drugs", [Term("Drug1", is_variable=True), Term("Drug2", is_variable=True)])]
    ))
    engine.add_clause(Clause(
        Term("interacts", [Term("Drug1", is_variable=True), Term("Drug2", is_variable=True)]),
        [Term("both_blood_pressure_drugs", [Term("Drug1", is_variable=True), Term("Drug2", is_variable=True)])]
    ))

    # Specific interactions
    engine.add_clause(Clause(Term("both_diabetes_drugs", [Term("metformin"), Term("glipizide")])))
    engine.add_clause(Clause(Term("both_diabetes_drugs", [Term("insulin"), Term("metformin")])))
    engine.add_clause(Clause(Term("both_blood_pressure_drugs", [Term("lisinopril"), Term("amlodipine")])))

    # Contraindication rules
    engine.add_clause(Clause(
        Term("contraindicated", [Term("Patient", is_variable=True), Term("Drug", is_variable=True)]),
        [Term("allergy", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("severe")])]
    ))
    engine.add_clause(Clause(
        Term("contraindicated", [Term("Patient", is_variable=True), Term("Drug", is_variable=True)]),
        [
            Term("allergy", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("moderate")]),
            Term("high_risk_drug", [Term("Drug", is_variable=True)])
        ]
    ))
    engine.add_clause(Clause(
        Term("contraindicated", [Term("Patient", is_variable=True), Term("Drug", is_variable=True)]),
        [
            Term("takes_medication", [Term("Patient", is_variable=True), Term("Drug2", is_variable=True), Term("_", is_variable=True), Term("_", is_variable=True)]),
            Term("interacts", [Term("Drug", is_variable=True), Term("Drug2", is_variable=True)])
        ]
    ))
    engine.add_clause(Clause(
        Term("contraindicated", [Term("Patient", is_variable=True), Term("Drug", is_variable=True)]),
        [
            Term("condition", [Term("Patient", is_variable=True), Term("kidney_disease")]),
            Term("nephrotoxic", [Term("Drug", is_variable=True)])
        ]
    ))

    # Drug classifications
    engine.add_clause(Clause(Term("high_risk_drug", [Term("penicillin")])))
    engine.add_clause(Clause(Term("nephrotoxic", [Term("gentamicin")])))
    engine.add_clause(Clause(Term("nephrotoxic", [Term("vancomycin")])))

    # Kidney disease rule (based on eGFR < 60)
    engine.add_clause(Clause(
        Term("condition", [Term("Patient", is_variable=True), Term("kidney_disease")]),
        [
            Term("lab_result", [Term("Patient", is_variable=True), Term("egfr"), Term("Value", is_variable=True), Term("_", is_variable=True)]),
            Term("<", [Term("Value", is_variable=True), Term("60", is_number=True)])
        ]
    ))

    return engine, tracer


def demonstrate_medication_safety():
    """Demonstrate medication safety checking."""
    print("*** Healthcare Medication Safety Demo")
    print("=" * 50)
    print()

    engine, tracer = setup_healthcare_kb()

    # Test cases that could cause real harm
    test_cases = [
        {
            "name": "Penicillin Allergy Check",
            "query": "contraindicated(john_smith, penicillin)",
            "description": "Checking for severe penicillin allergy",
            "expected": True,
            "impact": "PREVENTS ANAPHYLACTIC SHOCK"
        },
        {
            "name": "Drug Interaction Check",
            "query": "contraindicated(john_smith, glipizide)",
            "description": "Checking for diabetes drug interaction with metformin",
            "expected": True,
            "impact": "PREVENTS HYPOGLYCEMIC EPISODE"
        },
        {
            "name": "Kidney Function Safety",
            "query": "contraindicated(john_smith, gentamicin)",
            "description": "Checking nephrotoxic drug against kidney function",
            "expected": True,
            "impact": "PREVENTS ACUTE KIDNEY INJURY"
        },
        {
            "name": "Safe Medication Check",
            "query": "contraindicated(john_smith, acetaminophen)",
            "description": "Checking if safe medication is contraindicated",
            "expected": False,
            "impact": "CONFIRMS MEDICATION IS SAFE"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print("-" * 40)
        print(f"Query: {test_case['query']}")
        print(f"Description: {test_case['description']}")
        print()

        # Execute query
        try:
            query_term = engine.parse_term(test_case['query'])
            tracer.start_goal(query_term, 0)
            solutions = engine.resolve(query_term)

            success = len(solutions) > 0
            expected = test_case['expected']

            if success == expected:
                status = "SUCCESS"
            else:
                status = "UNEXPECTED"

            print(f"Result: {status} - {'True' if success else 'False'}")
            print(f"Impact: {test_case['impact']}")

            if solutions:
                explanation = tracer.generate_explanation(solutions, query_term)
                print("Explanation:")
                print(f"  {explanation['explanation']}")

        except Exception as e:
            print(f"ERROR: {e}")

        print()

    print("*** Key Insights:")
    print("- Prolog reasoning provides deterministic safety checks")
    print("- Rules encode medical knowledge that doesn't decay")
    print("- Complex interactions are automatically detected")
    print("- No reliance on LLM memory that can forget or hallucinate")
    print()
    print("*** Real-World Impact:")
    print("- Prevents medication errors that cause 1.3 million injuries/year in US")
    print("- Enables safe polypharmacy for complex patients")
    print("- Supports clinical decision making with perfect recall")


if __name__ == "__main__":
    demonstrate_medication_safety()