"""Prolog Engine package exports."""

from .core import Clause, PrologEngine, Substitution, Term
from .constraint_propagation import (
    ConstraintPropagator,
    PropagationProblem,
    PropagationResult,
)

__all__ = [
    "Clause",
    "PrologEngine",
    "Substitution",
    "Term",
    "ConstraintPropagator",
    "PropagationProblem",
    "PropagationResult",
]
