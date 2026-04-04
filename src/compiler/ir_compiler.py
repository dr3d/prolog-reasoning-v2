"""
IR Compiler: Converts structured intermediate representation (IR) to Prolog facts and rules.

Handles:
- JSON IR → Prolog syntax
- Schema validation
- Deduplication
- Type safety
"""

import sys
sys.path.insert(0, "src")

from ir.schema import IR, IRType, AssertionIR, QueryIR, RuleIR
from engine.core import Term, Clause, PrologEngine
from typing import List, Optional, Dict


class IRCompiler:
    """Compile IR to Prolog facts and rules."""
    
    def __init__(self, engine: PrologEngine):
        self.engine = engine
        self.compiled_facts: set = set()  # Track for deduplication
    
    def compile_ir(self, ir: IR) -> Optional[Clause]:
        """
        Compile a single IR instruction to a Clause.
        
        Returns:
            Clause (fact or rule), or None if compilation fails
        """
        if ir.type == IRType.ASSERTION:
            return self._compile_assertion(ir)
        elif ir.type == IRType.QUERY:
            return self._compile_query(ir)
        elif ir.type == IRType.RULE:
            return self._compile_rule(ir)
        else:
            return None
    
    def compile_and_add(self, ir: IR) -> bool:
        """
        Compile IR and add to engine.
        
        Returns:
            True if successful, False otherwise
        """
        clause = self.compile_ir(ir)
        if clause is None:
            return False
        
        # Check for duplicates
        fact_str = str(clause.head)
        if fact_str in self.compiled_facts:
            return True  # Already exists
        
        self.compiled_facts.add(fact_str)
        self.engine.add_clause(clause)
        return True
    
    def _compile_assertion(self, ir: AssertionIR) -> Optional[Clause]:
        """
        Compile assertion: predicate(args...) as a fact.
        
        Example:
            IR: {type: "assertion", predicate: "parent", args: ["john", "alice"]}
            Output: Clause(head=parent(john, alice), body=None)
        """
        head = self._compile_term(ir.predicate, ir.args)
        return Clause(head)
    
    def _compile_query(self, ir: QueryIR) -> Optional[Clause]:
        """
        Compile query: predicate(args...) as a query clause.
        
        For now, just returns the head as a clause (queries are handled at resolution time).
        """
        head = self._compile_term(ir.predicate, ir.args)
        return Clause(head)
    
    def _compile_rule(self, ir: RuleIR) -> Optional[Clause]:
        """
        Compile rule: head :- body.
        
        Example:
            IR: {type: "rule", predicate: "ancestor", args: ["X", "Y"], body: "parent(X, Y)"}
            Output: Clause(head=ancestor(X, Y), body=[parent(X, Y)])
        """
        head = self._compile_term(ir.predicate, ir.args)
        
        if not ir.body:
            return Clause(head)
        
        # Parse body (simplified - would need full parser for complex bodies)
        body_terms = self._parse_body(ir.body)
        return Clause(head, body_terms)
    
    def _compile_term(self, predicate: str, args: List) -> Term:
        """
        Convert IR args to Term args.
        
        Handles:
        - Atoms: "john" → Term("john")
        - Variables: "X" → Term("X", is_variable=True)
        - Numbers: 42 → Term("42", is_number=True)
        - Strings/quoted: "'john'" → Term("john")
        """
        if not args:
            return Term(predicate)
        
        term_args = []
        for arg in args:
            if isinstance(arg, str):
                term_args.append(self._parse_arg(arg))
            elif isinstance(arg, (int, float)):
                term_args.append(Term(str(arg), is_number=True))
            elif isinstance(arg, dict):
                # Nested term
                term_args.append(self._parse_arg(arg))
            else:
                term_args.append(Term(str(arg)))
        
        return Term(predicate, term_args)
    
    def _parse_arg(self, arg) -> Term:
        """
        Parse a single argument to a Term.
        
        Handles:
        - Uppercase or _ → variable
        - Quoted → atom
        - Digits → number
        - Else → atom
        """
        if isinstance(arg, dict):
            # Nested structure like {"term": "age", "args": ["X"]}
            return self._compile_term(arg.get("term", "f"), arg.get("args", []))
        
        arg_str = str(arg).strip()
        
        # Remove quotes
        if arg_str.startswith("'") and arg_str.endswith("'"):
            return Term(arg_str[1:-1])
        
        # Check if variable
        if arg_str[0].isupper() or arg_str == "_":
            return Term(arg_str, is_variable=True)
        
        # Check if number
        try:
            float(arg_str)
            return Term(arg_str, is_number=True)
        except ValueError:
            pass
        
        # Atom
        return Term(arg_str)
    
    def _parse_body(self, body: str) -> List[Term]:
        """
        Parse rule body.
        
        Simplified parser. For "parent(X, Y), ancestor(Y, Z)", returns:
        [parent(X, Y), ancestor(Y, Z)]
        
        TODO: Full Prolog parser
        """
        # Split on commas (naive - doesn't handle nested parens)
        goals = []
        for goal_str in body.split(","):
            goal_str = goal_str.strip()
            if goal_str:
                goals.append(self._parse_goal(goal_str))
        return goals
    
    def _parse_goal(self, goal_str: str) -> Term:
        """Parse a single goal from string."""
        goal_str = goal_str.strip()
        
        # Check for functor(args...)
        if "(" in goal_str and goal_str.endswith(")"):
            name, rest = goal_str.split("(", 1)
            rest = rest[:-1]
            args_strs = [a.strip() for a in rest.split(",")]
            args = [self._parse_arg(a) for a in args_strs]
            return Term(name.strip(), args)
        
        return Term(goal_str)


class IRValidator:
    """Validate IR before compilation."""
    
    def validate(self, ir: IR) -> tuple[bool, List[str]]:
        """
        Validate IR.
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Check type
        try:
            ir.type = IRType(ir.type) if isinstance(ir.type, str) else ir.type
        except ValueError:
            errors.append(f"Invalid IR type: {ir.type}")
            return False, errors
        
        # Check predicate name
        if not ir.predicate or not isinstance(ir.predicate, str):
            errors.append("Predicate must be a non-empty string")
            return False, errors
        
        # Check args
        if ir.args is None:
            errors.append("Args must be a list")
            return False, errors
        
        return len(errors) == 0, errors


if __name__ == "__main__":
    # Test compilation
    engine = PrologEngine()
    compiler = IRCompiler(engine)
    
    # Compile assertions
    ir1 = AssertionIR(predicate="parent", args=["john", "alice"])
    compiler.compile_and_add(ir1)
    
    ir2 = AssertionIR(predicate="parent", args=["alice", "bob"])
    compiler.compile_and_add(ir2)
    
    # Query
    from engine.core import Term as T
    query = T("parent", [T("john"), T("X", is_variable=True)])
    solutions = engine.resolve(query)
    
    print(f"KB size: {len(engine.clauses)}")
    print(f"Query solutions: {solutions}")
