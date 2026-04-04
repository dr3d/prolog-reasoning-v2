#!/usr/bin/env python3
"""
Agent Skill Interface for Prolog Reasoning.

Provides a clean API for LLM agents to query the knowledge base.
Designed to be called from agent frameworks like AutoGen, CrewAI, etc.

Usage:
    from agent_skill import PrologSkill
    
    skill = PrologSkill(kb_path="prolog/core.pl")
    result = skill.query("parent(john, X).")
    
    # Returns structured response for agent consumption
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engine.core import PrologEngine, Term
from explain.explanation import ExplanationGenerator


class PrologSkill:
    """
    Agent skill interface for Prolog reasoning.
    
    Provides:
    - Query execution
    - Proof trace generation
    - Structured responses
    - Error handling
    """
    
    def __init__(self, kb_path: str = "prolog/core.pl", max_depth: int = 500):
        self.kb_path = kb_path
        self.engine = PrologEngine(max_depth=max_depth)
        self.explanation_gen = ExplanationGenerator()
        self._load_kb()
    
    def _load_kb(self):
        """Load knowledge base into engine."""
        # TODO: Implement proper .pl file parsing
        # For now, use stub facts for demonstration
        
        # Family facts
        from engine.core import Term, Clause
        self.engine.add_clause(Clause(Term("person", [Term("john")])))
        self.engine.add_clause(Clause(Term("person", [Term("alice")])))
        self.engine.add_clause(Clause(Term("person", [Term("bob")])))
        self.engine.add_clause(Clause(Term("parent", [Term("john"), Term("alice")])))
        self.engine.add_clause(Clause(Term("parent", [Term("alice"), Term("bob")])))
        
        # Rules
        self.engine.add_clause(
            Clause(
                Term("ancestor", [Term("X", is_variable=True), Term("Y", is_variable=True)]),
                [Term("parent", [Term("X", is_variable=True), Term("Y", is_variable=True)])]
            )
        )
        self.engine.add_clause(
            Clause(
                Term("ancestor", [Term("X", is_variable=True), Term("Y", is_variable=True)]),
                [
                    Term("parent", [Term("X", is_variable=True), Term("Z", is_variable=True)]),
                    Term("ancestor", [Term("Z", is_variable=True), Term("Y", is_variable=True)])
                ]
            )
        )
        
        # Sibling rule
        self.engine.add_clause(
            Clause(
                Term("sibling", [Term("X", is_variable=True), Term("Y", is_variable=True)]),
                [
                    Term("parent", [Term("P", is_variable=True), Term("X", is_variable=True)]),
                    Term("parent", [Term("P", is_variable=True), Term("Y", is_variable=True)]),
                    Term("\\=", [Term("X", is_variable=True), Term("Y", is_variable=True)])
                ]
            )
        )
        
        # Access control
        self.engine.add_clause(Clause(Term("role", [Term("alice"), Term("admin")])))
        self.engine.add_clause(Clause(Term("permission", [Term("admin"), Term("read")])))
        self.engine.add_clause(Clause(Term("permission", [Term("admin"), Term("write")])))
        
        self.engine.add_clause(
            Clause(
                Term("allowed", [Term("User", is_variable=True), Term("Action", is_variable=True)]),
                [
                    Term("role", [Term("User", is_variable=True), Term("Role", is_variable=True)]),
                    Term("permission", [Term("Role", is_variable=True), Term("Action", is_variable=True)])
                ]
            )
        )
    
    def query(self, query_str: str) -> Dict[str, Any]:
        """
        Execute Prolog query and return structured result.
        
        Args:
            query_str: Prolog query (e.g., "parent(john, X).")
            
        Returns:
            dict with:
            - success: bool
            - bindings: list of variable bindings
            - explanation: human-readable proof
            - proof_trace: detailed execution steps
            - confidence: confidence score (0.0-1.0)
        """
        try:
            # Parse query
            query_term = self._parse_query(query_str)
            
            # Execute
            self.explanation_gen.start_goal(query_term, 0)
            solutions = self.engine.resolve(query_term)
            
            # Generate explanation
            explanation = self.explanation_gen.generate_explanation(solutions, query_term)
            
            # Structure response
            response = {
                "success": explanation["success"],
                "bindings": explanation["first_solution"] or [],
                "explanation": explanation["explanation"],
                "proof_trace": explanation["proof_trace"],
                "confidence": self._calculate_confidence(solutions),
                "query": query_str,
                "num_solutions": len(solutions)
            }
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query_str
            }
    
    def _parse_query(self, query_str: str) -> Term:
        """Parse query string to Term (simplified)."""
        query_str = query_str.strip()
        if query_str.endswith('.'):
            query_str = query_str[:-1]
        
        # Very basic parsing - would need full parser
        if '(' in query_str and query_str.endswith(')'):
            name, rest = query_str.split('(', 1)
            rest = rest[:-1]
            args_strs = [a.strip() for a in rest.split(',')]
            args = []
            for arg in args_strs:
                if arg and (arg[0].isupper() or arg == '_'):
                    args.append(Term(arg, is_variable=True))
                else:
                    args.append(Term(arg))
            return Term(name.strip(), args)
        
        return Term(query_str)
    
    def _calculate_confidence(self, solutions: List) -> float:
        """Calculate confidence in result (simplified)."""
        if not solutions:
            return 0.0
        # TODO: More sophisticated confidence calculation
        return 1.0 if len(solutions) == 1 else 0.8
    
    def get_manifest(self) -> Dict[str, Any]:
        """Get KB manifest for agent context."""
        # TODO: Generate proper manifest
        return {
            "skill": "prolog-reasoning",
            "description": "Deterministic knowledge base with inference",
            "entities": ["john", "alice", "bob"],  # stub
            "predicates": ["parent/2", "ancestor/2"],  # stub
            "query_command": "skill.query('<query>')"
        }
    
    def add_fact(self, fact_str: str) -> bool:
        """Add a fact to the knowledge base."""
        # TODO: Implement fact addition
        return False
    
    def explain_last_query(self) -> str:
        """Get detailed explanation of last query."""
        return self.explanation_gen.generate_short_proof([], Term("dummy"))


# =============================================================================
# AGENT FRAMEWORK INTEGRATIONS
# =============================================================================

class AutoGenSkill:
    """Integration with AutoGen framework."""
    
    def __init__(self, kb_path: str):
        self.skill = PrologSkill(kb_path)
    
    def __call__(self, query: str) -> str:
        """AutoGen function call interface."""
        result = self.skill.query(query)
        return json.dumps(result)


class CrewAISkill:
    """Integration with CrewAI framework."""
    
    def __init__(self, kb_path: str):
        self.skill = PrologSkill(kb_path)
    
    def execute(self, query: str) -> Dict[str, Any]:
        """CrewAI tool interface."""
        return self.skill.query(query)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Initialize skill
    skill = PrologSkill()
    
    # Example queries
    queries = [
        "parent(john, X).",
        "ancestor(john, alice).",
        "sibling(alice, bob)."
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = skill.query(query)
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Explanation: {result['explanation']}")
            print(f"Bindings: {result['bindings']}")
        else:
            print(f"Error: {result.get('error', 'Unknown')}")
    
    # Get manifest
    manifest = skill.get_manifest()
    print(f"\nManifest: {json.dumps(manifest, indent=2)}")
