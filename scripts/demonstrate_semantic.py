#!/usr/bin/env python3
"""
Demonstrate Semantic Grounding Layer.

Shows how natural language queries are converted to Prolog and executed.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.semantic import SemanticGrounder, SemanticPrologSkill


def demo_semantic_grounding():
    """Demonstrate semantic grounding with various query types."""

    print("SEMANTIC GROUNDING DEMO")
    print("=" * 50)

    grounder = SemanticGrounder()

    test_queries = [
        "Who is John's parent?",
        "Is Alice allowed to read?",
        "John is Alice's parent",
        "Who are the ancestors of Bob?",
        "Are Alice and Bob siblings?",
        "What permissions does Alice have?"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        print("-" * 30)

        try:
            # Ground the query
            parsed = grounder.ground_query(query)

            print(f"Intent: {parsed.intent.value}")
            print(f"Domain: {parsed.domain}")
            print(f"Confidence: {parsed.confidence:.2f}")

            # Show IR
            ir_dict = json.loads(parsed.ir.to_json())
            print(f"IR: {json.dumps(ir_dict, indent=2)}")

            # Show Prolog
            prolog = grounder.to_prolog_query(parsed)
            print(f"Prolog: {prolog}")

        except Exception as e:
            print(f"ERROR: {e}")


def demo_integrated_skill():
    """Demonstrate end-to-end NL to Prolog execution."""

    print("\nINTEGRATED SKILL DEMO")
    print("=" * 50)

    skill = SemanticPrologSkill()

    nl_queries = [
        "Who is John's parent?",
        "Is Alice allowed to read?",
        "Who are Alice's siblings?"
    ]

    for query in nl_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 30)

        try:
            result = skill.query_nl(query)

            print(f"Success: {result['success']}")
            print(f"Parsing Confidence: {result['parsing_confidence']:.2f}")
            print(f"Domain: {result['domain']}")

            if result['success']:
                print(f"Answer: {result['explanation']}")
                if result['bindings']:
                    print(f"Bindings: {result['bindings']}")
            else:
                print(f"Error: {result.get('error', 'No answer found')}")

        except Exception as e:
            print(f"ERROR: {e}")


def demo_error_correction():
    """Show error correction capabilities."""

    print("\nERROR CORRECTION DEMO")
    print("=" * 50)

    grounder = SemanticGrounder()

    # Test with ambiguous query
    ambiguous_query = "What is the relationship between John and Alice?"

    print(f"Query: '{ambiguous_query}'")
    print("-" * 30)

    parsed = grounder.ground_query(ambiguous_query)

    print(f"Parsed as: {parsed.intent.value}")
    print(f"Predicate: {parsed.ir.predicate}")
    print(f"Confidence: {parsed.confidence:.2f}")
    print(f"Prolog: {grounder.to_prolog_query(parsed)}")


if __name__ == "__main__":
    demo_semantic_grounding()
    demo_integrated_skill()
    demo_error_correction()

    print("\n*** Semantic Grounding Demo Complete!")
    print("\nNext steps:")
    print("- Integrate with real LLM API (OpenAI, Anthropic)")
    print("- Add more domain schemas")
    print("- Implement rule learning from examples")
    print("- Add multi-turn conversation context")