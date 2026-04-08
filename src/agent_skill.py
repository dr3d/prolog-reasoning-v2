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

from engine.core import Clause, PrologEngine, Term
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

        # Clinical triage facts
        self.engine.add_clause(Clause(Term("patient", [Term("alice")])))
        self.engine.add_clause(Clause(Term("patient", [Term("bob")])))

        self.engine.add_clause(Clause(Term("takes_medication", [Term("alice"), Term("warfarin")])))
        self.engine.add_clause(Clause(Term("takes_medication", [Term("alice"), Term("ibuprofen")])))
        self.engine.add_clause(Clause(Term("takes_medication", [Term("bob"), Term("lisinopril")])))

        self.engine.add_clause(Clause(Term("allergic_to", [Term("alice"), Term("penicillin")])))
        self.engine.add_clause(Clause(Term("renal_risk", [Term("alice")])))

        self.engine.add_clause(Clause(Term("candidate_drug", [Term("alice"), Term("acetaminophen")])))
        self.engine.add_clause(Clause(Term("candidate_drug", [Term("alice"), Term("naproxen")])))
        self.engine.add_clause(Clause(Term("candidate_drug", [Term("alice"), Term("amoxicillin")])))
        self.engine.add_clause(Clause(Term("candidate_drug", [Term("alice"), Term("clopidogrel")])))

        self.engine.add_clause(Clause(Term("interaction", [Term("warfarin"), Term("ibuprofen"), Term("major_bleed")])))
        self.engine.add_clause(Clause(Term("interaction", [Term("warfarin"), Term("clopidogrel"), Term("major_bleed")])))
        self.engine.add_clause(Clause(Term("interaction", [Term("lisinopril"), Term("ibuprofen"), Term("moderate_kidney_stress")])))

        self.engine.add_clause(Clause(Term("drug_class", [Term("amoxicillin"), Term("penicillin_family")])))
        self.engine.add_clause(Clause(Term("drug_class", [Term("ibuprofen"), Term("nsaid")])))
        self.engine.add_clause(Clause(Term("drug_class", [Term("naproxen"), Term("nsaid")])))
        self.engine.add_clause(Clause(Term("drug_class", [Term("acetaminophen"), Term("analgesic_non_nsaid")])))
        self.engine.add_clause(Clause(Term("drug_class", [Term("clopidogrel"), Term("antiplatelet")])))

        # Symmetric interaction helper
        self.engine.add_clause(
            Clause(
                Term("interacts", [Term("DrugA", is_variable=True), Term("DrugB", is_variable=True), Term("Risk", is_variable=True)]),
                [Term("interaction", [Term("DrugA", is_variable=True), Term("DrugB", is_variable=True), Term("Risk", is_variable=True)])]
            )
        )
        self.engine.add_clause(
            Clause(
                Term("interacts", [Term("DrugA", is_variable=True), Term("DrugB", is_variable=True), Term("Risk", is_variable=True)]),
                [Term("interaction", [Term("DrugB", is_variable=True), Term("DrugA", is_variable=True), Term("Risk", is_variable=True)])]
            )
        )

        # Triage status:
        #   contraindicated first, then caution, else safe_candidate/2 succeeds.
        self.engine.add_clause(
            Clause(
                Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("contraindicated"), Term("penicillin_allergy")]),
                [
                    Term("allergic_to", [Term("Patient", is_variable=True), Term("penicillin")]),
                    Term("drug_class", [Term("Drug", is_variable=True), Term("penicillin_family")]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("contraindicated"), Term("major_interaction")]),
                [
                    Term("takes_medication", [Term("Patient", is_variable=True), Term("Existing", is_variable=True)]),
                    Term("interacts", [Term("Drug", is_variable=True), Term("Existing", is_variable=True), Term("major_bleed")]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("caution"), Term("moderate_interaction")]),
                [
                    Term("\\+", [Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("contraindicated"), Term("Any", is_variable=True)])]),
                    Term("takes_medication", [Term("Patient", is_variable=True), Term("Existing", is_variable=True)]),
                    Term("interacts", [Term("Drug", is_variable=True), Term("Existing", is_variable=True), Term("moderate_kidney_stress")]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("caution"), Term("renal_risk_nsaid")]),
                [
                    Term("\\+", [Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("contraindicated"), Term("Any", is_variable=True)])]),
                    Term("renal_risk", [Term("Patient", is_variable=True)]),
                    Term("drug_class", [Term("Drug", is_variable=True), Term("nsaid")]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("safe_candidate", [Term("Patient", is_variable=True), Term("Drug", is_variable=True)]),
                [
                    Term("candidate_drug", [Term("Patient", is_variable=True), Term("Drug", is_variable=True)]),
                    Term("\\+", [Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("contraindicated"), Term("AnyA", is_variable=True)])]),
                    Term("\\+", [Term("triage", [Term("Patient", is_variable=True), Term("Drug", is_variable=True), Term("caution"), Term("AnyB", is_variable=True)])]),
                ],
            )
        )

        # Project dependency / CPM-like reasoning rules (facts are user-provided)
        self.engine.add_clause(
            Clause(
                Term("downstream", [Term("Task", is_variable=True), Term("Dependent", is_variable=True)]),
                [Term("depends_on", [Term("Dependent", is_variable=True), Term("Task", is_variable=True)])],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("downstream", [Term("Task", is_variable=True), Term("Final", is_variable=True)]),
                [
                    Term("depends_on", [Term("Intermediate", is_variable=True), Term("Task", is_variable=True)]),
                    Term("downstream", [Term("Intermediate", is_variable=True), Term("Final", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("blocked_task", [Term("Task", is_variable=True), Term("Supplier", is_variable=True)]),
                [
                    Term("task_supplier", [Term("Task", is_variable=True), Term("Supplier", is_variable=True)]),
                    Term("supplier_status", [Term("Supplier", is_variable=True), Term("delayed")]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("blocked_task", [Term("Task", is_variable=True), Term("Supplier", is_variable=True)]),
                [
                    Term("depends_on", [Term("Task", is_variable=True), Term("Prereq", is_variable=True)]),
                    Term("blocked_task", [Term("Prereq", is_variable=True), Term("Supplier", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("unmet_prereq", [Term("Task", is_variable=True), Term("Prereq", is_variable=True)]),
                [
                    Term("depends_on", [Term("Task", is_variable=True), Term("Prereq", is_variable=True)]),
                    Term("\\+", [Term("completed", [Term("Prereq", is_variable=True)])]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("task_status", [Term("Task", is_variable=True), Term("blocked")]),
                [
                    Term("task", [Term("Task", is_variable=True)]),
                    Term("blocked_task", [Term("Task", is_variable=True), Term("_", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("task_status", [Term("Task", is_variable=True), Term("ready")]),
                [
                    Term("task", [Term("Task", is_variable=True)]),
                    Term("\\+", [Term("blocked_task", [Term("Task", is_variable=True), Term("_", is_variable=True)])]),
                    Term("\\+", [Term("unmet_prereq", [Term("Task", is_variable=True), Term("_", is_variable=True)])]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("task_status", [Term("Task", is_variable=True), Term("waiting")]),
                [
                    Term("task", [Term("Task", is_variable=True)]),
                    Term("\\+", [Term("blocked_task", [Term("Task", is_variable=True), Term("_", is_variable=True)])]),
                    Term("unmet_prereq", [Term("Task", is_variable=True), Term("_", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("safe_to_start", [Term("Task", is_variable=True)]),
                [Term("task_status", [Term("Task", is_variable=True), Term("ready")])],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("waiting_on", [Term("Task", is_variable=True), Term("Prereq", is_variable=True)]),
                [
                    Term("task_status", [Term("Task", is_variable=True), Term("waiting")]),
                    Term("unmet_prereq", [Term("Task", is_variable=True), Term("Prereq", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("impacts_milestone", [Term("Task", is_variable=True), Term("Milestone", is_variable=True)]),
                [
                    Term("milestone", [Term("Milestone", is_variable=True)]),
                    Term("=", [Term("Task", is_variable=True), Term("Milestone", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("impacts_milestone", [Term("Task", is_variable=True), Term("Milestone", is_variable=True)]),
                [
                    Term("milestone", [Term("Milestone", is_variable=True)]),
                    Term("downstream", [Term("Task", is_variable=True), Term("Milestone", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("delayed_milestone", [Term("Milestone", is_variable=True), Term("Supplier", is_variable=True)]),
                [
                    Term("blocked_task", [Term("Task", is_variable=True), Term("Supplier", is_variable=True)]),
                    Term("impacts_milestone", [Term("Task", is_variable=True), Term("Milestone", is_variable=True)]),
                ],
            )
        )

        # Simulation / world-state rules (multi-character locality + conditions)
        self.engine.add_clause(
            Clause(
                Term("asleep", [Term("C", is_variable=True)]),
                [
                    Term("character", [Term("C", is_variable=True)]),
                    Term("time_of_day", [Term("night")]),
                    Term("\\+", [Term("insomnia", [Term("C", is_variable=True)])]),
                    Term("\\+", [Term("status", [Term("C", is_variable=True), Term("guard_duty")])]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("awake", [Term("C", is_variable=True)]),
                [
                    Term("character", [Term("C", is_variable=True)]),
                    Term("\\+", [Term("asleep", [Term("C", is_variable=True)])]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("co_located", [Term("A", is_variable=True), Term("B", is_variable=True), Term("L", is_variable=True)]),
                [
                    Term("at", [Term("A", is_variable=True), Term("L", is_variable=True)]),
                    Term("at", [Term("B", is_variable=True), Term("L", is_variable=True)]),
                    Term("\\=", [Term("A", is_variable=True), Term("B", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("can_move", [Term("C", is_variable=True), Term("To", is_variable=True)]),
                [
                    Term("awake", [Term("C", is_variable=True)]),
                    Term("at", [Term("C", is_variable=True), Term("From", is_variable=True)]),
                    Term("connected", [Term("From", is_variable=True), Term("To", is_variable=True)]),
                    Term("\\+", [Term("status", [Term("C", is_variable=True), Term("rooted")])]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("exposed", [Term("C", is_variable=True)]),
                [
                    Term("weather", [Term("storm")]),
                    Term("at", [Term("C", is_variable=True), Term("docks")]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("needs_rest", [Term("C", is_variable=True)]),
                [
                    Term("hp", [Term("C", is_variable=True), Term("HP", is_variable=True)]),
                    Term("<", [Term("HP", is_variable=True), Term("8", is_number=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("vulnerable", [Term("C", is_variable=True)]),
                [
                    Term("exposed", [Term("C", is_variable=True)]),
                    Term("needs_rest", [Term("C", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("threatened", [Term("C", is_variable=True)]),
                [
                    Term("co_located", [Term("C", is_variable=True), Term("Other", is_variable=True), Term("_L", is_variable=True)]),
                    Term("faction", [Term("C", is_variable=True), Term("F1", is_variable=True)]),
                    Term("faction", [Term("Other", is_variable=True), Term("F2", is_variable=True)]),
                    Term("\\=", [Term("F1", is_variable=True), Term("F2", is_variable=True)]),
                    Term("\\+", [Term("charmed", [Term("Other", is_variable=True), Term("C", is_variable=True)])]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("high_risk", [Term("C", is_variable=True)]),
                [
                    Term("vulnerable", [Term("C", is_variable=True)]),
                    Term("threatened", [Term("C", is_variable=True)]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("can_trade", [Term("A", is_variable=True), Term("B", is_variable=True), Term("L", is_variable=True)]),
                [
                    Term("co_located", [Term("A", is_variable=True), Term("B", is_variable=True), Term("L", is_variable=True)]),
                    Term("awake", [Term("A", is_variable=True)]),
                    Term("awake", [Term("B", is_variable=True)]),
                    Term("\\+", [Term("threatened", [Term("A", is_variable=True)])]),
                    Term("\\+", [Term("threatened", [Term("B", is_variable=True)])]),
                ],
            )
        )
        self.engine.add_clause(
            Clause(
                Term("can_cast_charm", [Term("Caster", is_variable=True), Term("Target", is_variable=True), Term("L", is_variable=True)]),
                [
                    Term("has_item", [Term("Caster", is_variable=True), Term("charm_scroll")]),
                    Term("co_located", [Term("Caster", is_variable=True), Term("Target", is_variable=True), Term("L", is_variable=True)]),
                    Term("awake", [Term("Caster", is_variable=True)]),
                    Term("awake", [Term("Target", is_variable=True)]),
                    Term("\\+", [Term("charmed", [Term("Target", is_variable=True), Term("_By", is_variable=True)])]),
                ],
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
            args_strs = self._split_top_level(rest, ',')
            args = []
            for arg in args_strs:
                if arg and (arg[0].isupper() or arg == '_'):
                    args.append(Term(arg, is_variable=True))
                else:
                    args.append(Term(arg))
            return Term(name.strip(), args)
        
        return Term(query_str)

    def _split_top_level(self, text: str, delimiter: str) -> List[str]:
        """Split by delimiter while respecting nested parentheses."""
        parts: List[str] = []
        current: List[str] = []
        depth = 0

        for ch in text:
            if ch == "(":
                depth += 1
                current.append(ch)
                continue
            if ch == ")":
                depth = max(0, depth - 1)
                current.append(ch)
                continue
            if ch == delimiter and depth == 0:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
                continue
            current.append(ch)

        tail = "".join(current).strip()
        if tail:
            parts.append(tail)
        return parts
    
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
        if ":-" in fact_str:
            return False
        try:
            fact_term = self._parse_query(fact_str)
            if self._contains_variable(fact_term):
                return False
            for clause in self.engine.clauses:
                if clause.head == fact_term and not clause.body:
                    return True
            self.engine.add_clause(Clause(fact_term))
            return True
        except Exception:
            return False

    def add_rule(self, rule_str: str) -> bool:
        """Add a rule to the knowledge base."""
        normalized = (rule_str or "").strip()
        if not normalized:
            return False
        if normalized.endswith("."):
            normalized = normalized[:-1].strip()
        if ":-" not in normalized:
            return False

        try:
            head_text, body_text = normalized.split(":-", 1)
            head_text = head_text.strip()
            body_text = body_text.strip()
            if not head_text or not body_text:
                return False

            head = self._parse_query(head_text)
            body_terms = [self._parse_query(piece) for piece in self._split_top_level(body_text, ",")]
            if not body_terms:
                return False

            clause = Clause(head, body_terms)
            for existing in self.engine.clauses:
                if existing.head == clause.head and (existing.body or []) == clause.body:
                    return True

            self.engine.add_clause(clause)
            return True
        except Exception:
            return False

    def retract_fact(self, fact_str: str) -> bool:
        """Retract one matching fact from the runtime knowledge base."""
        if ":-" in fact_str:
            return False
        try:
            fact_term = self._parse_query(fact_str)
            if self._contains_variable(fact_term):
                return False
            for index, clause in enumerate(self.engine.clauses):
                if clause.head == fact_term and not clause.body:
                    del self.engine.clauses[index]
                    return True
            return False
        except Exception:
            return False

    def _contains_variable(self, term: Term) -> bool:
        """Return True if a term tree contains any variable nodes."""
        if term.is_variable:
            return True
        return any(self._contains_variable(arg) for arg in term.args)
    
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
