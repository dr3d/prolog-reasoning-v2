#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Prolog Reasoning.

Wraps SemanticPrologSkill as an MCP server for use with LM Studio and other MCP clients.

Usage:
    python src/mcp_server.py --kb-path prolog/core.pl
    
For LM Studio, configure in settings.json:
    {
        "mcpServers": {
            "prolog": {
                "command": "python",
                "args": ["path/to/mcp_server.py"]
            }
        }
    }
"""

import json
import sys
import argparse
import re
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from parser.semantic import SemanticPrologSkill
from parser.statement_classifier import StatementClassifier
from engine.core import Term


class PrologMCPServer:
    """MCP Server exposing Prolog reasoning capabilities."""

    SUPPORTED_PROTOCOL_VERSIONS = [
        "2025-11-25",
        "2025-06-18",
        "2025-03-26",
        "2024-11-05",
    ]
    RULE_DERIVED_PREDICATES = {
        "ancestor",
        "sibling",
        "allowed",
        "can_access",
        "child",
        "interacts",
        "triage",
        "safe_candidate",
        "downstream",
        "blocked_task",
        "unmet_prereq",
        "task_status",
        "safe_to_start",
        "waiting_on",
        "impacts_milestone",
        "delayed_milestone",
        "asleep",
        "awake",
        "co_located",
        "can_move",
        "exposed",
        "needs_rest",
        "vulnerable",
        "threatened",
        "high_risk",
        "can_trade",
        "can_cast_charm",
    }
    SUPPORTED_PREDICATES = [
        "parent",
        "sibling",
        "ancestor",
        "child",
        "allergic_to",
        "takes_medication",
        "user",
        "role",
        "permission",
        "access_level",
        "can_access",
        "granted_permission",
        "allowed",
        "patient",
        "renal_risk",
        "candidate_drug",
        "interaction",
        "drug_class",
        "interacts",
        "triage",
        "safe_candidate",
        "task",
        "depends_on",
        "duration_days",
        "task_supplier",
        "supplier_status",
        "completed",
        "milestone",
        "downstream",
        "blocked_task",
        "unmet_prereq",
        "task_status",
        "safe_to_start",
        "waiting_on",
        "impacts_milestone",
        "delayed_milestone",
        "character",
        "location",
        "connected",
        "at",
        "faction",
        "has_item",
        "hp",
        "status",
        "weather",
        "time_of_day",
        "insomnia",
        "charmed",
        "quest_active",
        "asleep",
        "awake",
        "co_located",
        "can_move",
        "exposed",
        "needs_rest",
        "vulnerable",
        "threatened",
        "high_risk",
        "can_trade",
        "can_cast_charm",
    ]
    
    def __init__(self, kb_path: str = "prolog/core.pl"):
        """Initialize the MCP server with a knowledge base."""
        self.kb_path = self._resolve_kb_path(kb_path)
        self.skill = SemanticPrologSkill(kb_path=str(self.kb_path))
        self.statement_classifier = StatementClassifier()
        self._request_id = 0

    def _resolve_kb_path(self, kb_path: str) -> Path:
        """Resolve KB paths relative to the repo root when needed."""
        candidate = Path(kb_path)
        if candidate.is_absolute():
            return candidate

        repo_root = Path(__file__).resolve().parent.parent
        return (repo_root / candidate).resolve()
        
    def get_tools(self) -> list:
        """Return available tools for MCP."""
        return [
            {
                "name": "query_prolog",
                "description": "Query the Prolog knowledge base using natural language. The system will parse your question, validate it against the known facts, and return a logical answer with explanation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query (e.g., 'Who is John's parent?' or 'Is Alice allergic to peanuts?')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "query_logic",
                "description": "Query the Prolog engine with a literal Prolog query string.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Raw Prolog query string (e.g., 'allowed(alice, read).' or 'parent(john, X).')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "query_rows",
                "description": "Query the Prolog engine and return all solution rows projected to query variables.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Raw Prolog query with variables (e.g., 'waiting_on(Task, Prereq).')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "assert_fact",
                "description": "Assert a ground Prolog fact into the runtime KB for this MCP server process.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fact": {
                            "type": "string",
                            "description": "Ground Prolog fact string ending in '.' (e.g., 'depends_on(structure, foundation).')"
                        }
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "bulk_assert_facts",
                "description": "Assert multiple ground Prolog facts into the runtime KB in one call.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "facts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of ground Prolog fact strings."
                        }
                    },
                    "required": ["facts"]
                }
            },
            {
                "name": "retract_fact",
                "description": "Retract one matching ground Prolog fact from the runtime KB for this MCP server process.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fact": {
                            "type": "string",
                            "description": "Ground Prolog fact string ending in '.' to remove."
                        }
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "reset_kb",
                "description": "Reset runtime assertions by reloading the baseline KB into a fresh in-memory skill instance.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "query_prolog_raw",
                "description": "Legacy alias of query_logic (kept for backward compatibility).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Raw Prolog query string (e.g., 'allowed(alice, read).' or 'parent(john, X).')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "query_prolog_rows_raw",
                "description": "Legacy alias of query_rows (kept for backward compatibility).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Raw Prolog query with variables (e.g., 'waiting_on(Task, Prereq).')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "assert_fact_raw",
                "description": "Legacy alias of assert_fact (kept for backward compatibility).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fact": {
                            "type": "string",
                            "description": "Ground Prolog fact string ending in '.' (e.g., 'depends_on(structure, foundation).')"
                        }
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "bulk_assert_facts_raw",
                "description": "Legacy alias of bulk_assert_facts (kept for backward compatibility).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "facts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of ground Prolog fact strings."
                        }
                    },
                    "required": ["facts"]
                }
            },
            {
                "name": "retract_fact_raw",
                "description": "Legacy alias of retract_fact (kept for backward compatibility).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fact": {
                            "type": "string",
                            "description": "Ground Prolog fact string ending in '.' to remove."
                        }
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "reset_runtime_kb",
                "description": "Legacy alias of reset_kb (kept for backward compatibility).",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "classify_statement",
                "description": "Classify a user utterance before querying. Return classification only; do not act on the statement. Useful for distinguishing questions from candidate facts, corrections, preferences, or session context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The raw user utterance to classify."
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "list_known_facts",
                "description": "Show all known entities and relationships in the knowledge base. Useful for understanding what the system knows about.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "explain_error",
                "description": "Get a detailed explanation of what went wrong with a query. Provides 'Did you mean?' suggestions if relevant.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "error_message": {
                            "type": "string",
                            "description": "The error message or issue description"
                        }
                    },
                    "required": ["error_message"]
                }
            },
            {
                "name": "show_system_info",
                "description": "Display information about this Prolog MCP server, capabilities, and how to use it.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def classify_statement(self, text: str) -> Dict[str, Any]:
        """Classify a user utterance for query-vs-ingestion routing."""
        classification = self.statement_classifier.classify(text)
        result = classification.to_dict()
        result.update(
            {
                "status": "success",
                "text": text,
                "message": (
                    "Return classification only. Do not act on the statement. "
                    "This is a routing hint, not a write. The current MCP surface can classify "
                    "candidate facts, but it does not yet persist them."
                ),
            }
        )
        return result

    def _extract_predicate_name(self, result: Dict[str, Any]) -> Optional[str]:
        """Best-effort extraction of the predicate being queried."""
        parsed_ir = result.get("parsed_ir")
        if isinstance(parsed_ir, str):
            try:
                parsed_ir = json.loads(parsed_ir)
            except json.JSONDecodeError:
                parsed_ir = None

        if isinstance(parsed_ir, dict):
            predicate = parsed_ir.get("predicate")
            if predicate:
                return predicate

        nl_query = result.get("nl_query", "")
        pattern = r"\b(" + "|".join(re.escape(name) for name in self.SUPPORTED_PREDICATES) + r")\b"
        match = re.search(pattern, nl_query)
        if match:
            return match.group(1)

        return None

    def _extract_predicate_from_prolog_query(self, query: str) -> Optional[str]:
        """Extract predicate name from a raw Prolog query string."""
        match = re.match(r"^\s*([a-z_][a-z0-9_]*)\s*\(", query.strip(), re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return None

    def _normalize_logic_query(self, query: str) -> str:
        """
        Normalize chat-produced query strings.

        Handles common list/bullet formatting artifacts such as:
        - "- safe_to_start(Task)."
        - "1) waiting_on(Task, Prereq)."
        - "`task_status(Task, Status).`"
        """
        text = (query or "").strip()
        text = text.strip("`").strip()
        text = re.sub(r"^\s*(?:[-*•]\s+|\d+[\)\.:]\s*)", "", text)
        return text.strip()

    def _infer_reasoning_basis(self, predicate: Optional[str]) -> Dict[str, str]:
        """Describe whether the answer is likely fact-based or rule-derived."""
        if not predicate:
            return {
                "kind": "unknown",
                "note": "Could not reliably infer the predicate family for this result."
            }

        if predicate in self.RULE_DERIVED_PREDICATES:
            return {
                "kind": "rule-derived",
                "note": f"The `{predicate}` predicate is typically computed through rules rather than stored as a single explicit fact."
            }

        return {
            "kind": "fact-backed",
            "note": f"The `{predicate}` predicate is typically answered from stored facts, though rules may still participate."
        }

    def _build_answer_short(self, result: Dict[str, Any]) -> str:
        """Short answer suitable for tool-using models."""
        explanation = result.get("explanation", "").strip()
        if explanation:
            first_line = explanation.splitlines()[0].strip()
            if first_line:
                return first_line
        return "Query succeeded."

    def query_prolog(self, query: str) -> Dict[str, Any]:
        """Execute a natural language query against the Prolog KB."""
        result = self.skill.query_nl(query)
        predicate = self._extract_predicate_name(result)
        reasoning_basis = self._infer_reasoning_basis(predicate)
        
        # Format the response for better readability
        if result.get("success"):
            return {
                "status": "success",
                "result_type": "success",
                "predicate": predicate,
                "answer_short": self._build_answer_short(result),
                "answer_detailed": result.get("explanation", "Query succeeded"),
                "confidence": result.get("validation_confidence", 0.0),
                "parsing_confidence": result.get("parsing_confidence", 0.0),
                "domain": result.get("domain", "general"),
                "nl_query": query,
                "reasoning_basis": reasoning_basis,
                "metadata": {
                    "parsed_ir": result.get("parsed_ir"),
                    "proof_trace": result.get("proof_trace", result.get("explanation", "")),
                    "bindings": result.get("bindings"),
                    "num_solutions": result.get("num_solutions")
                }
            }
        else:
            # Return validation or query failure
            if result.get("validation_errors"):
                error_types = [error.get("type") for error in result.get("validation_errors", [])]
                return {
                    "status": "validation_error",
                    "result_type": "validation_error",
                    "predicate": predicate,
                    "error_types": error_types,
                    "errors": result.get("validation_errors", []),
                    "validation_confidence": result.get("validation_confidence", 0.0),
                    "parsing_confidence": result.get("parsing_confidence", 0.0),
                    "nl_query": query,
                    "message": "The system found validation issues before query execution. See the structured errors for suggestions."
                }
            else:
                return {
                    "status": "no_results",
                    "result_type": "no_result",
                    "predicate": predicate,
                    "message": result.get("why_it_failed", "No results found for this query"),
                    "suggestion": result.get("what_to_try", "Try rephrasing your question or adding more facts"),
                    "failure_explanation": result.get("failure_explanation"),
                    "nl_query": query,
                    "reasoning_basis": reasoning_basis
                }

    def query_logic(self, query: str) -> Dict[str, Any]:
        """Execute a literal Prolog query string against the deterministic engine."""
        normalized_query = self._normalize_logic_query(query)
        predicate = self._extract_predicate_from_prolog_query(normalized_query)
        reasoning_basis = self._infer_reasoning_basis(predicate)
        result = self.skill.prolog_skill.query(normalized_query)

        if result.get("success"):
            explanation = result.get("explanation", "Query succeeded").strip()
            first_line = explanation.splitlines()[0].strip() if explanation else "Query succeeded."
            return {
                "status": "success",
                "result_type": "success",
                "predicate": predicate,
                "answer_short": first_line,
                "answer_detailed": explanation or "Query succeeded",
                "confidence": result.get("confidence", 0.0),
                "prolog_query": normalized_query,
                "reasoning_basis": reasoning_basis,
                "metadata": {
                    "proof_trace": result.get("proof_trace"),
                    "bindings": result.get("bindings"),
                    "num_solutions": result.get("num_solutions"),
                },
            }

        error = result.get("error")
        if error:
            return {
                "status": "error",
                "result_type": "execution_error",
                "predicate": predicate,
                "prolog_query": normalized_query,
                "message": str(error),
                "reasoning_basis": reasoning_basis,
            }

        return {
            "status": "no_results",
            "result_type": "no_result",
            "predicate": predicate,
            "prolog_query": normalized_query,
            "message": result.get("explanation", "No results found for this query"),
            "reasoning_basis": reasoning_basis,
            "metadata": {
                "proof_trace": result.get("proof_trace"),
                "bindings": result.get("bindings"),
                "num_solutions": result.get("num_solutions"),
            },
        }

    # Legacy compatibility shims (`*_raw`) for older prompts/clients.
    def query_prolog_raw(self, query: str) -> Dict[str, Any]:
        """Legacy alias for query_logic."""
        return self.query_logic(query)

    def _collect_query_variables(self, term: Any) -> List[str]:
        """Collect original variable names from a parsed query term."""
        names: List[str] = []

        def walk(node: Any) -> None:
            if getattr(node, "is_variable", False):
                name = getattr(node, "name", "")
                if isinstance(name, str) and name not in names:
                    names.append(name)
            for arg in getattr(node, "args", []):
                walk(arg)

        walk(term)
        return names

    def query_rows(self, query: str) -> Dict[str, Any]:
        """
        Execute a Prolog query and return all rows projected to query vars.
        """
        normalized_query = self._normalize_logic_query(query)
        predicate = self._extract_predicate_from_prolog_query(normalized_query)
        reasoning_basis = self._infer_reasoning_basis(predicate)

        try:
            query_term = self.skill.prolog_skill._parse_query(normalized_query)
            variable_names = self._collect_query_variables(query_term)
            solutions = self.skill.prolog_skill.engine.resolve(query_term)
        except Exception as error:
            return {
                "status": "error",
                "result_type": "execution_error",
                "predicate": predicate,
                "prolog_query": normalized_query,
                "message": str(error),
                "reasoning_basis": reasoning_basis,
            }

        if not solutions:
            return {
                "status": "no_results",
                "result_type": "no_result",
                "predicate": predicate,
                "prolog_query": normalized_query,
                "variables": variable_names,
                "rows": [],
                "num_rows": 0,
                "reasoning_basis": reasoning_basis,
            }

        rows: List[Dict[str, str]] = []
        seen_rows: Set[str] = set()

        if variable_names:
            for solution in solutions:
                row: Dict[str, str] = {}
                for variable_name in variable_names:
                    bound = solution.apply(Term(variable_name, is_variable=True))
                    row[variable_name] = str(bound)
                key = json.dumps(row, sort_keys=True)
                if key not in seen_rows:
                    seen_rows.add(key)
                    rows.append(row)
        else:
            rows.append({})

        return {
            "status": "success",
            "result_type": "table",
            "predicate": predicate,
            "prolog_query": normalized_query,
            "variables": variable_names,
            "rows": rows,
            "num_rows": len(rows),
            "reasoning_basis": reasoning_basis,
        }

    def query_prolog_rows_raw(self, query: str) -> Dict[str, Any]:
        """Legacy alias for query_rows."""
        return self.query_rows(query)

    def reset_kb(self) -> Dict[str, Any]:
        return self.reset_runtime_kb()

    def _extract_entities_from_fact(self, fact: str) -> Set[str]:
        """Extract atom-like entities from a fact's arguments."""
        entities: Set[str] = set()
        term = None

        parse_method = getattr(self.skill.prolog_skill, "_parse_query", None)
        if parse_method:
            try:
                term = parse_method(fact)
            except Exception:
                term = None

        if term is not None:
            stack: List[Any] = list(getattr(term, "args", []))
            while stack:
                node = stack.pop()
                if getattr(node, "is_variable", False):
                    continue
                args = getattr(node, "args", [])
                if args:
                    stack.extend(args)
                else:
                    name = getattr(node, "name", "")
                    if re.match(r"^[a-z_][a-z0-9_]*$", str(name)):
                        entities.add(str(name))
            return entities

        for token in re.findall(r"\b[a-z_][a-z0-9_]*\b", fact):
            entities.add(token)
        return entities

    def assert_fact(self, fact: str) -> Dict[str, Any]:
        """Assert one runtime fact into the current in-memory KB."""
        normalized = (fact or "").strip()
        if not normalized:
            return {
                "status": "validation_error",
                "message": "No fact provided.",
                "fact": fact,
            }
        if not normalized.endswith("."):
            normalized = normalized + "."

        added = self.skill.prolog_skill.add_fact(normalized)
        if not added:
            return {
                "status": "validation_error",
                "message": "Fact assertion failed. Ensure this is a ground fact (no variables) and not a rule.",
                "fact": normalized,
            }

        if hasattr(self.skill, "validator"):
            self.skill.validator.kb_entities.update(self._extract_entities_from_fact(normalized))

        return {
            "status": "success",
            "result_type": "fact_asserted",
            "fact": normalized,
            "message": "Fact asserted into runtime KB for this server process.",
            "note": "Use reset_kb to clear runtime changes.",
        }

    def assert_fact_raw(self, fact: str) -> Dict[str, Any]:
        """Legacy alias for assert_fact."""
        return self.assert_fact(fact)

    def bulk_assert_facts(self, facts: List[str]) -> Dict[str, Any]:
        """Assert multiple facts in one call."""
        if not isinstance(facts, list) or not facts:
            return {
                "status": "validation_error",
                "message": "facts must be a non-empty list of fact strings.",
                "requested_count": 0,
            }

        successes: List[str] = []
        failures: List[Dict[str, str]] = []
        for raw_fact in facts:
            result = self.assert_fact(str(raw_fact))
            if result.get("status") == "success":
                successes.append(result["fact"])
            else:
                failures.append(
                    {
                        "fact": str(raw_fact),
                        "status": result.get("status", "error"),
                        "message": result.get("message", "Assertion failed."),
                    }
                )

        status = "success" if not failures else "partial_success"
        return {
            "status": status,
            "result_type": "bulk_fact_assertion",
            "requested_count": len(facts),
            "asserted_count": len(successes),
            "failed_count": len(failures),
            "asserted_facts": successes,
            "failed_facts": failures,
            "message": "Bulk assertion complete.",
        }

    def bulk_assert_facts_raw(self, facts: List[str]) -> Dict[str, Any]:
        """Legacy alias for bulk_assert_facts."""
        return self.bulk_assert_facts(facts)

    def retract_fact(self, fact: str) -> Dict[str, Any]:
        """Retract one runtime fact from the current in-memory KB."""
        normalized = (fact or "").strip()
        if not normalized:
            return {
                "status": "validation_error",
                "message": "No fact provided.",
                "fact": fact,
            }
        if not normalized.endswith("."):
            normalized = normalized + "."

        removed = self.skill.prolog_skill.retract_fact(normalized)
        if not removed:
            return {
                "status": "no_results",
                "result_type": "no_result",
                "fact": normalized,
                "message": "No matching fact found to retract.",
            }

        return {
            "status": "success",
            "result_type": "fact_retracted",
            "fact": normalized,
            "message": "Fact retracted from runtime KB.",
        }

    def retract_fact_raw(self, fact: str) -> Dict[str, Any]:
        """Legacy alias for retract_fact."""
        return self.retract_fact(fact)

    def reset_runtime_kb(self) -> Dict[str, Any]:
        """Reset in-memory runtime assertions by recreating the semantic skill."""
        self.skill = SemanticPrologSkill(kb_path=str(self.kb_path))
        return {
            "status": "success",
            "result_type": "runtime_reset",
            "message": "Runtime KB reset to baseline seed state.",
            "knowledge_base_path": str(self.kb_path),
        }
    
    def list_known_facts(self) -> Dict[str, Any]:
        """List known entities plus the supported predicate vocabulary."""
        kb_entities = self.skill.validator.kb_entities if hasattr(self.skill, 'validator') else set()
        
        return {
            "status": "success",
            "known_entities": sorted(list(kb_entities)),
            "supported_predicates": self.SUPPORTED_PREDICATES,
            "predicate_notes": {
                "fact_backed_examples": ["parent", "role", "permission", "allergic_to"],
                "typically_rule_derived": sorted(self.RULE_DERIVED_PREDICATES),
            },
            "note": (
                "This is a summary view of currently known entities plus the predicate vocabulary "
                "the skill knows how to talk about. It is not a full dump of every stored fact, "
                "and a supported predicate does not imply facts exist for every entity."
            ),
            "knowledge_base_path": str(self.kb_path)
        }
    
    def explain_error(self, error_message: str) -> Dict[str, Any]:
        """Provide explanation for an error message."""
        message = (error_message or "").strip()
        lower = message.lower()

        error_type = "generic_error"
        explanation = (
            "The query could not be resolved cleanly. Common causes are unknown entities, "
            "unknown predicates, ambiguous phrasing, or a valid query that simply has no results."
        )
        suggestions = [
            "Check spelling of entity names",
            "Verify the relationship type exists",
            "Use 'list_known_facts' to inspect known entities and supported predicates",
            "Run 'query_prolog' with a simpler question first"
        ]

        entity_match = re.search(r"entity ['\"]?([^'\" ]+)['\"]?", lower)
        predicate_match = re.search(r"(predicate|relationship) ['\"]?([^'\" ]+)['\"]?", lower)

        if "undefined entity" in lower or "not in kb" in lower:
            error_type = "undefined_entity"
            entity = entity_match.group(1) if entity_match else None
            explanation = (
                f"The query refers to an entity that is not currently known to the knowledge base"
                + (f": `{entity}`." if entity else ".")
            )
            suggestions = [
                "Check the spelling of the entity name",
                "Ask about a known entity such as john, alice, bob, admin, read, or write",
                "Use 'list_known_facts' to inspect which entities are currently known",
                "If the entity should exist, add facts for it before querying"
            ]
        elif "unknown predicate" in lower or "ungrounded predicate" in lower or predicate_match:
            error_type = "unknown_predicate"
            predicate = predicate_match.group(2) if predicate_match else None
            explanation = (
                f"The query appears to use a predicate or relationship the skill does not currently recognize"
                + (f": `{predicate}`." if predicate else ".")
            )
            suggestions = [
                "Use 'list_known_facts' to inspect the supported predicate vocabulary",
                "Rephrase the question using relationships like parent, ancestor, sibling, role, or permission",
                "If this relationship is important, extend the knowledge base and parser schema together"
            ]
        elif "no results" in lower or "no solution" in lower or "no solutions" in lower:
            error_type = "no_result"
            explanation = (
                "The query looks structurally valid, but the current knowledge base does not contain facts "
                "that make it succeed."
            )
            suggestions = [
                "Ask a narrower question about a known entity",
                "Check whether the needed supporting facts exist in the KB",
                "Try 'list_known_facts' to see what the system currently knows"
            ]
        elif "ambig" in lower or "unclear" in lower or "could not parse" in lower:
            error_type = "ambiguous_query"
            explanation = (
                "The query is ambiguous or too unclear for the natural-language grounding layer to map cleanly into logic."
            )
            suggestions = [
                "Use a simpler sentence with one relationship",
                "Mention the entity and relationship explicitly",
                "Example: 'Who is John's parent?' or 'Is Alice an ancestor of Bob?'"
            ]

        return {
            "status": "success",
            "error_input": message,
            "error_type": error_type,
            "explanation": explanation,
            "suggestions": suggestions,
            "learn_more": "See the training materials at training/03-learning-from-failures.md"
        }
    
    def show_system_info(self) -> Dict[str, Any]:
        """Show system information and capabilities."""
        return {
            "status": "success",
            "system": "Prolog Reasoning v2",
            "version": "0.5",
            "description": (
                "A local-first neuro-symbolic reliability layer for LLM agents. "
                "Natural language helps express intent; symbolic reasoning decides truth."
            ),
            "knowledge_base_path": str(self.kb_path),
            "core_idea": "Memories are timestamped. Facts are not.",
            "capabilities": [
                "Natural language query processing",
                "Statement classification before query or ingestion decisions",
                "Deterministic knowledge-base reasoning",
                "Runtime fact assertion/retraction for chat-driven scenarios",
                "Semantic validation before query execution",
                "Friendly failure explanations with suggestions",
                "Proof-trace generation"
            ],
            "supported_domains": [
                "Family relationships (parent, sibling, ancestor)",
                "Access control (permissions, roles, users)",
                "Clinical medication triage (deterministic risk flags)",
                "Project dependency risk analysis (CPM-like milestone impact)",
                "General knowledge representations"
            ],
            "example_queries": [
                "Who is John's parent?",
                "Is Alice an ancestor of Bob?",
                "Can admin read files?",
                "What is Bob allergic to?"
            ],
            "learn_more": {
                "getting_started": "See training/01-llm-memory-magic.md",
                "kb_design": "See training/02-knowledge-bases-101.md",
                "error_handling": "See training/03-learning-from-failures.md",
                "lm_studio": "See docs/lm-studio-mcp-guide.md",
                "github": "https://github.com/dr3d/prolog-reasoning-v2"
            }
        }
    
    def handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool calls to appropriate handler."""
        handlers = {
            "query_prolog": lambda: self.query_prolog(tool_input.get("query", "")),
            "query_logic": lambda: self.query_logic(tool_input.get("query", "")),
            "query_rows": lambda: self.query_rows(tool_input.get("query", "")),
            "assert_fact": lambda: self.assert_fact(tool_input.get("fact", "")),
            "bulk_assert_facts": lambda: self.bulk_assert_facts(tool_input.get("facts", [])),
            "retract_fact": lambda: self.retract_fact(tool_input.get("fact", "")),
            "reset_kb": lambda: self.reset_kb(),
            "query_prolog_raw": lambda: self.query_prolog_raw(tool_input.get("query", "")),
            "query_prolog_rows_raw": lambda: self.query_prolog_rows_raw(tool_input.get("query", "")),
            "assert_fact_raw": lambda: self.assert_fact_raw(tool_input.get("fact", "")),
            "bulk_assert_facts_raw": lambda: self.bulk_assert_facts_raw(tool_input.get("facts", [])),
            "retract_fact_raw": lambda: self.retract_fact_raw(tool_input.get("fact", "")),
            "reset_runtime_kb": lambda: self.reset_runtime_kb(),
            "classify_statement": lambda: self.classify_statement(tool_input.get("text", "")),
            "list_known_facts": lambda: self.list_known_facts(),
            "explain_error": lambda: self.explain_error(tool_input.get("error_message", "")),
            "show_system_info": lambda: self.show_system_info()
        }
        
        handler = handlers.get(tool_name)
        if handler:
            try:
                return handler()
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "tool": tool_name
                }
        else:
            return {
                "status": "error",
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(handlers.keys())
            }
    
    def _negotiate_protocol_version(self, requested: Optional[str]) -> str:
        """Return the requested protocol version if supported, else our default."""
        if requested in self.SUPPORTED_PROTOCOL_VERSIONS:
            return requested
        return self.SUPPORTED_PROTOCOL_VERSIONS[0]

    def _format_tool_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap tool output in MCP CallToolResult shape."""
        sanitized = self._json_safe(result)
        is_error = sanitized.get("status") in {"error", "validation_error", "no_results"}
        pretty = json.dumps(sanitized, indent=2)
        return {
            "content": [
                {
                    "type": "text",
                    "text": pretty
                }
            ],
            "structuredContent": sanitized,
            "isError": is_error
        }

    def _json_safe(self, value: Any) -> Any:
        """Convert nested values into JSON-safe structures."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        return str(value)

    def process_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an MCP request (simplified for stdio protocol)."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id", self._request_id)
        self._request_id = request_id + 1

        # MCP clients typically begin with initialize, followed by
        # notifications/initialized before tool discovery.
        if method == "initialize":
            client_info = params.get("clientInfo", {})
            requested_protocol = params.get("protocolVersion")
            negotiated_protocol = self._negotiate_protocol_version(requested_protocol)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": negotiated_protocol,
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "prolog-reasoning",
                        "version": "0.5"
                    },
                    "instructions": (
                        "Use query_prolog for natural-language queries against the "
                        "deterministic Prolog knowledge base. Use list_known_facts "
                        "first if you need to inspect available entities."
                    ),
                    "clientInfoEcho": client_info
                }
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": self.get_tools()
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_input = params.get("arguments", {})
            result = self.handle_tool_call(tool_name, tool_input)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": self._format_tool_result(result)
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Prolog Reasoning MCP Server")
    parser.add_argument("--kb-path", default="prolog/core.pl", help="Path to Prolog knowledge base")
    parser.add_argument("--stdio", action="store_true", help="Use stdio transport (for LM Studio)")
    parser.add_argument("--test", action="store_true", help="Run in test mode (show available tools)")
    args = parser.parse_args()
    
    # Initialize server
    server = PrologMCPServer(kb_path=args.kb_path)
    
    if args.test:
        # Test mode: show available tools and exit
        print("MCP Server initialized successfully\n")
        print("Available Tools:")
        for tool in server.get_tools():
            print(f"  - {tool['name']}: {tool['description']}")
        print("\nExample usage:")
        print('  query_prolog({"query": "Who is John\'s parent?"})')
        sys.exit(0)
    
    if args.stdio:
        # Stdio transport for LM Studio
        print("Prolog Reasoning MCP Server ready", file=sys.stderr)
        print("Reading from stdin, writing to stdout", file=sys.stderr)
        
        try:
            for line in sys.stdin:
                try:
                    payload = json.loads(line)

                    # JSON-RPC batch support: respond with an array of
                    # responses, skipping notifications that return None.
                    if isinstance(payload, list):
                        responses = []
                        for request in payload:
                            response = server.process_request(request)
                            if response is not None:
                                responses.append(response)
                        if responses:
                            print(json.dumps(responses))
                            sys.stdout.flush()
                    else:
                        response = server.process_request(payload)
                        if response is not None:
                            print(json.dumps(response))
                            sys.stdout.flush()
                except json.JSONDecodeError:
                    print(json.dumps({
                        "error": "Invalid JSON",
                        "received": line.strip()
                    }))
                    sys.stdout.flush()
        except KeyboardInterrupt:
            print("Server shutting down", file=sys.stderr)
            sys.exit(0)
    else:
        # Interactive mode for testing
        print("Prolog Reasoning MCP Server (Interactive Mode)")
        print("Available tools:", [t["name"] for t in server.get_tools()])
        print("\nType 'help' for commands, 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if user_input.lower() == "quit":
                    print("Goodbye!")
                    break
                elif user_input.lower() == "help":
                    print("\nAvailable commands:")
                    print("  query <natural language>  - Query the knowledge base")
                    print("  list                     - Show known facts")
                    print("  info                     - System information")
                    print("  help                     - Show this help")
                    print("  quit                     - Exit")
                    print()
                elif user_input.lower().startswith("query "):
                    query = user_input[6:].strip()
                    result = server.query_prolog(query)
                    print(json.dumps(result, indent=2))
                elif user_input.lower() == "list":
                    result = server.list_known_facts()
                    print(json.dumps(result, indent=2))
                elif user_input.lower() == "info":
                    result = server.show_system_info()
                    print(json.dumps(result, indent=2))
                else:
                    print("Unknown command. Type 'help' for options.")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
