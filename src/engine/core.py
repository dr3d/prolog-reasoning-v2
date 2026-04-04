"""
Core Prolog Engine Implementation.

Pure Python Prolog interpreter with:
- Unification
- Backward-chaining inference
- Backtracking
- Built-in predicates (is, findall, negation, cut, etc.)
- Depth filtering (prevent infinite loops)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from copy import deepcopy
import re


@dataclass
class Term:
    """
    Prolog term representation.
    
    Types:
    - Atom: "john", "mary" (lowercase)
    - Number: 42, 3.14
    - Variable: X, Y (uppercase or _)
    - Compound: f(a, b) or parent(john, mary)
    - List: [1, 2, 3] or [H|T]
    """
    name: str
    args: List["Term"] = None
    is_variable: bool = False
    is_number: bool = False
    
    def __init__(self, name: str, args=None, is_variable=False, is_number=False):
        self.name = name
        self.args = args or []
        self.is_variable = is_variable
        self.is_number = is_number
    
    def __repr__(self):
        if self.args:
            args_str = ", ".join(str(arg) for arg in self.args)
            return f"{self.name}({args_str})"
        return self.name
    
    def __eq__(self, other):
        if not isinstance(other, Term):
            return False
        return (self.name == other.name and 
                self.args == other.args and 
                self.is_variable == other.is_variable)
    
    def __hash__(self):
        return hash((self.name, tuple(self.args)))
    
    def copy(self):
        """Deep copy this term."""
        return deepcopy(self)


@dataclass
class Clause:
    """
    Prolog clause: head :- body.
    
    If body is None, it's a fact.
    """
    head: Term
    body: Optional[List[Term]] = None  # Goals in the body
    
    def __repr__(self):
        if self.body:
            body_str = ", ".join(str(t) for t in self.body)
            return f"{self.head} :- {body_str}."
        return f"{self.head}."


class Substitution:
    """Variable substitution/binding."""
    
    def __init__(self, bindings=None):
        self.bindings = bindings or {}
    
    def bind(self, var: str, term: Term) -> "Substitution":
        """Create new substitution with additional binding."""
        new_bindings = self.bindings.copy()
        new_bindings[var] = term
        return Substitution(new_bindings)
    
    def get(self, var: str) -> Optional[Term]:
        """Get binding for variable."""
        return self.bindings.get(var)
    
    def apply(self, term: Term) -> Term:
        """Apply substitution to a term."""
        if term.is_variable:
            binding = self.get(term.name)
            if binding:
                return self.apply(binding)  # Follow chains
            return term
        
        if term.args:
            new_args = [self.apply(arg) for arg in term.args]
            new_term = Term(term.name, new_args)
            return new_term
        
        return term
    
    def compose(self, other: "Substitution") -> "Substitution":
        """Compose two substitutions."""
        # Apply other to all bindings in self
        new_bindings = {}
        for var, term in self.bindings.items():
            new_bindings[var] = other.apply(term)
        
        # Add bindings from other
        for var, term in other.bindings.items():
            if var not in new_bindings:
                new_bindings[var] = term
        
        return Substitution(new_bindings)
    
    def __repr__(self):
        items = [f"{k}: {v}" for k, v in self.bindings.items()]
        return "{" + ", ".join(items) + "}"
    
    def __bool__(self):
        return bool(self.bindings)


class PrologEngine:
    """Pure Python Prolog interpreter."""
    
    def __init__(self, max_depth=500):
        self.clauses: List[Clause] = []
        self.max_depth = max_depth
        self.builtins = {
            "is": self._builtin_is,
            ">": self._builtin_gt,
            "<": self._builtin_lt,
            ">=": self._builtin_gte,
            "=<": self._builtin_lte,
            "=:=": self._builtin_arith_eq,
            "=\\=": self._builtin_arith_neq,
            "\\+": self._builtin_not,
            "!": self._builtin_cut,
            "findall": self._builtin_findall,
            "=": self._builtin_unify,
            "\\=": self._builtin_not_unify,
        }
    
    def add_clause(self, clause: Clause):
        """Add a fact or rule to the KB."""
        self.clauses.append(clause)
    
    def parse_term(self, s: str) -> Term:
        """Parse a string into a Term (simplified)."""
        s = s.strip()
        
        # TODO: Implement full parser
        # For now, handle simple cases
        if "(" in s and s.endswith(")"):
            name, rest = s.split("(", 1)
            rest = rest[:-1]
            args = [self.parse_term(arg.strip()) for arg in rest.split(",")]
            return Term(name, args)
        
        if s[0].isupper() or s == "_":
            return Term(s, is_variable=True)
        
        if s.isdigit():
            return Term(str(int(s)), is_number=True)
        
        return Term(s)
    
    def unify(self, t1: Term, t2: Term, subst: Substitution = None) -> Optional[Substitution]:
        """Unify two terms, returning substitution if successful."""
        if subst is None:
            subst = Substitution()
        
        t1 = subst.apply(t1)
        t2 = subst.apply(t2)
        
        # Same term
        if t1 == t2:
            return subst
        
        # Variable unification
        if t1.is_variable:
            if self._occurs_check(t1.name, t2):
                return None
            return subst.bind(t1.name, t2)
        
        if t2.is_variable:
            if self._occurs_check(t2.name, t1):
                return None
            return subst.bind(t2.name, t1)
        
        # Compound unification
        if t1.name != t2.name or len(t1.args) != len(t2.args):
            return None
        
        for arg1, arg2 in zip(t1.args, t2.args):
            subst = self.unify(arg1, arg2, subst)
            if subst is None:
                return None
        
        return subst
    
    def _occurs_check(self, var: str, term: Term) -> bool:
        """Check if variable occurs in term (prevent infinite structures)."""
        if term.is_variable:
            return term.name == var
        return any(self._occurs_check(var, arg) for arg in term.args)
    
    def resolve(self, goal: Term, subst: Substitution = None, depth: int = 0) -> List[Substitution]:
        """
        Resolve a goal, returning all solutions.
        
        Uses depth-first search with backtracking.
        """
        if subst is None:
            subst = Substitution()
        
        if depth > self.max_depth:
            return []
        
        goal = subst.apply(goal)
        
        # Check if builtin
        if goal.name in self.builtins:
            return self.builtins[goal.name](goal, subst, depth)
        
        solutions = []
        
        # Try to unify with each clause head
        for clause in self.clauses:
            # Rename variables in clause to avoid conflicts
            renamed_clause = self._rename_clause(clause, depth)
            
            # Try to unify goal with clause head
            new_subst = self.unify(goal, renamed_clause.head, subst)
            if new_subst is None:
                continue
            
            # If clause has no body, we found a solution
            if not renamed_clause.body:
                solutions.append(new_subst)
            else:
                # Resolve body goals
                body_solutions = self._resolve_goals(renamed_clause.body, new_subst, depth + 1)
                solutions.extend(body_solutions)
        
        return solutions
    
    def _resolve_goals(self, goals: List[Term], subst: Substitution, depth: int) -> List[Substitution]:
        """Resolve a list of goals."""
        if not goals:
            return [subst]
        
        first_goal = goals[0]
        rest_goals = goals[1:]
        
        solutions = []
        
        # Resolve first goal
        first_solutions = self.resolve(first_goal, subst, depth)
        
        # For each solution to first goal, resolve rest
        for sol in first_solutions:
            rest_solutions = self._resolve_goals(rest_goals, sol, depth)
            solutions.extend(rest_solutions)
        
        return solutions
    
    def _rename_clause(self, clause: Clause, depth: int) -> Clause:
        """Rename variables in clause to avoid conflicts."""
        suffix = f"_{depth}"
        renamed_head = self._rename_term(clause.head, suffix)
        renamed_body = [self._rename_term(t, suffix) for t in clause.body] if clause.body else None
        return Clause(renamed_head, renamed_body)
    
    def _rename_term(self, term: Term, suffix: str) -> Term:
        """Rename all variables in a term."""
        if term.is_variable:
            return Term(term.name + suffix, is_variable=True)
        if term.args:
            new_args = [self._rename_term(arg, suffix) for arg in term.args]
            return Term(term.name, new_args)
        return term
    
    # =============================================================================
    # BUILT-IN PREDICATES
    # =============================================================================
    
    def _builtin_is(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X is Expr — arithmetic evaluation."""
        if len(goal.args) != 2:
            return []
        
        lhs = subst.apply(goal.args[0])
        rhs = subst.apply(goal.args[1])
        
        try:
            value = self._eval_expr(rhs)
            result_term = Term(str(value), is_number=True)
            new_subst = self.unify(lhs, result_term, subst)
            return [new_subst] if new_subst else []
        except:
            return []
    
    def _eval_expr(self, expr: Term) -> float:
        """Evaluate arithmetic expression."""
        if expr.is_number:
            return float(expr.name)
        
        if expr.name == "+":
            return self._eval_expr(expr.args[0]) + self._eval_expr(expr.args[1])
        elif expr.name == "-":
            return self._eval_expr(expr.args[0]) - self._eval_expr(expr.args[1])
        elif expr.name == "*":
            return self._eval_expr(expr.args[0]) * self._eval_expr(expr.args[1])
        elif expr.name == "/":
            return self._eval_expr(expr.args[0]) / self._eval_expr(expr.args[1])
        else:
            raise ValueError(f"Unknown operator: {expr.name}")
    
    def _builtin_gt(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X > Y."""
        if len(goal.args) != 2:
            return []
        try:
            left = self._eval_expr(subst.apply(goal.args[0]))
            right = self._eval_expr(subst.apply(goal.args[1]))
            return [subst] if left > right else []
        except:
            return []
    
    def _builtin_lt(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X < Y."""
        if len(goal.args) != 2:
            return []
        try:
            left = self._eval_expr(subst.apply(goal.args[0]))
            right = self._eval_expr(subst.apply(goal.args[1]))
            return [subst] if left < right else []
        except:
            return []
    
    def _builtin_gte(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X >= Y."""
        if len(goal.args) != 2:
            return []
        try:
            left = self._eval_expr(subst.apply(goal.args[0]))
            right = self._eval_expr(subst.apply(goal.args[1]))
            return [subst] if left >= right else []
        except:
            return []
    
    def _builtin_lte(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X =< Y."""
        if len(goal.args) != 2:
            return []
        try:
            left = self._eval_expr(subst.apply(goal.args[0]))
            right = self._eval_expr(subst.apply(goal.args[1]))
            return [subst] if left <= right else []
        except:
            return []
    
    def _builtin_arith_eq(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X =:= Y — arithmetic equality."""
        if len(goal.args) != 2:
            return []
        try:
            left = self._eval_expr(subst.apply(goal.args[0]))
            right = self._eval_expr(subst.apply(goal.args[1]))
            return [subst] if left == right else []
        except:
            return []
    
    def _builtin_arith_neq(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X =\\= Y — arithmetic inequality."""
        if len(goal.args) != 2:
            return []
        try:
            left = self._eval_expr(subst.apply(goal.args[0]))
            right = self._eval_expr(subst.apply(goal.args[1]))
            return [subst] if left != right else []
        except:
            return []
    
    def _builtin_not(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """\\+ Goal — negation as failure."""
        if len(goal.args) != 1:
            return []
        
        inner_goal = goal.args[0]
        solutions = self.resolve(inner_goal, subst, depth + 1)
        
        # Succeeds if inner goal fails
        return [subst] if not solutions else []
    
    def _builtin_cut(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """! — cut (simplified: just succeed once)."""
        return [subst]
    
    def _builtin_findall(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """findall(Template, Goal, List) — collect all solutions."""
        # TODO: Implement
        return []
    
    def _builtin_unify(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X = Y — unify."""
        if len(goal.args) != 2:
            return []
        new_subst = self.unify(goal.args[0], goal.args[1], subst)
        return [new_subst] if new_subst else []
    
    def _builtin_not_unify(self, goal: Term, subst: Substitution, depth: int) -> List[Substitution]:
        """X \\= Y — not unifiable."""
        if len(goal.args) != 2:
            return []
        new_subst = self.unify(goal.args[0], goal.args[1], subst)
        return [subst] if not new_subst else []


if __name__ == "__main__":
    # Test engine
    engine = PrologEngine()
    
    # Add facts
    engine.add_clause(Clause(Term("parent", [Term("john"), Term("alice")])))
    engine.add_clause(Clause(Term("parent", [Term("alice"), Term("bob")])))
    
    # Add rule: ancestor(X, Y) :- parent(X, Y).
    engine.add_clause(
        Clause(
            Term("ancestor", [Term("X", is_variable=True), Term("Y", is_variable=True)]),
            [Term("parent", [Term("X", is_variable=True), Term("Y", is_variable=True)])]
        )
    )
    
    # Query
    query = Term("ancestor", [Term("john", is_variable=False), Term("X", is_variable=True)])
    solutions = engine.resolve(query)
    
    print(f"Query: {query}")
    print(f"Solutions: {solutions}")
