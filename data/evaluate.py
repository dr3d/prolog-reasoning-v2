"""
Evaluation Script: Run system against benchmark and generate results.

Compares:
- Pure Prolog (baseline)
- LLM semantic parsing → Prolog
- LLM only (0-shot, few-shot)
"""

import sys
sys.path.insert(0, "src")

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
import time

from engine.core import PrologEngine, Term, Clause, Substitution
from compiler.ir_compiler import IRCompiler, IRValidator
from ir.schema import AssertionIR, QueryIR, RuleIR
from benchmark import BenchmarkDataset


def _wilson_ci(passes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score 95% confidence interval for an observed pass rate."""
    if total == 0:
        return 0.0, 0.0
    p = passes / total
    z2n = z * z / total
    centre = p + z2n / 2
    margin = z * math.sqrt(p * (1 - p) / total + z2n / (4 * total))
    denom = 1 + z2n
    return centre / denom - margin / denom, centre / denom + margin / denom


class Evaluator:
    """Run tests and collect metrics."""
    
    def __init__(self):
        self.results = {
            "prolog_baseline": {},
            "ir_compiled": {},
            "lm_only": {}  # Placeholder for LLM-only results
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
                self._add_domain_rules(engine, test.domain)
                
                # Add facts/rules
                for fact_str in test.facts:
                    clauses = self._parse_clause(fact_str)
                    for clause in clauses:
                        engine.add_clause(clause)
                
                # Execute query
                query_goals = self._parse_query_goals(test.query)
                start_time = time.time()
                solutions = self._execute_query(engine, query_goals)
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

    def evaluate_ir_compiled(self, dataset: BenchmarkDataset) -> Dict[str, Any]:
        """
        IR pipeline: assertions/rules -> IR compile -> Prolog execution.
        """
        results = {
            "name": "ir_compiled",
            "passed": 0,
            "failed": 0,
            "total": len(dataset.test_cases),
            "details": []
        }

        validator = IRValidator()

        for test in dataset.test_cases:
            try:
                engine = PrologEngine()
                compiler = IRCompiler(engine)
                self._add_domain_rules(engine, test.domain)

                for fact_str in test.facts:
                    ir_obj = self._fact_to_ir(fact_str)
                    is_valid, errors = validator.validate(ir_obj)
                    if not is_valid:
                        raise ValueError(f"IR validation failed: {errors}")
                    if not compiler.compile_and_add(ir_obj):
                        raise ValueError(f"IR compile failed for: {fact_str}")

                query_goals = self._parse_query_goals(test.query)
                start_time = time.time()
                solutions = self._execute_query(engine, query_goals)
                elapsed = time.time() - start_time

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

    def evaluate_lm_only(self, dataset: BenchmarkDataset) -> Dict[str, Any]:
        """
        LM-only proxy baseline.

        Uses direct fact retrieval and simple expression checks, without adding
        domain-derived rules. This approximates a non-symbolic baseline that
        does not benefit from explicit logical rule compilation.
        """
        results = {
            "name": "lm_only",
            "passed": 0,
            "failed": 0,
            "total": len(dataset.test_cases),
            "details": []
        }

        for test in dataset.test_cases:
            try:
                engine = PrologEngine()

                # Load all user-provided facts and rules (they are part of the
                # problem context, just as prompt text would be for a real LM).
                # Domain rules are NOT injected — that is the key difference from
                # the symbolic baselines.
                for fact_str in test.facts:
                    clauses = self._parse_clause(fact_str)
                    for clause in clauses:
                        engine.add_clause(clause)

                query_goals = self._parse_query_goals(test.query)
                start_time = time.time()
                solutions = self._execute_query(engine, query_goals)
                elapsed = time.time() - start_time

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
            body_terms = [self._parse_goal(g.strip()) for g in self._split_top_level(body_str, ",")]
            return [Clause(head, body_terms)]
        else:
            head = self._parse_goal(clause_str)
            return [Clause(head)]

    def _parse_query_goals(self, query_str: str) -> List[Term]:
        """Parse query string into one or more goals."""
        query_str = query_str.strip()
        if query_str.startswith("?-"):
            query_str = query_str[2:].strip()
        if query_str.endswith("."):
            query_str = query_str[:-1]

        return [self._parse_goal(part.strip()) for part in self._split_top_level(query_str, ",") if part.strip()]

    def _execute_query(self, engine: PrologEngine, goals: List[Term]) -> List[Substitution]:
        """Execute conjunctive query goals."""
        if not goals:
            return []
        if len(goals) == 1:
            return engine.resolve(goals[0])
        return engine._resolve_goals(goals, Substitution(), 0)

    def _split_top_level(self, text: str, delimiter: str) -> List[str]:
        """Split text at delimiter while respecting parentheses nesting."""
        parts: List[str] = []
        current: List[str] = []
        depth = 0

        for ch in text:
            if ch == "(":
                depth += 1
                current.append(ch)
            elif ch == ")":
                depth = max(0, depth - 1)
                current.append(ch)
            elif ch == delimiter and depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(ch)

        if current:
            parts.append("".join(current).strip())
        return parts
    
    def _parse_goal(self, goal_str: str) -> Term:
        """Parse a single goal/term."""
        goal_str = goal_str.strip()

        if goal_str.startswith("\\+"):
            negated = goal_str[2:].strip()
            return Term("\\+", [self._parse_goal(negated)])

        for op in [" is ", " =\\= ", " =:= ", " >= ", " =< ", " \\= ", " = ", " > ", " < "]:
            if op in goal_str:
                left, right = goal_str.split(op, 1)
                return Term(op.strip(), [self._parse_expr(left.strip()), self._parse_expr(right.strip())])
        
        # Handle compound terms: f(a, b, c)
        if "(" in goal_str and goal_str.endswith(")"):
            name, rest = goal_str.split("(", 1)
            rest = rest[:-1]
            args_strs = [a.strip() for a in self._split_top_level(rest, ",")]
            args = [self._parse_arg(a) for a in args_strs]
            return Term(name.strip(), args)
        
        # Atom or variable
        return self._parse_arg(goal_str)

    def _parse_expr(self, expr_str: str) -> Term:
        """Parse arithmetic/logical expression for built-in predicates."""
        expr_str = expr_str.strip()

        # Parse + and - at top level first.
        for op in ["+", "-"]:
            idx = self._find_top_level_operator(expr_str, op)
            if idx != -1:
                left = self._parse_expr(expr_str[:idx])
                right = self._parse_expr(expr_str[idx + 1:])
                return Term(op, [left, right])

        # Parse * and / at top level.
        for op in ["*", "/"]:
            idx = self._find_top_level_operator(expr_str, op)
            if idx != -1:
                left = self._parse_expr(expr_str[:idx])
                right = self._parse_expr(expr_str[idx + 1:])
                return Term(op, [left, right])

        if expr_str.startswith("(") and expr_str.endswith(")"):
            return self._parse_expr(expr_str[1:-1])

        return self._parse_arg(expr_str)

    def _find_top_level_operator(self, expr_str: str, operator: str) -> int:
        """Find operator index outside nested parentheses."""
        depth = 0
        for idx in range(len(expr_str) - 1, -1, -1):
            ch = expr_str[idx]
            if ch == ")":
                depth += 1
            elif ch == "(":
                depth = max(0, depth - 1)
            elif ch == operator and depth == 0:
                return idx
        return -1
    
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

    def _fact_to_ir(self, fact_str: str):
        """Convert a fact/rule string to IR object for IR compilation path."""
        normalized = fact_str.strip()
        if normalized.endswith("."):
            normalized = normalized[:-1]

        if ":-" in normalized:
            head_str, body_str = normalized.split(":-", 1)
            head = self._parse_goal(head_str.strip())
            head_args: List[Any] = []
            for arg in head.args:
                if arg.is_variable:
                    head_args.append(arg.name)
                elif arg.is_number:
                    head_args.append(float(arg.name) if "." in arg.name else int(float(arg.name)))
                else:
                    head_args.append(arg.name)

            return RuleIR(predicate=head.name, args=head_args, body=body_str.strip())

        head = self._parse_goal(normalized)
        head_args = []
        for arg in head.args:
            if arg.is_variable:
                head_args.append(arg.name)
            elif arg.is_number:
                head_args.append(float(arg.name) if "." in arg.name else int(float(arg.name)))
            else:
                head_args.append(arg.name)

        return AssertionIR(predicate=head.name, args=head_args)

    def _add_domain_rules(self, engine: PrologEngine, domain: str):
        """Inject minimal derived rules used by benchmark domains."""
        rule_map = {
            "family": [
                "ancestor(X, Y) :- parent(X, Y).",
                "ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).",
                "sibling(X, Y) :- parent(P, X), parent(P, Y), X \\= Y."
            ],
            "access": [
                "allowed(User, Action) :- role(User, Role), permission(Role, Action)."
            ]
        }

        for rule in rule_map.get(domain, []):
            for clause in self._parse_clause(rule):
                engine.add_clause(clause)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report."""
        tests_run = 0
        for result in self.results.values():
            if isinstance(result, dict):
                tests_run += result.get("total", 0)

        return {
            "results": self.results,
            "metrics": self.metrics,
            "summary": {
                "baseline_accuracy": self.results["prolog_baseline"].get("accuracy", 0),
                "tests_run": tests_run,
            }
        }

    # -------------------------------------------------------------------------
    # Repeated-run statistics
    # -------------------------------------------------------------------------

    def run_repeated(self, dataset, n: int = 5) -> Dict[str, Any]:
        """Run all three evaluators n times and return aggregated statistics.

        For purely deterministic evaluators the accuracy will be identical each
        run; this still gives meaningful timing statistics and produces the
        correct Wilson confidence interval from the single observed pass rate.
        """
        buckets: Dict[str, List[Dict[str, Any]]] = {
            "prolog_baseline": [],
            "ir_compiled": [],
            "lm_only": [],
        }

        for _ in range(n):
            ev = Evaluator()
            buckets["prolog_baseline"].append(ev.evaluate_prolog_baseline(dataset))
            buckets["ir_compiled"].append(ev.evaluate_ir_compiled(dataset))
            buckets["lm_only"].append(ev.evaluate_lm_only(dataset))

        stats: Dict[str, Any] = {}
        for name, runs in buckets.items():
            accuracies = [r["accuracy"] for r in runs]
            passes = runs[0]["passed"]
            total = runs[0]["total"]
            ci_lo, ci_hi = _wilson_ci(passes, total)
            mean_acc = statistics.mean(accuracies)
            std_acc = statistics.stdev(accuracies) if len(accuracies) > 1 else 0.0
            stats[name] = {
                "mean_accuracy": mean_acc,
                "std_accuracy": std_acc,
                "wilson_ci_95": [round(ci_lo, 4), round(ci_hi, 4)],
                "n_runs": n,
                "timing_ms": self._aggregate_timing([r["details"] for r in runs]),
            }
        return stats

    @staticmethod
    def _aggregate_timing(all_details: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Compute per-test mean/std timing (ms) over multiple run detail lists."""
        by_test: Dict[str, List[float]] = {}
        for run_details in all_details:
            for d in run_details:
                name = d.get("test", "unknown")
                by_test.setdefault(name, []).append(d.get("time", 0.0) * 1000)
        return {
            test: {
                "mean_ms": round(statistics.mean(times), 4),
                "std_ms": round(statistics.stdev(times) if len(times) > 1 else 0.0, 4),
            }
            for test, times in by_test.items()
        }


def main():
    """Run full evaluation."""
    parser = argparse.ArgumentParser(description="Run prolog reasoning benchmark evaluation.")
    parser.add_argument(
        "--runs", type=int, default=1,
        help="Number of repeated runs for timing/statistics (default: 1)."
    )
    args = parser.parse_args()

    # Load dataset
    dataset = BenchmarkDataset()
    print(f"\nLoaded {len(dataset.test_cases)} test cases")
    print(f"Domains: {dataset.summary()}\n")
    
    # Run evaluation
    evaluator = Evaluator()
    print("Running Prolog baseline evaluation...")
    baseline_results = evaluator.evaluate_prolog_baseline(dataset)
    evaluator.results["prolog_baseline"] = baseline_results

    print("Running IR-compiled evaluation...")
    ir_results = evaluator.evaluate_ir_compiled(dataset)
    evaluator.results["ir_compiled"] = ir_results

    print("Running LM-only proxy baseline...")
    lm_only_results = evaluator.evaluate_lm_only(dataset)
    evaluator.results["lm_only"] = lm_only_results
    
    # Print results
    print(f"\n{'='*60}")
    print(f"BASELINE RESULTS")
    print(f"{'='*60}")
    print(f"Total: {baseline_results['total']}")
    print(f"Passed: {baseline_results['passed']}")
    print(f"Failed: {baseline_results['failed']}")
    print(f"Accuracy: {baseline_results['accuracy']:.2%}\n")

    print(f"{'='*60}")
    print("IR-COMPILED RESULTS")
    print(f"{'='*60}")
    print(f"Total: {ir_results['total']}")
    print(f"Passed: {ir_results['passed']}")
    print(f"Failed: {ir_results['failed']}")
    print(f"Accuracy: {ir_results['accuracy']:.2%}\n")

    print(f"{'='*60}")
    print("LM-ONLY PROXY RESULTS")
    print(f"{'='*60}")
    print(f"Total: {lm_only_results['total']}")
    print(f"Passed: {lm_only_results['passed']}")
    print(f"Failed: {lm_only_results['failed']}")
    print(f"Accuracy: {lm_only_results['accuracy']:.2%}\n")
    
    # Show failures
    failures = [d for d in lm_only_results['details'] if not d['success']]
    if failures:
        print(f"LM-only failures ({len(failures)}):")
        for f in failures:
            print(f"  - {f.get('test', 'unknown')}: {f.get('error', 'wrong result')}")
        print()

    # Repeated-run statistics
    report = evaluator.generate_report()
    if args.runs > 1:
        print(f"Running {args.runs} repeated passes for statistics...")
        stats = evaluator.run_repeated(dataset, n=args.runs)
        report["repeated_run_stats"] = stats

        print(f"\n{'='*60}")
        print(f"REPEATED-RUN STATISTICS  (n={args.runs})")
        print(f"{'='*60}")
        for ev_name, s in stats.items():
            ci = s["wilson_ci_95"]
            print(
                f"{ev_name:20s}  "
                f"mean={s['mean_accuracy']:.2%}  "
                f"std={s['std_accuracy']:.4f}  "
                f"95% CI [{ci[0]:.2%}, {ci[1]:.2%}]"
            )

    # Save report
    report_path = Path("data/evaluation_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
