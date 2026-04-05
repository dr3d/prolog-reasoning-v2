#!/usr/bin/env python3
"""
Demonstrate Failure Explanations for Beginners.

Shows how the system helps newcomers understand what went wrong
and how to fix it. This is perfect for learning!

Run: python scripts/demonstrate_failures.py
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.semantic import SemanticPrologSkill


def print_section(title):
    """Print a nice section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def demonstrate_valid_query():
    """Show a query that works perfectly."""
    print_section("✅ SUCCESS: When Everything Works")
    
    skill = SemanticPrologSkill()
    
    query = "Who is John's parent?"
    print(f"\nYou ask: \"{query}\"")
    
    result = skill.query_nl(query)
    
    if result["success"]:
        print("\n✨ The system found an answer!")
        print(f"Answer: {result['explanation']}")
        print(f"Confidence: {result['validation_confidence']:.0%} sure this is right")
    else:
        print("No answer found")


def demonstrate_undefined_entity():
    """Show what happens when you mention someone unknown."""
    print_section("❌ FAILURE: Unknown Person (Most Common Beginner Mistake!)")
    
    skill = SemanticPrologSkill()
    
    query = "Who is Charlie's parent?"
    print(f"\nYou ask: \"{query}\"")
    print("\n🤔 System thinks...")
    print("  → 'Charlie' - I've never heard of this person!")
    
    result = skill.query_nl(query)
    
    if not result["success"]:
        print("\n❌ The system found a problem:")
        
        for error in result.get("validation_errors", []):
            # Print the human-friendly explanation
            if "explanation" in error:
                print(error["explanation"])
            else:
                print(f"  Error: {error['message']}")
                print(f"  Suggestion: {error['suggestion']}")
    
    print("\n💡 How to fix it:")
    print("  1. Tell the system about Charlie first")
    print("  2. Or use a name it knows: John, Alice, or Bob")


def demonstrate_ungrounded_predicate():
    """Show what happens with unfamiliar predicates."""
    print_section("⚠️ WARNING: Unfamiliar Relationship Type")
    
    skill = SemanticPrologSkill()
    
    query = "Can Alice fly?"
    print(f"\nYou ask: \"{query}\"")
    print("\n🤔 System thinks...")
    print("  → 'Can fly' - I don't know this relationship!")
    
    result = skill.query_nl(query)
    
    print("\n⚠️ The system is unsure:")
    print(f"  Parsing confidence: {result.get('parsing_confidence', 0.0):.0%}")
    print(f"  Validation confidence: {result.get('validation_confidence', 0.0):.0%}")
    
    if result.get("validation_errors"):
        for error in result["validation_errors"]:
            if "explanation" in error:
                print(error["explanation"])


def demonstrate_query_failure():
    """Show what happens when a query returns no answers."""
    print_section("🔍 NO MATCH: Query Found Nothing")
    
    skill = SemanticPrologSkill()
    
    query = "Who is Alice's grandparent?"
    print(f"\nYou ask: \"{query}\"")
    print("\n🤔 System thinks...")
    print("  → Searching for 'Alice's grandparent'...")
    print("  → Looking through facts...")
    print("  → No matches found!")
    
    result = skill.query_nl(query)
    
    if not result["success"] and "failure_explanation" not in result:
        print("\n🤷 The system couldn't find an answer")
        if "what_to_try" in result:
            print(f"  Try: {result['what_to_try']}")
    elif "failure_explanation" in result:
        print("\n📝 Why no answer?")
        print(result["failure_explanation"])


def demonstrate_success_with_derived_facts():
    """Show the power of logical reasoning."""
    print_section("🧠 POWER: Derived Knowledge (The Cool Part!)")
    
    skill = SemanticPrologSkill()
    
    query = "Is John an ancestor of Bob?"
    print(f"\nYou ask: \"{query}\"")
    print("\n🤔 System thinks...")
    print("  → Is John the parent of Bob? No...")
    print("  → Is John the parent of someone who is an ancestor of Bob? Yes!")
    print("  → John → Alice → Bob (chain found!)")
    
    result = skill.query_nl(query)
    
    if result["success"]:
        print("\n✨ The system figured it out:")
        print(f"  Answer: {result['explanation']}")
        print("\n💡 Key point:")
        print("  You never told it John was Bob's grandpa.")
        print("  It figured it out from the facts you provided!")


def demonstrate_step_by_step():
    """Show a complete beginner workflow."""
    print_section("📚 TUTORIAL: Your First Real Query")
    
    skill = SemanticPrologSkill()
    
    print("\nStep 1: You tell the system some facts")
    print('  You: "My mom is Alice"')
    print('  You: "Alice\'s mom is Eve"')
    print("\nStep 2: You ask a question")
    
    query = "Is Alice John's parent?"
    print(f'  You: "{query}"')
    
    result = skill.query_nl(query)
    
    print("\nStep 3: The system reasons through it")
    print("  System: Looking for relationship...")
    print("  System: Checking facts...")
    print(f"  System: {result['explanation']}")
    
    print("\nStep 4: You learn from feedback")
    if result["success"]:
        print("  Confidence: It's this sure because of the facts")
    if "validation_errors" in result:
        print("  Errors: The system caught these issues")


def show_comparison():
    """Show the difference between with and without explanations."""
    print_section("🎯 WHY EXPLANATIONS MATTER FOR LEARNING")
    
    print("\n❌ WITHOUT explanations:")
    print('  You: "Who is Charlie\'s parent?"')
    print('  System: "Error: undefined_entity"')
    print("  You: 😕 What does that mean? What do I do?")
    
    print("\n✅ WITH explanations:")
    print('  You: "Who is Charlie\'s parent?"')
    print('  System: ❌ I don\'t know who Charlie is')
    print('          System only knows: john, alice, bob')
    print('          💡 Try: Tell me about Charlie first')
    print("  You: 😊 Ah! I need to define new people first")
    
    print("\n💡 Explanations let you learn, not just get errors!")


def main():
    """Run all demonstrations."""
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Failure Explanations: Learning from Mistakes  ".center(68) + "║")
    print("║" + "  Perfect for beginners learning how NeSy works  ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        # Show success case first
        demonstrate_valid_query()
        
        # Show common beginner mistakes
        demonstrate_undefined_entity()
        demonstrate_ungrounded_predicate()
        demonstrate_query_failure()
        
        # Show the power of reasoning
        demonstrate_success_with_derived_facts()
        
        # Tutorial
        demonstrate_step_by_step()
        
        # Why this matters
        show_comparison()
        
        print_section("🎉 You Now Understand Failure Explanations!")
        print("\nKey Takeaways:")
        print("  1. Errors are expected - they help you learn")
        print("  2. Explanations tell you WHY something failed")
        print("  3. Suggestions tell you HOW to fix it")
        print("  4. The system reasons through chains of facts")
        print("\n💡 Next: Try modifying the queries above and experiment!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()