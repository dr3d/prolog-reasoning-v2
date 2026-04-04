#!/usr/bin/env python3
"""
Demonstrate Agent Integration

Shows how an LLM agent would use the Prolog reasoning skill.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_skill import PrologSkill


def simulate_agent_conversation():
    """Simulate how an agent would use the skill."""
    
    print("*** Agent Integration Demo")
    print("=" * 50)
    
    # Initialize skill
    skill = PrologSkill()
    
    # Load manifest (would be injected into agent prompt)
    manifest = skill.get_manifest()
    print("*** Manifest injected into agent context:")
    print(json.dumps(manifest, indent=2))
    print()
    
    # Simulate conversation
    conversations = [
        {
            "user": "Who are John's children?",
            "agent_thinking": "John is a known entity. Query KB for parent relationships.",
            "query": "parent(john, X).",
            "expected": "Find all children of John"
        },
        {
            "user": "Is John Alice's ancestor?",
            "agent_thinking": "John and Alice are known entities. Check ancestor relationship.",
            "query": "ancestor(john, alice).",
            "expected": "Check if John is Alice's ancestor"
        },
        {
            "user": "Does Alice have read permissions?",
            "agent_thinking": "Alice is known entity. Check role and permissions.",
            "query": "allowed(alice, read).",
            "expected": "Check read access"
        }
    ]
    
    for i, conv in enumerate(conversations, 1):
        print(f"*** Conversation {i}")
        print(f"User: {conv['user']}")
        print(f"Agent thinking: {conv['agent_thinking']}")
        print(f"Query: {conv['query']}")
        
        # Execute query
        result = skill.query(conv['query'])
        
        print(f"KB Response: {result['success']}")
        if result['success']:
            print(f"Explanation: {result['explanation']}")
        else:
            print(f"Error: {result.get('error', 'Query failed')}")
        
        print("-" * 30)
    
    print("\n>>> Key Benefits:")
    print("* KB stays external (no context window waste)")
    print("* Facts are lossless (never degrade)")
    print("* Inference works (derived relationships)")
    print("* Proof traces provide explainability")
    print("* Agent can focus on reasoning, not memorization")


def demonstrate_skill_api():
    """Show the skill API for framework integration."""
    
    print("\n*** Skill API Demo")
    print("=" * 30)
    
    skill = PrologSkill()
    
    # Direct query
    result = skill.query("parent(john, alice).")
    print("Direct query result:")
    print(json.dumps(result, indent=2))
    
    # Manifest for context injection
    manifest = skill.get_manifest()
    print("\nManifest for agent prompt:")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    simulate_agent_conversation()
    demonstrate_skill_api()
