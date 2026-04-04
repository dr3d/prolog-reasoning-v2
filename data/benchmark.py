"""
Benchmark Test Cases for Prolog Reasoning System.

Domains:
1. Family Relations (genealogy)
2. Access Control (permissions)
3. Constraint Satisfaction (logical puzzles)
4. Knowledge Inference (multi-hop reasoning)
"""

import json
from typing import List, Dict, Any


class TestCase:
    """A single test case."""
    
    def __init__(self, name: str, domain: str, facts: List[str], query: str, 
                 expected_answer: bool, expected_bindings: List[Dict[str, str]] = None):
        self.name = name
        self.domain = domain
        self.facts = facts
        self.query = query
        self.expected_answer = expected_answer
        self.expected_bindings = expected_bindings or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "facts": self.facts,
            "query": self.query,
            "expected_answer": self.expected_answer,
            "expected_bindings": self.expected_bindings
        }


class BenchmarkDataset:
    """Collection of test cases for evaluation."""
    
    def __init__(self):
        self.test_cases: List[TestCase] = []
        self._build_tests()
    
    def add_test(self, test: TestCase):
        self.test_cases.append(test)
    
    def _build_tests(self):
        """Populate benchmark with test cases."""
        # =============================================================================
        # DOMAIN 1: FAMILY RELATIONS (Genealogy)
        # =============================================================================
        
        # Simple parent query
        self.add_test(TestCase(
            name="parent_direct",
            domain="family",
            facts=[
                "parent(john, alice).",
                "parent(alice, bob).",
                "parent(bob, charlie)."
            ],
            query="parent(john, alice).",
            expected_answer=True
        ))
        
        # Variable binding
        self.add_test(TestCase(
            name="parent_variable",
            domain="family",
            facts=[
                "parent(john, alice).",
                "parent(john, bob)."
            ],
            query="parent(john, X).",
            expected_answer=True,
            expected_bindings=[{"X": "alice"}, {"X": "bob"}]
        ))
        
        # Compound rule: ancestor (direct)
        self.add_test(TestCase(
            name="ancestor_direct_parent",
            domain="family",
            facts=[
                "parent(john, alice).",
                "parent(alice, bob).",
            ],
            query="ancestor(john, alice).",
            expected_answer=True
        ))
        
        # Compound rule: ancestor (transitive)
        self.add_test(TestCase(
            name="ancestor_transitive",
            domain="family",
            facts=[
                "parent(john, alice).",
                "parent(alice, bob).",
                "parent(bob, charlie)."
            ],
            query="ancestor(john, charlie).",
            expected_answer=True
        ))
        
        # Sibling relationship
        self.add_test(TestCase(
            name="sibling",
            domain="family",
            facts=[
                "parent(john, alice).",
                "parent(john, bob)."
            ],
            query="sibling(alice, bob).",
            expected_answer=True
        ))
        
        # Negative case
        self.add_test(TestCase(
            name="parent_not_exists",
            domain="family",
            facts=[
                "parent(john, alice)."
            ],
            query="parent(john, bob).",
            expected_answer=False
        ))
        
        # =============================================================================
        # DOMAIN 2: ACCESS CONTROL (Permissions)
        # =============================================================================
        
        # Simple permission
        self.add_test(TestCase(
            name="permission_direct",
            domain="access",
            facts=[
                "role(alice, admin).",
                "permission(admin, read).",
                "permission(admin, write)."
            ],
            query="allowed(alice, read).",
            expected_answer=True
        ))
        
        # Multiple roles
        self.add_test(TestCase(
            name="permission_multiple_roles",
            domain="access",
            facts=[
                "role(alice, admin).",
                "role(alice, user).",
                "permission(admin, delete).",
                "permission(user, read)."
            ],
            query="allowed(alice, delete).",
            expected_answer=True
        ))
        
        # Permission not granted
        self.add_test(TestCase(
            name="permission_denied",
            domain="access",
            facts=[
                "role(alice, user).",
                "permission(user, read)."
            ],
            query="allowed(alice, delete).",
            expected_answer=False
        ))
        
        # =============================================================================
        # DOMAIN 3: LOGICAL CONSTRAINTS (Puzzles)
        # =============================================================================
        
        # Simple comparison
        self.add_test(TestCase(
            name="comparison_greater_than",
            domain="constraint",
            facts=[
                "age(john, 30).",
                "age(alice, 25)."
            ],
            query="age(john, X), age(alice, Y), X > Y.",
            expected_answer=True
        ))
        
        # Arithmetic
        self.add_test(TestCase(
            name="arithmetic_is",
            domain="constraint",
            facts=[],
            query="X is 2 + 3, X =:= 5.",
            expected_answer=True
        ))
        
        # =============================================================================
        # DOMAIN 4: MULTI-HOP REASONING
        # =============================================================================
        
        # Three-hop chain
        self.add_test(TestCase(
            name="three_hop_chain",
            domain="inference",
            facts=[
                "connected(a, b).",
                "connected(b, c).",
                "connected(c, d).",
                "can_reach(X, Y) :- connected(X, Y).",
                "can_reach(X, Z) :- connected(X, Y), can_reach(Y, Z)."
            ],
            query="can_reach(a, d).",
            expected_answer=True
        ))
        
        # Negation as failure
        self.add_test(TestCase(
            name="negation_as_failure",
            domain="inference",
            facts=[
                "bird(tweety).",
                "bird(polly).",
                "penguin(polly).",
                "can_fly(X) :- bird(X), \\+ penguin(X)."
            ],
            query="can_fly(tweety).",
            expected_answer=True
        ))
    
    def save_to_json(self, filepath: str):
        """Export test cases to JSON."""
        data = {
            "dataset": "prolog-reasoning-benchmark",
            "num_tests": len(self.test_cases),
            "tests": [test.to_dict() for test in self.test_cases]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_by_domain(self, domain: str) -> List[TestCase]:
        """Get all tests for a domain."""
        return [t for t in self.test_cases if t.domain == domain]
    
    def summary(self) -> Dict[str, int]:
        """Summary statistics."""
        domains = {}
        for test in self.test_cases:
            domains[test.domain] = domains.get(test.domain, 0) + 1
        return domains


if __name__ == "__main__":
    dataset = BenchmarkDataset()
    
    print(f"Loaded {len(dataset.test_cases)} test cases")
    print(f"Domains: {dataset.summary()}")
    
    # Save to JSON
    dataset.save_to_json("data/benchmark.json")
    print("\nSaved to data/benchmark.json")
    
    # Print a sample
    print("\n--- Sample Tests ---")
    for test in dataset.test_cases[:3]:
        print(f"\n{test.name}:")
        print(f"  Domain: {test.domain}")
        print(f"  Facts: {'; '.join(test.facts[:2])}...")
        print(f"  Query: {test.query}")
        print(f"  Expected: {test.expected_answer}")
