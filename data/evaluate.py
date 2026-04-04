"""
Evaluation Script: Run system against benchmark and generate results.

Compares:
- Pure Prolog (baseline)
- LLM semantic parsing → Prolog
- LLM only (0-shot, few-shot)
"""

import sys
sys.path.insert(0, "src")

import json
from pathlib import Path
from typing import Dict, List, Any
import time

from engine.core import PrologEngine, Term, Clause
from compiler.ir_compiler import IRCompiler, IRValidator
from ir.schema import AssertionIR, QueryIR
from benchmark import BenchmarkDataset


class Evaluator:
    """Run tests and collect metrics."""
    
    def __init__(self):
        self.results = {
            "prolog_baseline": [],
            "ir_compiled": [],
            "lm_only": []  # Placeholder for LLM-only results
        }
        self.metrics = {}
    
    def evaluate_prolog_baseline(self, dataset: BenchmarkDataset) -> Dict[str, Any]:
        """
        Baseline: Pure Prolog (assume facts/rules already parsed).
        """
        results = {
            "name": "prolog_baseline",
            "passed": 0,
            "failed": 0,
            "total": len(dataset.test_cases),
            "details": []
        }
        
        for test in dataset.test_cases:
            try:
                # Load KB
                engine = PrologEngine()
                
                # Add facts/rules
                for fact_str in test.facts:
                    clauses = self._parse_clause(fact_str)
                    for clause in clauses:
                        engine.add_clause(clause)
                
                # Execute query
                query_term = self._parse_query(test.query)
                start_time = time.time()
                solutions = engine.resolve(query_term)
                elapsed = time.time() - start_time
                
                # Check result
                success = (len(solutions) > 0) == test.expected_answer
                
                results["details"].append({
                    "test": test.name,
                    "success": success,
                    "passed": len(solutions) > 0,
                    "expected": test.expected_answer,
                    "time": elapsed
                })
                
                if success:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["details"].append({
                    "test": test.name,
                    "success": False,
                    "error": str(e)
                })
                results["failed"] += 1
        
        results["accuracy"] = results["passed"] / results["total"]
        return results
    
    def _parse_clause(self, clause_str: str) -> List[Clause]:
        """
        Parse Prolog clause string.
        
        Simplified parser - handles:
        - fact(args).
        - rule(X) :- body(X).
        """
        clause_str = clause_str.strip()
        if clause_str.endswith("."):
            clause_str = clause_str[:-1]
        
        if ":-" in clause_str:
            head_str, body_str = clause_str.split(":-", 1)
            head = self._parse_goal(head_str.strip())
            body_terms = [self._parse_goal(g.strip()) for g in body_str.split(",")]
            return [Clause(head, body_terms)]
        else:
            head = self._parse_goal(clause_str)
            return [Clause(head)]
    
    def _parse_query(self, query_str: str) -> Term:
        """Parse query string."""
        query_str = query_str.strip()
        if query_str.startswith("?-"):
            query_str = query_str[2:].strip()
        if query_str.endswith("."):
            query_str = query_str[:-1]
        
        return self._parse_goal(query_str)
    
    def _parse_goal(self, goal_str: str) -> Term:
        """Parse a single goal/term (simplified)."""
        goal_str = goal_str.strip()
        
        # Handle compound terms: f(a, b, c)
        if "(" in goal_str and goal_str.endswith(")"):
            name, rest = goal_str.split("(", 1)
            rest = rest[:-1]
            args_strs = [a.strip() for a in rest.split(",")]
            args = [self._parse_arg(a) for a in args_strs]
            return Term(name.strip(), args)
        
        # Atom or variable
        return self._parse_arg(goal_str)
    
    def _parse_arg(self, arg_str: str) -> Term:
        """Parse an argument."""
        arg_str = arg_str.strip()
        
        # Variable (uppercase)
        if arg_str and (arg_str[0].isupper() or arg_str == "_"):
            return Term(arg_str, is_variable=True)
        
        # Number
        try:
            float(arg_str)
            return Term(arg_str, is_number=True)
        except ValueError:
            pass
        
        # Atom
        return Term(arg_str)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report."""
        return {
            "results": self.results,
            "metrics": self.metrics,
            "summary": {
                "baseline_accuracy": self.results["prolog_baseline"].get("accuracy", 0),
                "tests_run": sum(r.get("total", 0) for r in self.results.values()),
            }
        }


def main():
    """Run full evaluation."""
    # Load dataset
    dataset = BenchmarkDataset()
    print(f"\nLoaded {len(dataset.test_cases)} test cases")
    print(f"Domains: {dataset.summary()}\n")
    
    # Run evaluation
    evaluator = Evaluator()
    print("Running Prolog baseline evaluation...")
    baseline_results = evaluator.evaluate_prolog_baseline(dataset)
    evaluator.results["prolog_baseline"] = baseline_results
    
    # Print results
    print(f"\n{'='*60}")
    print(f"BASELINE RESULTS")
    print(f"{'='*60}")
    print(f"Total: {baseline_results['total']}")
    print(f"Passed: {baseline_results['passed']}")
    print(f"Failed: {baseline_results['failed']}")
    print(f"Accuracy: {baseline_results['accuracy']:.2%}\n")
    
    # Show failures
    failures = [d for d in baseline_results['details'] if not d['success']]
    if failures:
        print(f"Failed tests ({len(failures)}):")
        for f in failures[:5]:  # Show first 5
            print(f"  - {f.get('test', 'unknown')}: {f.get('error', 'wrong result')}")
    
    # Save report
    report_path = Path("data/evaluation_report.json")
    report = evaluator.generate_report()
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
