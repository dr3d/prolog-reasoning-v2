"""
Explanation Layer: Generate proof traces and human-readable justifications.

Key responsibility:
- Track inference path during resolution
- Generate proof trees
- Create readable explanations of why a query succeeded/failed
"""

import sys
sys.path.insert(0, "src")

from engine.core import Term, Substitution
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ProofNodeType(str, Enum):
    """Types of nodes in a proof tree."""
    FACT = "fact"           # Base fact from KB
    RULE_HEAD = "rule_head" # Head of a rule
    UNIFICATION = "unify"   # Unification step
    GOAL = "goal"           # A goal being resolved
    SUCCESS = "success"     # Successful resolution
    FAILURE = "failure"     # Failed resolution


@dataclass
class ProofNode:
    """Node in a proof tree."""
    type: ProofNodeType
    term: Term
    depth: int
    solution: Optional[Substitution] = None
    children: List["ProofNode"] = None
    explanation: str = ""
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "term": str(self.term),
            "depth": self.depth,
            "solution": str(self.solution) if self.solution else None,
            "explanation": self.explanation,
            "children": [child.to_dict() for child in self.children]
        }


class ExplanationGenerator:
    """Generate explanations and proof traces."""
    
    def __init__(self):
        self.proof_tree: Optional[ProofNode] = None
        self.all_steps: List[str] = []
    
    def start_goal(self, goal: Term, depth: int):
        """Initialize proof tree for a goal."""
        self.proof_tree = ProofNode(
            type=ProofNodeType.GOAL,
            term=goal,
            depth=depth,
            explanation=f"Attempting to resolve: {goal}"
        )
        self.all_steps = []
    
    def add_fact_used(self, goal: Term, fact: Term, unifier: Substitution, depth: int):
        """Record that a fact was matched."""
        node = ProofNode(
            type=ProofNodeType.FACT,
            term=fact,
            depth=depth,
            solution=unifier,
            explanation=f"Matched fact: {fact}"
        )
        self.all_steps.append(f"[{depth}] Fact: {fact}")
        return node
    
    def add_unification(self, t1: Term, t2: Term, unifier: Optional[Substitution], depth: int):
        """Record unification attempt."""
        if unifier:
            self.all_steps.append(f"[{depth}] SUCCESS: Unified {t1} with {t2}: {unifier}")
        else:
            self.all_steps.append(f"[{depth}] FAIL: Failed to unify {t1} with {t2}")
    
    def add_rule_application(self, head: Term, body: List[Term], depth: int):
        """Record rule application."""
        body_str = ", ".join(str(t) for t in body)
        self.all_steps.append(f"[{depth}] Rule: {head} :- {body_str}")
    
    def add_builtin_call(self, builtin: str, args: List[Term], result: bool, depth: int):
        """Record built-in predicate call."""
        args_str = ", ".join(str(arg) for arg in args)
        status = "SUCCESS" if result else "FAIL"
        self.all_steps.append(f"[{depth}] {status}: Built-in: {builtin}({args_str})")
    
    def generate_explanation(self, solutions: List[Substitution], goal: Term) -> Dict[str, Any]:
        """
        Generate human-readable explanation of query resolution.
        
        Returns:
            dict with keys:
            - success: bool
            - num_solutions: int
            - proof_trace: list of steps
            - first_solution: first binding if any
            - explanation: summary text
        """
        success = len(solutions) > 0
        
        explanation_text = ""
        if success:
            explanation_text = f"SUCCESS: Query '{goal}' succeeded with {len(solutions)} solution(s)."
            if len(solutions) == 1:
                sol = solutions[0]
                bindings = [f"{var}: {term}" for var, term in sol.bindings.items()]
                if bindings:
                    explanation_text += f"\n  Bindings: {', '.join(bindings)}"
                else:
                    explanation_text += "\n  (Ground query confirmed)"
        else:
            explanation_text = f"FAIL: Query '{goal}' failed. No solutions found."
        
        return {
            "success": success,
            "num_solutions": len(solutions),
            "first_solution": solutions[0].bindings if solutions else None,
            "proof_trace": self.all_steps,
            "explanation": explanation_text,
            "tree": self.proof_tree.to_dict() if self.proof_tree else None
        }
    
    def generate_short_proof(self, solutions: List[Substitution], goal: Term) -> str:
        """Generate a short, human-readable proof."""
        if not solutions:
            return f"Cannot prove: {goal}"
        
        proof_lines = [f"Proof of: {goal}"]
        
        for i, sol in enumerate(solutions, 1):
            if sol.bindings:
                bindings_str = ", ".join(f"{k}={v}" for k, v in sol.bindings.items())
                proof_lines.append(f"  Solution {i}: {bindings_str}")
            else:
                proof_lines.append(f"  Solution {i}: (TRUE)")
        
        return "\n".join(proof_lines)


class ProofTracer:
    """
    Enhanced version that builds full proof tree during resolution.
    
    Requires integration into the resolution engine itself.
    """
    
    def __init__(self):
        self.root: Optional[ProofNode] = None
        self.current_node: Optional[ProofNode] = None
    
    def record_goal_attempt(self, goal: Term, depth: int):
        """Record attempt to resolve a goal."""
        node = ProofNode(
            type=ProofNodeType.GOAL,
            term=goal,
            depth=depth,
            explanation=f"Attempt: {goal}"
        )
        
        if self.current_node:
            self.current_node.children.append(node)
        else:
            self.root = node
        
        self.current_node = node
    
    def record_fact_match(self, fact: Term, solution: Substitution):
        """Record successful fact match."""
        node = ProofNode(
            type=ProofNodeType.FACT,
            term=fact,
            depth=self.current_node.depth + 1 if self.current_node else 0,
            solution=solution,
            explanation=f"Fact: {fact}"
        )
        
        if self.current_node:
            self.current_node.children.append(node)
    
    def record_failure(self):
        """Record failed goal resolution."""
        if self.current_node:
            self.current_node.type = ProofNodeType.FAILURE
    
    def record_success(self, solution: Substitution):
        """Record successful resolution."""
        if self.current_node:
            self.current_node.type = ProofNodeType.SUCCESS
            self.current_node.solution = solution
    
    def get_proof_tree(self) -> Optional[ProofNode]:
        """Get the completed proof tree."""
        return self.root


if __name__ == "__main__":
    # Test explanation generator
    from engine.core import Term as T, Substitution as Sub
    
    gen = ExplanationGenerator()
    gen.start_goal(T("parent", [T("john"), T("X", is_variable=True)]), 0)
    
    gen.add_fact_used(
        T("parent", [T("john"), T("X", is_variable=True)]),
        T("parent", [T("john"), T("alice")]),
        Sub({"X": T("alice")}),
        0
    )
    
    solutions = [Sub({"X": T("alice")})]
    result = gen.generate_explanation(solutions, T("parent", [T("john"), T("X", is_variable=True)]))
    
    print(result["explanation"])
    print("\nProof trace:")
    for step in result["proof_trace"]:
        print(f"  {step}")
