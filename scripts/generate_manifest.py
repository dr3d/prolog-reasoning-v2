#!/usr/bin/env python3
"""
Generate KB Manifest for Agent Integration.

Creates a compact summary of the knowledge base that can be injected into
LLM agent prompts without wasting context window space.

Usage:
    python scripts/generate_manifest.py --kb prolog/core.pl --output kb_manifest.json
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engine.core import PrologEngine, Term, Clause


class ManifestGenerator:
    """Generate knowledge base manifest."""
    
    def __init__(self):
        self.engine = PrologEngine()
    
    def load_kb(self, kb_path: str):
        """Load knowledge base from .pl file."""
        path = Path(kb_path)
        if not path.exists():
            raise FileNotFoundError(f"KB not found: {kb_path}")
        
        with open(path, 'r') as f:
            content = f.read()
        
        # Parse clauses (simplified)
        clauses = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('%') and line.endswith('.'):
                # Very basic parsing - would need full parser for production
                clauses.append(line[:-1])  # Remove .
        
        return clauses
    
    def analyze_kb(self, kb_path: str) -> Dict[str, Any]:
        """Analyze KB and extract manifest information."""
        
        clauses = self.load_kb(kb_path)
        
        # Extract predicates and entities
        predicates: Set[str] = set()
        entities: Set[str] = set()
        fact_count = 0
        rule_count = 0
        
        for clause in clauses:
            if ':-' in clause:
                rule_count += 1
                head = clause.split(':-')[0].strip()
            else:
                fact_count += 1
                head = clause
            
            # Extract predicate name and arity
            if '(' in head and head.endswith(')'):
                pred_name = head.split('(')[0]
                args_str = head.split('(')[1][:-1]
                arity = len(args_str.split(',')) if args_str else 0
                predicates.add(f"{pred_name}/{arity}")
                
                # Extract entities (atoms that look like names)
                for arg in args_str.split(','):
                    arg = arg.strip()
                    if arg and not arg[0].isupper() and arg != '_':
                        # Heuristic: lowercase atoms are likely entities
                        entities.add(arg)
        
        return {
            "facts": fact_count,
            "rules": rule_count,
            "predicates": sorted(list(predicates)),
            "entities": sorted(list(entities)),
            "kb_path": kb_path
        }
    
    def generate_manifest(self, kb_path: str) -> Dict[str, Any]:
        """Generate full manifest for agent integration."""
        
        analysis = self.analyze_kb(kb_path)
        
        manifest = {
            "knowledge_base": {
                "facts": analysis["facts"],
                "rules": analysis["rules"],
                "predicates": analysis["predicates"],
                "entities": analysis["entities"],
                "path": analysis["kb_path"]
            },
            "skill": {
                "name": "prolog-reasoning",
                "description": "Deterministic knowledge base with backward-chaining inference",
                "capabilities": [
                    "factual queries",
                    "relationship inference",
                    "constraint checking",
                    "proof generation"
                ]
            },
            "query_interface": {
                "command": f"python src/engine/runner.py \"<query>\" --kb {kb_path}",
                "format": "Prolog syntax (e.g., 'parent(john, X).')",
                "response_format": "JSON with bindings and proof trace"
            },
            "behavioral_rules": [
                "Query KB before answering factual questions about known entities",
                "Use KB as source of truth, not training data",
                "Query for relationships and derived facts",
                "Include proof traces when explaining answers"
            ],
            "examples": [
                {
                    "query": "parent(john, X).",
                    "description": "Find John's children"
                },
                {
                    "query": "ancestor(scott, alice).",
                    "description": "Check if Scott is Alice's ancestor (derived)"
                },
                {
                    "query": "allowed(alice, read).",
                    "description": "Check if Alice has read permission"
                }
            ]
        }
        
        return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate KB manifest for agent integration"
    )
    parser.add_argument(
        "--kb",
        required=True,
        help="Path to knowledge base .pl file"
    )
    parser.add_argument(
        "--output",
        default="kb_manifest.json",
        help="Output manifest file"
    )
    
    args = parser.parse_args()
    
    generator = ManifestGenerator()
    manifest = generator.generate_manifest(args.kb)
    
    # Save manifest
    with open(args.output, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Manifest generated: {args.output}")
    print(f"KB Analysis: {manifest['knowledge_base']['facts']} facts, "
          f"{manifest['knowledge_base']['rules']} rules")
    print(f"Entities: {len(manifest['knowledge_base']['entities'])}")
    print(f"Predicates: {len(manifest['knowledge_base']['predicates'])}")


if __name__ == "__main__":
    main()
