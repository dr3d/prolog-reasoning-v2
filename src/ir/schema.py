"""
Structured Intermediate Representation (IR) for Prolog reasoning.

IR serves as the bridge between natural language (parsed by LLM) and Prolog facts/queries.

Example:
    Input (from LLM): "John is the parent of Alice"
    
    IR:
    {
        "type": "assertion",
        "predicate": "parent",
        "args": ["john", "alice"],
        "confidence": 0.95
    }
    
    Output (Prolog): parent(john, alice).

Schema ensures:
- Type safety
- Schema consistency
- Deduplication
- Validation
"""

from typing import Any, Dict, List, Optional, Literal, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json


class PredicateType(str, Enum):
    """Standard predicate types in reasoning systems."""
    RELATION = "relation"          # parent(X, Y), sibling(X, Y)
    ATTRIBUTE = "attribute"        # age(X, N), color(X, red)
    ROLE = "role"                  # role(User, admin)
    PERMISSION = "permission"      # permission(admin, read)
    EVENT = "event"                # event(deploy, '2026-03-31')
    CONSTRAINT = "constraint"      # no negative ages
    RULE = "rule"                  # derived predicates


class IRType(str, Enum):
    """IR instruction types."""
    ASSERTION = "assertion"        # Store a fact
    QUERY = "query"                # Ask a question
    RULE = "rule"                  # Define a derived predicate
    RETRACT = "retract"            # Remove a fact


@dataclass
class Argument:
    """
    Argument to a predicate.
    
    Can be:
    - Constant (atom or number): "john", 42, "2026-03-31"
    - Variable (unification): "X", "Y" (capitalized)
    - Compound (nested): {"term": "age", "args": ["john"]}
    """
    value: Any
    is_variable: bool = False
    type_hint: Optional[str] = None  # "person", "number", "date", etc.
    
    
@dataclass
class PredicateSignature:
    """
    Schema definition for a predicate.
    
    Example:
        PredicateSignature(
            name="parent",
            arity=2,
            arg_types=["person", "person"],
            description="X is the parent of Y"
        )
    """
    name: str
    arity: int
    arg_types: List[str]  # Type of each argument
    description: str = ""
    
    def validate(self, args: List[Any]) -> bool:
        """Check if arguments match signature."""
        if len(args) != self.arity:
            return False
        # TODO: Type checking
        return True


@dataclass
class IR:
    """
    Base structured representation for logical statements.
    """
    predicate: str
    args: List[Any]
    type: IRType
    confidence: float = 1.0  # How confident the LLM was (0.0-1.0)
    source: Optional[str] = None  # Where this came from (e.g., "user", "inference")
    metadata: Optional[Dict[str, Any]] = None  # Extra info
    
    def to_prolog(self) -> str:
        """Convert IR to Prolog syntax."""
        def format_arg(arg):
            if isinstance(arg, str) and len(arg) == 1 and arg.isupper():
                # Variable (X, Y, Z)
                return arg
            elif isinstance(arg, str):
                # Constant - wrap in quotes if contains spaces/special chars
                if any(c in arg for c in " ,()"):
                    return f"'{arg}'"
                return arg
            else:
                # Number or other
                return str(arg)

        args_str = ", ".join(format_arg(arg) for arg in self.args)

        if self.type == IRType.ASSERTION:
            return f"{self.predicate}({args_str})."
        elif self.type == IRType.QUERY:
            return f"?- {self.predicate}({args_str})."
        elif self.type == IRType.RULE:
            # For rules, we need the body
            rule_ir = self.__class__ if hasattr(self, 'body') else None
            if rule_ir and self.body:
                return f"{self.predicate}({args_str}) :- {self.body}."
            else:
                return f"{self.predicate}({args_str})."
        else:
            raise NotImplementedError(f"Prolog generation for {self.type}")
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "IR":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls(
            type=IRType(data["type"]),
            predicate=data["predicate"],
            args=data["args"],
            confidence=data.get("confidence", 1.0),
            source=data.get("source"),
            metadata=data.get("metadata")
        )


@dataclass
class AssertionIR(IR):
    """Assertion: store a fact."""
    type: IRType = IRType.ASSERTION
    
    def __post_init__(self):
        self.type = IRType.ASSERTION


@dataclass
class QueryIR(IR):
    """Query: ask a question."""
    type: IRType = IRType.QUERY
    
    def __post_init__(self):
        self.type = IRType.QUERY


@dataclass
class RuleIR(IR):
    """Rule: define a derived predicate."""
    type: IRType = IRType.RULE
    body: Optional[str] = None  # Prolog rule body (e.g., "parent(X, Y), parent(Y, Z)")
    
    def __post_init__(self):
        self.type = IRType.RULE


@dataclass(frozen=True)
class StateAtom:
    """
    Canonical state representation used by constraint propagation.

    Example:
        StateAtom("machine_ready", ("line_1",))
        StateAtom("has_role", ("alice", "admin"))
    """
    predicate: str
    args: Tuple[Any, ...] = ()


@dataclass
class ConstraintRuleSpec:
    """
    Deterministic implication rule for known-state propagation.

    If all antecedents are satisfied, derive consequent.
    Variables are represented with leading "?" (for example, "?X").
    """
    name: str
    antecedents: List[StateAtom]
    consequent: StateAtom


@dataclass
class DomainConstraintSpec:
    """
    Constraint over variable domains for DoF propagation.

    Supported kinds:
    - allowed_values
    - forbidden_values
    - equal
    - not_equal
    - implication
    """
    kind: str
    left: str
    right: Optional[str] = None
    values: Optional[Set[Any]] = None
    when_value: Optional[Any] = None


@dataclass
class StateDomainLinkSpec:
    """
    Domain restriction activated by a known state.

    When trigger is known, restrict variable domain to allowed_values.
    """
    trigger: StateAtom
    variable: str
    allowed_values: Set[Any]


# =============================================================================
# SCHEMA DEFINITIONS for common domains
# =============================================================================

FAMILY_SCHEMA = {
    "person": PredicateSignature(
        name="person",
        arity=1,
        arg_types=["atom"],
        description="X is a person"
    ),
    "parent": PredicateSignature(
        name="parent",
        arity=2,
        arg_types=["person", "person"],
        description="X is the parent of Y"
    ),
    "sibling": PredicateSignature(
        name="sibling",
        arity=2,
        arg_types=["person", "person"],
        description="X and Y are siblings"
    ),
    "ancestor": PredicateSignature(
        name="ancestor",
        arity=2,
        arg_types=["person", "person"],
        description="X is an ancestor of Y (derived)"
    ),
}

ACCESS_CONTROL_SCHEMA = {
    "user": PredicateSignature(
        name="user",
        arity=1,
        arg_types=["atom"],
        description="X is a user"
    ),
    "role": PredicateSignature(
        name="role",
        arity=2,
        arg_types=["user", "atom"],
        description="X has role Y"
    ),
    "permission": PredicateSignature(
        name="permission",
        arity=2,
        arg_types=["atom", "atom"],
        description="Role X has permission Y"
    ),
    "allowed": PredicateSignature(
        name="allowed",
        arity=2,
        arg_types=["user", "atom"],
        description="User X is allowed action Y (derived)"
    ),
}


# =============================================================================
# IR VALIDATION
# =============================================================================

def validate_ir(ir: IR, schema: Dict[str, PredicateSignature]) -> tuple[bool, List[str]]:
    """
    Validate IR against a schema.
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # Check predicate exists in schema
    if ir.predicate not in schema:
        errors.append(f"Unknown predicate: {ir.predicate}")
        return False, errors
    
    sig = schema[ir.predicate]
    
    # Check arity
    if not sig.validate(ir.args):
        errors.append(
            f"Predicate {ir.predicate} expects {sig.arity} args, got {len(ir.args)}"
        )
        return False, errors
    
    return len(errors) == 0, errors


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Create an assertion
    ir = AssertionIR(
        predicate="parent",
        args=["john", "alice"],
        confidence=0.95,
        source="user"
    )
    
    print("IR JSON:", ir.to_json())
    print("Prolog:", ir.to_prolog())
    
    # Validate
    is_valid, errors = validate_ir(ir, FAMILY_SCHEMA)
    print(f"Valid: {is_valid}, Errors: {errors}")
