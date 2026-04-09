#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server for Prolog Reasoning.

Exposes deterministic Prolog tooling over MCP for LM Studio and other clients.

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
import os
import urllib.error
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from parser.semantic import SemanticPrologSkill
from parser.statement_classifier import StatementClassifier
from engine.core import Term
from write_path.validator import PredicateProposalValidator


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
    DEFAULT_CONTROL_PLANE_POLICY = {
        "clarification_eagerness": 0.0
    }
    DEFAULT_PRETHINKER_BASE_URL = "http://127.0.0.1:1234"
    DEFAULT_PRETHINKER_MODEL = "qwen3.5-4b"
    DEFAULT_PRE_THINK_MODEL = "qwen/qwen3.5-9b"
    DEFAULT_PRE_THINK_SKILL_PATH = "skills/pre-think/SKILL.md"
    DEFAULT_PRE_THINK_HISTORY_TURNS = 6
    DEFAULT_PRE_THINK_HISTORY_PATH = ".tmp_pre_think_history.json"
    DEFAULT_PRE_THINK_KB_INGEST_MODE = "none"
    DEFAULT_PRE_THINK_MAX_CANDIDATE_FACTS = 24
    DEFAULT_PRETHINKER_ENV_FILE = ".env.local"
    DEFAULT_PRETHINKER_TEMPERATURE = 0.0
    DEFAULT_PRETHINKER_CONTEXT_LENGTH = 4000
    DEFAULT_PRETHINKER_TIMEOUT_SECONDS = 120
    DEFAULT_EXPOSE_LEGACY_PRETHINK_TOOLS = False
    PRETHINKER_KINDS = {
        "query",
        "hard_fact",
        "tentative_fact",
        "correction",
        "preference",
        "session_context",
        "instruction",
        "unknown",
    }
    PRETHINKER_OPERATIONS = {
        "query",
        "store_fact",
        "store_tentative",
        "revise_memory",
        "store_preference",
        "store_context",
        "ignore",
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
        self.proposal_validator = self._build_proposal_validator()
        # Reserved policy surface for future routing/clarification behavior.
        # This is intentionally a no-op in current runtime logic.
        self.control_plane_policy = dict(self.DEFAULT_CONTROL_PLANE_POLICY)
        env_file = (
            os.environ.get("PRETHINKER_ENV_FILE", "").strip()
            or os.environ.get("LMSTUDIO_ENV_FILE", "").strip()
            or self.DEFAULT_PRETHINKER_ENV_FILE
        )
        self._load_env_file(env_file)
        self.prethinker_base_url = (
            os.environ.get("PRETHINKER_BASE_URL", "").strip()
            or os.environ.get("LMSTUDIO_BASE_URL", "").strip()
            or self.DEFAULT_PRETHINKER_BASE_URL
        )
        self.prethinker_model = (
            os.environ.get("PRETHINKER_MODEL", "").strip()
            or self.DEFAULT_PRETHINKER_MODEL
        )
        self.pre_think_model = (
            os.environ.get("PRE_THINK_MODEL", "").strip()
            or self.DEFAULT_PRE_THINK_MODEL
        )
        self.pre_think_skill_path = (
            os.environ.get("PRE_THINK_SKILL_PATH", "").strip()
            or self.DEFAULT_PRE_THINK_SKILL_PATH
        )
        self.pre_think_max_history_turns = self._coerce_positive_int(
            os.environ.get("PRE_THINK_HISTORY_TURNS"),
            fallback=self.DEFAULT_PRE_THINK_HISTORY_TURNS,
        )
        self.pre_think_history_path = (
            os.environ.get("PRE_THINK_HISTORY_PATH", "").strip()
            or self.DEFAULT_PRE_THINK_HISTORY_PATH
        )
        self.pre_think_history: List[Dict[str, str]] = self._load_pre_think_history_from_disk(
            self.pre_think_history_path
        )
        self.pre_think_skill_text = self._load_pre_think_skill_text(self.pre_think_skill_path)
        self.expose_legacy_prethink_tools = self._coerce_bool(
            os.environ.get("PRETHINK_EXPOSE_LEGACY_TOOLS"),
            fallback=self.DEFAULT_EXPOSE_LEGACY_PRETHINK_TOOLS,
        )
        prethinker_api_key = (
            os.environ.get("PRETHINKER_API_KEY", "").strip()
            or os.environ.get("LMSTUDIO_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        )
        self.prethinker_api_key = prethinker_api_key or None
        self.prethinker_timeout_seconds = self._coerce_positive_int(
            os.environ.get("PRETHINKER_TIMEOUT_SECONDS"),
            fallback=self.DEFAULT_PRETHINKER_TIMEOUT_SECONDS,
        )
        self._request_id = 0

    def _resolve_kb_path(self, kb_path: str) -> Path:
        """Resolve KB paths relative to the repo root when needed."""
        candidate = Path(kb_path)
        if candidate.is_absolute():
            return candidate

        repo_root = Path(__file__).resolve().parent.parent
        return (repo_root / candidate).resolve()

    def _resolve_repo_relative_path(self, raw_path: str) -> Path:
        """Resolve a path relative to repo root when not absolute."""
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate.resolve()
        repo_root = Path(__file__).resolve().parent.parent
        return (repo_root / candidate).resolve()

    def _load_env_file(self, env_file: str) -> None:
        """Load KEY=VALUE pairs from an env file into process env when missing."""
        if not env_file:
            return
        candidate = Path(env_file)
        if not candidate.is_absolute():
            repo_root = Path(__file__).resolve().parent.parent
            candidate = (repo_root / candidate).resolve()
        if not candidate.exists():
            return
        try:
            lines = candidate.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            return
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value

    def _build_proposal_validator(self) -> PredicateProposalValidator:
        """Create deterministic proposal validator from predicate registry."""
        repo_root = Path(__file__).resolve().parent.parent
        registry_path = repo_root / "data" / "predicate_registry.json"
        return PredicateProposalValidator(str(registry_path))

    def _get_proposal_validator(self) -> PredicateProposalValidator:
        """Lazy getter for tests using __new__ initialization."""
        validator = getattr(self, "proposal_validator", None)
        if validator is None:
            validator = self._build_proposal_validator()
            self.proposal_validator = validator
        return validator

    def _coerce_positive_int(self, value: Any, fallback: int) -> int:
        """Parse a positive int from env/input, falling back when invalid."""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        return parsed if parsed > 0 else fallback

    def _coerce_float(
        self,
        value: Any,
        fallback: float,
        *,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
    ) -> float:
        """Parse float with optional bounds and fallback."""
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = fallback
        if minimum is not None and parsed < minimum:
            parsed = minimum
        if maximum is not None and parsed > maximum:
            parsed = maximum
        return parsed

    def _coerce_bool(self, value: Any, fallback: bool = False) -> bool:
        """Parse booleans robustly from model-ish values."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y"}:
                return True
            if lowered in {"false", "0", "no", "n"}:
                return False
        return fallback

    def _get_prethinker_base_url(self) -> str:
        return (
            getattr(self, "prethinker_base_url", "").strip()
            or self.DEFAULT_PRETHINKER_BASE_URL
        )

    def _get_prethinker_model(self) -> str:
        return (
            getattr(self, "prethinker_model", "").strip()
            or self.DEFAULT_PRETHINKER_MODEL
        )

    def _get_pre_think_model(self) -> str:
        return (
            getattr(self, "pre_think_model", "").strip()
            or self.DEFAULT_PRE_THINK_MODEL
        )

    def _get_pre_think_skill_path(self) -> str:
        return (
            getattr(self, "pre_think_skill_path", "").strip()
            or self.DEFAULT_PRE_THINK_SKILL_PATH
        )

    def _load_pre_think_skill_text(self, raw_path: str) -> str:
        """Load optional pre-think skill guidance from disk."""
        if not raw_path:
            return ""
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            repo_root = Path(__file__).resolve().parent.parent
            candidate = (repo_root / candidate).resolve()
        try:
            text = candidate.read_text(encoding="utf-8-sig").strip()
        except OSError:
            return ""
        if not text:
            return ""
        # Keep prompt bounded to avoid runaway context growth.
        max_chars = 8000
        return text[:max_chars]

    def _get_pre_think_skill_text(self) -> str:
        """Get cached pre-think skill guidance, lazily loading if needed."""
        cached = getattr(self, "pre_think_skill_text", None)
        if isinstance(cached, str):
            return cached
        text = self._load_pre_think_skill_text(self._get_pre_think_skill_path())
        self.pre_think_skill_text = text
        return text

    def _get_pre_think_history(self) -> List[Dict[str, str]]:
        history = getattr(self, "pre_think_history", None)
        if not isinstance(history, list):
            history = []
            self.pre_think_history = history
        return history

    def _get_pre_think_max_history_turns(self) -> int:
        return self._coerce_positive_int(
            getattr(self, "pre_think_max_history_turns", None),
            fallback=self.DEFAULT_PRE_THINK_HISTORY_TURNS,
        )

    def _coerce_pre_think_kb_ingest_mode(self, value: Any) -> str:
        """Normalize pre-think KB ingest mode to a supported value."""
        normalized = (str(value or "").strip().lower() or self.DEFAULT_PRE_THINK_KB_INGEST_MODE)
        if normalized in {"facts", "fact"}:
            return "facts"
        return "none"

    def _normalize_pre_think_candidate_facts(self, raw_value: Any) -> List[str]:
        """Normalize model-proposed candidate facts into unique Prolog fact strings."""
        items: List[str] = []
        if isinstance(raw_value, str):
            parts = re.split(r"[\r\n;]+", raw_value)
            items.extend(part.strip() for part in parts if part.strip())
        elif isinstance(raw_value, list):
            for item in raw_value:
                if isinstance(item, str) and item.strip():
                    items.append(item.strip())

        normalized: List[str] = []
        seen: Set[str] = set()
        for item in items:
            fact = item.strip()
            if not fact:
                continue
            if not fact.endswith("."):
                fact = f"{fact}."
            # Restrict to simple ground-fact-like shapes; no rules or queries.
            if ":-" in fact or "?" in fact:
                continue
            key = fact.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(fact)
        return normalized

    def _get_pre_think_history_path(self) -> str:
        return (
            getattr(self, "pre_think_history_path", "").strip()
            or self.DEFAULT_PRE_THINK_HISTORY_PATH
        )

    def _load_pre_think_history_from_disk(self, raw_path: str) -> List[Dict[str, str]]:
        """Load persisted pre-think history rows from disk."""
        history_path = (raw_path or "").strip()
        if not history_path:
            return []
        try:
            candidate = self._resolve_repo_relative_path(history_path)
        except (TypeError, ValueError, OSError):
            return []
        if not candidate.exists():
            return []
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return []

        if isinstance(payload, dict):
            payload = payload.get("history", [])
        if not isinstance(payload, list):
            return []

        rows: List[Dict[str, str]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            input_utterance = str(item.get("input_utterance", "")).strip()
            processed_utterance = str(item.get("processed_utterance", "")).strip()
            if not input_utterance and not processed_utterance:
                continue
            rows.append(
                {
                    "input_utterance": input_utterance,
                    "processed_utterance": processed_utterance,
                }
            )

        max_turns = self._get_pre_think_max_history_turns()
        if max_turns > 0 and len(rows) > max_turns:
            rows = rows[-max_turns:]
        return rows

    def _persist_pre_think_history_to_disk(self) -> None:
        """Persist current pre-think history rows to disk."""
        history_path = self._get_pre_think_history_path()
        if not history_path:
            return
        try:
            candidate = self._resolve_repo_relative_path(history_path)
        except (TypeError, ValueError, OSError):
            return
        payload: List[Dict[str, str]] = []
        for row in self._get_pre_think_history():
            if not isinstance(row, dict):
                continue
            input_utterance = str(row.get("input_utterance", "")).strip()
            processed_utterance = str(row.get("processed_utterance", "")).strip()
            if not input_utterance and not processed_utterance:
                continue
            payload.append(
                {
                    "input_utterance": input_utterance,
                    "processed_utterance": processed_utterance,
                }
            )
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            return

    def _should_expose_legacy_prethink_tools(self) -> bool:
        """Return whether legacy pre-thinker tools should appear in tools/list."""
        configured = getattr(self, "expose_legacy_prethink_tools", None)
        if configured is None:
            return self._coerce_bool(
                os.environ.get("PRETHINK_EXPOSE_LEGACY_TOOLS"),
                fallback=self.DEFAULT_EXPOSE_LEGACY_PRETHINK_TOOLS,
            )
        return self._coerce_bool(
            configured,
            fallback=self.DEFAULT_EXPOSE_LEGACY_PRETHINK_TOOLS,
        )

    def _render_pre_think_history_block(self) -> str:
        history = self._get_pre_think_history()
        max_turns = self._get_pre_think_max_history_turns()
        if not history or max_turns <= 0:
            return "(none)"
        lines: List[str] = []
        recent = history[-max_turns:]
        for idx, row in enumerate(recent, start=1):
            input_utterance = str(row.get("input_utterance", "")).strip()
            processed_utterance = str(row.get("processed_utterance", "")).strip()
            if not input_utterance and not processed_utterance:
                continue
            lines.append(f"{idx}. input: {input_utterance}")
            lines.append(f"   processed: {processed_utterance}")
        return "\n".join(lines).strip() if lines else "(none)"

    def _record_pre_think_turn(self, *, input_utterance: str, processed_utterance: str) -> None:
        history = self._get_pre_think_history()
        history.append(
            {
                "input_utterance": input_utterance,
                "processed_utterance": processed_utterance,
            }
        )
        max_turns = self._get_pre_think_max_history_turns()
        if max_turns > 0 and len(history) > max_turns:
            del history[: len(history) - max_turns]
        self._persist_pre_think_history_to_disk()

    def _ingest_pre_think_candidate_facts(
        self,
        candidate_facts: List[str],
        *,
        max_candidate_facts: int,
    ) -> Dict[str, Any]:
        """Attempt to assert pre-think candidate facts into runtime KB."""
        limit = self._coerce_positive_int(
            max_candidate_facts,
            fallback=self.DEFAULT_PRE_THINK_MAX_CANDIDATE_FACTS,
        )
        requested = list(candidate_facts or [])
        attempted = requested[:limit]
        ingested_facts: List[str] = []
        rejected_candidate_facts: List[Dict[str, str]] = []

        for fact in attempted:
            result = self.assert_fact(fact)
            if result.get("status") == "success":
                ingested_facts.append(str(result.get("fact", fact)))
            else:
                rejected_candidate_facts.append(
                    {
                        "fact": fact,
                        "status": str(result.get("status", "error")),
                        "message": str(result.get("message", "Fact assertion failed.")),
                    }
                )

        overflow = max(0, len(requested) - len(attempted))
        if overflow:
            rejected_candidate_facts.append(
                {
                    "fact": f"{overflow} additional candidate facts omitted",
                    "status": "skipped",
                    "message": f"Exceeded max_candidate_facts={limit}.",
                }
            )

        return {
            "requested_candidate_facts": len(requested),
            "attempted_candidate_facts": len(attempted),
            "ingested_facts_count": len(ingested_facts),
            "rejected_candidate_facts_count": len(rejected_candidate_facts),
            "ingested_facts": ingested_facts,
            "rejected_candidate_facts": rejected_candidate_facts,
        }

    def _get_prethinker_api_key(self) -> Optional[str]:
        api_key = getattr(self, "prethinker_api_key", None)
        if isinstance(api_key, str):
            api_key = api_key.strip() or None
        return api_key

    def _get_prethinker_timeout_seconds(self) -> int:
        return self._coerce_positive_int(
            getattr(self, "prethinker_timeout_seconds", None),
            fallback=self.DEFAULT_PRETHINKER_TIMEOUT_SECONDS,
        )

    def _post_json(
        self,
        *,
        url: str,
        payload: Dict[str, Any],
        api_key: Optional[str],
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """POST JSON to LM Studio-like endpoints with optional bearer auth."""
        body = json.dumps(payload).encode("utf-8")
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").strip().lower()
        is_localhost = host in {"127.0.0.1", "localhost", "::1"}

        def _send_request(effective_api_key: Optional[str]) -> Dict[str, Any]:
            request = urllib.request.Request(url=url, data=body, method="POST")
            request.add_header("Content-Type", "application/json")
            if effective_api_key:
                request.add_header("Authorization", f"Bearer {effective_api_key}")
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            return _send_request(api_key)
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            # Some LM Studio local configurations enforce auth headers even for localhost.
            # If caller did not provide a key, retry once with a common local default token.
            if error.code == 401 and not api_key and is_localhost:
                fallback_api_key = (
                    os.environ.get("LMSTUDIO_DEFAULT_API_KEY", "").strip()
                    or "lm-studio"
                )
                try:
                    return _send_request(fallback_api_key)
                except urllib.error.HTTPError as retry_error:
                    retry_raw = retry_error.read().decode("utf-8", errors="replace")
                    if retry_error.code == 401:
                        raise RuntimeError(
                            "HTTP 401 from pre-thinker model endpoint. Local LM Studio appears to require "
                            "an API key header. Set PRETHINKER_API_KEY or LMSTUDIO_API_KEY, or disable "
                            "auth enforcement in LM Studio."
                        ) from retry_error
                    raise RuntimeError(f"HTTP {retry_error.code}: {retry_raw}") from retry_error
                except urllib.error.URLError as retry_error:
                    raise RuntimeError(f"Connection error: {retry_error}") from retry_error
            if error.code == 401:
                raise RuntimeError(
                    "HTTP 401 from pre-thinker model endpoint. Set PRETHINKER_API_KEY "
                    "or LMSTUDIO_API_KEY."
                ) from error
            raise RuntimeError(f"HTTP {error.code}: {raw}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Connection error: {error}") from error

    def _extract_message_text(self, response: Dict[str, Any]) -> str:
        """Extract assistant text from LM Studio /api/v1/chat output payload."""
        items = response.get("output", [])
        if not isinstance(items, list):
            return ""

        parts: List[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
        return "\n\n".join(parts).strip()

    def _build_prethinker_input(self, *, text: str, narrative_context: str) -> str:
        """Build structured prompt for pre-thinker JSON assessment."""
        schema = (
            "{"
            "\"kind\":\"query|hard_fact|tentative_fact|correction|preference|session_context|instruction|unknown\","
            "\"confidence\":0.0,"
            "\"needs_clarification\":false,"
            "\"can_persist_now\":false,"
            "\"suggested_operation\":\"query|store_fact|store_tentative|revise_memory|store_preference|store_context|ignore\","
            "\"rationale\":\"short reason\""
            "}"
        )
        context_block = narrative_context.strip()
        if not context_block:
            context_block = "(none)"
        return (
            "You are a pre-thinker for neuro-symbolic ingestion routing.\n"
            "Assess the utterance and return ONLY a single JSON object.\n"
            "No markdown, no code fences, no prose outside JSON.\n"
            "JSON schema:\n"
            f"{schema}\n\n"
            "Rules:\n"
            "- Use tentative_fact for uncertain/hedged claims.\n"
            "- Use hard_fact only when claim is assertive and grounded enough to persist.\n"
            "- Use query for questions.\n"
            "- Use correction for explicit revisions of prior claims.\n"
            "- Set can_persist_now=false whenever needs_clarification=true.\n\n"
            f"Narrative context:\n{context_block}\n\n"
            f"Utterance:\n{text}"
        )

    def _build_pre_think_input(self, *, utterance: str, narrative_context: str) -> str:
        """Build prompt for simple utterance preprocessing before main-model continuation."""
        return self._build_pre_think_input_with_mode(
            utterance=utterance,
            narrative_context=narrative_context,
            handoff_mode="rewrite",
            kb_ingest_mode=self.DEFAULT_PRE_THINK_KB_INGEST_MODE,
        )

    def _build_pre_think_input_with_mode(
        self,
        *,
        utterance: str,
        narrative_context: str,
        handoff_mode: str,
        kb_ingest_mode: str = "none",
    ) -> str:
        """Build prompt for pre-think with rewrite vs answer-proxy handoff modes."""
        context_block = narrative_context.strip()
        if not context_block:
            context_block = "(none)"
        skill_text = self._get_pre_think_skill_text()
        skill_block = (
            "Pre-think SKILL guidance:\n"
            f"{skill_text}\n\n"
            if skill_text
            else "Pre-think SKILL guidance:\n(none)\n\n"
        )
        history_block = self._render_pre_think_history_block()
        normalized_mode = (handoff_mode or "rewrite").strip().lower()
        normalized_ingest_mode = self._coerce_pre_think_kb_ingest_mode(kb_ingest_mode)
        if normalized_mode == "answer_proxy":
            mode_rules = (
                "You are a pre-think proxy-answer generator for a downstream model.\n"
                "The pre-think stage gets first shot: apply SKILL guidance as authoritative policy.\n"
                "Produce the final user-facing answer text directly.\n"
                "The downstream model will echo your output verbatim, so make it complete and correct.\n"
                "Use tools only if explicitly encoded by SKILL guidance; otherwise do not call tools.\n"
            )
            if normalized_ingest_mode == "facts":
                mode_rules += (
                    "Return JSON only with keys:\n"
                    "- processed_utterance: final answer text\n"
                    "- candidate_facts: array of grounded Prolog facts to assert when high confidence\n"
                    "Do not include uncertain facts.\n\n"
                )
            else:
                mode_rules += "Return plain text only (no markdown, no code fences).\n\n"
        else:
            mode_rules = (
                "You are a pre-think utterance processor for a downstream reasoning model.\n"
                "The pre-think stage gets first shot: apply SKILL guidance as authoritative policy.\n"
                "Rewrite the input utterance into a cleaner, more explicit continuation utterance.\n"
                "Keep the original intent, uncertainty, and constraints.\n"
                "If SKILL guidance includes directive transformations (for example translation), apply them.\n"
                "Do NOT answer the question. Do NOT invent facts. Do NOT call tools.\n"
            )
            if normalized_ingest_mode == "facts":
                mode_rules += (
                    "Return JSON only with keys:\n"
                    "- processed_utterance: rewritten continuation text\n"
                    "- candidate_facts: array of grounded Prolog facts to assert when high confidence\n"
                    "Do not include uncertain facts.\n\n"
                )
            else:
                mode_rules += "Return plain text only (no markdown, no code fences).\n\n"
        return (
            mode_rules
            + 
            f"{skill_block}"
            f"Recent pre-think context (most recent last):\n{history_block}\n\n"
            f"Narrative context:\n{context_block}\n\n"
            f"Utterance:\n{utterance}"
        )

    def _extract_first_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract first JSON object found in possibly noisy model output."""
        blob = (text or "").strip()
        if not blob:
            return None
        decoder = json.JSONDecoder()
        for idx, char in enumerate(blob):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(blob[idx:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                return candidate
        return None

    def _validate_prethinker_assessment(self, assessment: Optional[Dict[str, Any]]) -> List[str]:
        """Validate structured pre-thinker JSON contract."""
        if not isinstance(assessment, dict):
            return ["Missing JSON object assessment."]

        errors: List[str] = []
        required = [
            "kind",
            "confidence",
            "needs_clarification",
            "can_persist_now",
            "suggested_operation",
            "rationale",
        ]
        for key in required:
            if key not in assessment:
                errors.append(f"Missing required key: {key}")

        kind = assessment.get("kind")
        if kind not in self.PRETHINKER_KINDS:
            errors.append(f"Invalid kind: {kind}")

        operation = assessment.get("suggested_operation")
        if operation not in self.PRETHINKER_OPERATIONS:
            errors.append(f"Invalid suggested_operation: {operation}")

        confidence = assessment.get("confidence")
        if not isinstance(confidence, (int, float)):
            errors.append("confidence must be numeric.")
        else:
            confidence_float = float(confidence)
            if confidence_float < 0.0 or confidence_float > 1.0:
                errors.append("confidence must be between 0.0 and 1.0.")

        for bool_key in ("needs_clarification", "can_persist_now"):
            if not isinstance(assessment.get(bool_key), bool):
                errors.append(f"{bool_key} must be boolean.")

        rationale = assessment.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append("rationale must be a non-empty string.")

        if (
            isinstance(assessment.get("needs_clarification"), bool)
            and isinstance(assessment.get("can_persist_now"), bool)
            and assessment.get("needs_clarification") is True
            and assessment.get("can_persist_now") is True
        ):
            errors.append("can_persist_now must be false when needs_clarification is true.")

        return errors

    def _normalize_prethinker_kind(self, value: Any) -> str:
        """Normalize model-provided kind labels into canonical taxonomy."""
        raw = str(value or "").strip().lower()
        mapping = {
            "question": "query",
            "fact": "hard_fact",
            "hard": "hard_fact",
            "tentative": "tentative_fact",
            "uncertain_fact": "tentative_fact",
            "preference_note": "preference",
            "context": "session_context",
            "session": "session_context",
            "command": "instruction",
            "none": "unknown",
        }
        return mapping.get(raw, raw)

    def _normalize_prethinker_operation(self, value: Any) -> str:
        """Normalize model operation variants into canonical routing operations."""
        raw = str(value or "").strip().lower()
        mapping = {
            "ask": "query",
            "query_user": "query",
            "store_tentative_fact": "store_tentative",
            "store_tentative_claim": "store_tentative",
            "tentative_store": "store_tentative",
            "store_session_context": "store_context",
            "save_context": "store_context",
            "store_preference_note": "store_preference",
            "revise_fact": "revise_memory",
            "correct_memory": "revise_memory",
            "noop": "ignore",
            "none": "ignore",
            "no_action": "ignore",
        }
        return mapping.get(raw, raw)

    def _normalize_prethinker_assessment(
        self, assessment: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Normalize loose model JSON into canonical pre-thinker assessment keys."""
        if not isinstance(assessment, dict):
            return {}

        kind = self._normalize_prethinker_kind(assessment.get("kind", ""))
        operation = self._normalize_prethinker_operation(
            assessment.get("suggested_operation", "")
        )
        confidence = self._coerce_float(
            assessment.get("confidence"),
            fallback=0.0,
            minimum=0.0,
            maximum=1.0,
        )
        needs_clarification = self._coerce_bool(
            assessment.get("needs_clarification", False),
            fallback=False,
        )
        can_persist_now = self._coerce_bool(
            assessment.get("can_persist_now", False),
            fallback=False,
        )
        rationale = str(assessment.get("rationale", "")).strip()

        normalized = {
            "kind": kind,
            "confidence": confidence,
            "needs_clarification": needs_clarification,
            "can_persist_now": can_persist_now,
            "suggested_operation": operation,
            "rationale": rationale,
        }
        return normalized

    def _map_classifier_operation(self, operation: str) -> str:
        """Map deterministic classifier operations into pre-thinker operation set."""
        mapping = {
            "query": "query",
            "store_fact": "store_fact",
            "store_tentative_fact": "store_tentative",
            "revise_memory": "revise_memory",
            "store_preference": "store_preference",
            "store_session_context": "store_context",
            "follow_instruction": "ignore",
            "none": "ignore",
        }
        return mapping.get(operation, "ignore")

    def _is_write_operation(self, operation: str) -> bool:
        """Return whether operation implies a write-path attempt."""
        return operation in {"store_fact", "store_tentative", "revise_memory"}

    def _build_baseline_prethink_assessment(self, text: str) -> Dict[str, Any]:
        """Build deterministic baseline assessment from classifier + proposal validator."""
        classification = self.statement_classifier.classify(text)
        class_dict = classification.to_dict()
        proposal = self._get_proposal_validator().evaluate(
            text,
            kind=class_dict.get("kind", "unknown"),
            needs_speaker_resolution=bool(class_dict.get("needs_speaker_resolution", False)),
        )

        kind = str(class_dict.get("kind", "unknown"))
        confidence = self._coerce_float(
            class_dict.get("confidence"),
            fallback=0.0,
            minimum=0.0,
            maximum=1.0,
        )
        suggested_operation = self._map_classifier_operation(
            str(class_dict.get("suggested_operation", "none"))
        )
        needs_clarification = bool(class_dict.get("needs_speaker_resolution", False))
        can_persist_now = bool(class_dict.get("can_persist_now", False))
        proposal_status = str(proposal.get("status", "reject"))

        if proposal_status in {"needs_clarification", "reject"}:
            can_persist_now = False
        if proposal_status == "needs_clarification":
            needs_clarification = True

        reasons = class_dict.get("reasons", [])
        reason_text = ", ".join(str(item) for item in reasons) if isinstance(reasons, list) else ""
        rationale = (
            f"classifier={kind}; proposal={proposal_status}"
            + (f"; reasons={reason_text}" if reason_text else "")
        )

        return {
            "kind": kind,
            "confidence": confidence,
            "needs_clarification": needs_clarification,
            "can_persist_now": can_persist_now,
            "suggested_operation": suggested_operation,
            "rationale": rationale,
        }

    def _project_write_path(
        self,
        *,
        text: str,
        assessment: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Project whether a pre-thinker assessment would clear deterministic write-path gates."""
        if not isinstance(assessment, dict):
            assessment = {}

        kind = str(assessment.get("kind", "unknown"))
        operation = str(assessment.get("suggested_operation", "ignore"))
        needs_clarification = self._coerce_bool(
            assessment.get("needs_clarification"),
            fallback=False,
        )
        can_persist_now = self._coerce_bool(
            assessment.get("can_persist_now"),
            fallback=False,
        )
        should_attempt_write = self._is_write_operation(operation)

        proposal_check = self._get_proposal_validator().evaluate(
            text,
            kind=kind,
            needs_speaker_resolution=needs_clarification,
        )
        proposal_status = str(proposal_check.get("status", "reject"))
        write_path_allows = proposal_status == "valid"
        can_write_now = (
            should_attempt_write
            and can_persist_now
            and (not needs_clarification)
            and write_path_allows
        )

        blocking_reasons: List[str] = []
        if not should_attempt_write:
            blocking_reasons.append("operation_not_write_like")
        if not can_persist_now:
            blocking_reasons.append("assessment_can_persist_now_false")
        if needs_clarification:
            blocking_reasons.append("assessment_needs_clarification_true")
        if not write_path_allows:
            blocking_reasons.append(f"proposal_status_{proposal_status}")

        return {
            "kind": kind,
            "suggested_operation": operation,
            "should_attempt_write": should_attempt_write,
            "write_path_allows": write_path_allows,
            "can_write_now": can_write_now,
            "proposal_status": proposal_status,
            "proposal_check": proposal_check,
            "blocking_reasons": blocking_reasons,
        }

    def _assessment_agreement(
        self,
        baseline: Dict[str, Any],
        model_assessment: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute key-field agreement between model output and deterministic baseline."""
        if not isinstance(model_assessment, dict) or not model_assessment:
            return {
                "kind": None,
                "can_persist_now": None,
                "needs_clarification": None,
                "suggested_operation": None,
                "all_core_fields_match": None,
            }

        agreement = {
            "kind": baseline.get("kind") == model_assessment.get("kind"),
            "can_persist_now": baseline.get("can_persist_now") == model_assessment.get("can_persist_now"),
            "needs_clarification": baseline.get("needs_clarification") == model_assessment.get("needs_clarification"),
            "suggested_operation": baseline.get("suggested_operation") == model_assessment.get("suggested_operation"),
        }
        agreement["all_core_fields_match"] = all(
            bool(agreement[field]) for field in ("kind", "can_persist_now", "needs_clarification", "suggested_operation")
        )
        return agreement

    def _normalize_pre_think_output(
        self,
        assistant_message: str,
        *,
        fallback_utterance: str,
    ) -> Dict[str, Any]:
        """Normalize rewrite output into a clean processed utterance with safe fallback."""
        text = (assistant_message or "").strip()
        candidate_facts: List[str] = []
        if not text:
            return {
                "processed_utterance": fallback_utterance,
                "fallback_used": True,
                "normalization_reason": "empty_model_output",
                "candidate_facts": candidate_facts,
            }

        parsed = self._extract_first_json_object(text)
        if isinstance(parsed, dict):
            candidate_facts = self._normalize_pre_think_candidate_facts(
                parsed.get("candidate_facts")
                or parsed.get("facts")
                or parsed.get("assert_facts")
                or []
            )
            for key in ("processed_utterance", "utterance", "text", "output", "rewrite"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    break

        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text.strip())
            text = re.sub(r"\s*```$", "", text).strip()

        lowered = text.lower()
        prefixes = (
            "processed utterance:",
            "rewritten utterance:",
            "rewritten:",
            "output:",
            "processed:",
        )
        for prefix in prefixes:
            if lowered.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return {
                "processed_utterance": fallback_utterance,
                "fallback_used": True,
                "normalization_reason": "empty_after_normalization",
                "candidate_facts": candidate_facts,
            }

        return {
            "processed_utterance": text,
            "fallback_used": False,
            "normalization_reason": "model_output",
            "candidate_facts": candidate_facts,
        }

    def _call_prethinker(
        self,
        *,
        text: str,
        model: str,
        temperature: float,
        context_length: int,
        narrative_context: str,
    ) -> Dict[str, Any]:
        """Forward utterance to pre-thinker model endpoint and return raw payload."""
        endpoint = f"{self._get_prethinker_base_url().rstrip('/')}/api/v1/chat"
        prompt_input = self._build_prethinker_input(
            text=text,
            narrative_context=narrative_context,
        )
        payload = {
            "model": model,
            "input": prompt_input,
            "temperature": temperature,
            "context_length": context_length,
        }
        raw_response = self._post_json(
            url=endpoint,
            payload=payload,
            api_key=self._get_prethinker_api_key(),
            timeout_seconds=self._get_prethinker_timeout_seconds(),
        )
        return {
            "assistant_message": self._extract_message_text(raw_response),
            "raw_response": raw_response,
        }

    def _call_prethink_rewriter(
        self,
        *,
        utterance: str,
        model: str,
        temperature: float,
        context_length: int,
        narrative_context: str,
        handoff_mode: str,
        kb_ingest_mode: str,
    ) -> Dict[str, Any]:
        """Forward utterance to pre-thinker model endpoint for rewrite-style preprocessing."""
        endpoint = f"{self._get_prethinker_base_url().rstrip('/')}/api/v1/chat"
        prompt_input = self._build_pre_think_input_with_mode(
            utterance=utterance,
            narrative_context=narrative_context,
            handoff_mode=handoff_mode,
            kb_ingest_mode=kb_ingest_mode,
        )
        payload = {
            "model": model,
            "input": prompt_input,
            "temperature": temperature,
            "context_length": context_length,
        }
        raw_response = self._post_json(
            url=endpoint,
            payload=payload,
            api_key=self._get_prethinker_api_key(),
            timeout_seconds=self._get_prethinker_timeout_seconds(),
        )
        return {
            "assistant_message": self._extract_message_text(raw_response),
            "raw_response": raw_response,
        }
        
    def get_tools(self) -> list:
        """Return available tools for MCP."""
        tools = [
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
                "name": "assert_rule",
                "description": "Assert a Prolog rule into the runtime KB for this MCP server process.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "rule": {
                            "type": "string",
                            "description": "Prolog rule string ending in '.' (e.g., 'can_enter(P, server_room) :- employee(P), security_clearance(P, 5).')"
                        }
                    },
                    "required": ["rule"]
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
                "name": "kb_empty",
                "description": "Clear the runtime KB to an empty in-memory state (no baseline facts/rules loaded).",
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
                "name": "pre_think",
                "description": "Primary pre-think entrypoint. Process a raw utterance into a cleaned continuation utterance for the downstream model. This call does not mutate the KB.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "utterance": {
                            "type": "string",
                            "description": "Incoming raw utterance to preprocess."
                        },
                        "narrative_context": {
                            "type": "string",
                            "description": "Optional context block used to preserve turn intent while rewriting."
                        },
                        "model": {
                            "type": "string",
                            "description": "Optional model override. Defaults to PRETHINKER_MODEL or a server default."
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Optional sampling temperature override (default 0.0)."
                        },
                        "context_length": {
                            "type": "integer",
                            "description": "Optional context length override for the pre-think request."
                        },
                        "handoff_mode": {
                            "type": "string",
                            "description": "Optional handoff mode: `rewrite` (default) or `answer_proxy`."
                        },
                        "kb_ingest_mode": {
                            "type": "string",
                            "description": "Optional pre-think candidate fact ingestion mode: `none` (default) or `facts`."
                        },
                        "max_candidate_facts": {
                            "type": "integer",
                            "description": "Optional cap for candidate facts to assert when kb_ingest_mode=`facts` (default 24)."
                        }
                    },
                    "required": ["utterance"]
                }
            },
            {
                "name": "prethink_utterance",
                "description": "Legacy diagnostic pre-thinker assessment route. Prefer `pre_think` for normal preprocessing. This call does not mutate the KB.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Incoming utterance to forward to the pre-thinker model."
                        },
                        "narrative_context": {
                            "type": "string",
                            "description": "Optional preceding narrative/context block for the utterance."
                        },
                        "model": {
                            "type": "string",
                            "description": "Optional model override. Defaults to PRETHINKER_MODEL or a server default."
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Optional sampling temperature override (default 0.0)."
                        },
                        "context_length": {
                            "type": "integer",
                            "description": "Optional context length override for the pre-thinker request."
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "prethink_batch",
                "description": "Legacy batch diagnostic route for pre-thinker assessment. Prefer `pre_think` for normal preprocessing. This call does not mutate the KB.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "description": "Array of utterance items. Each item may include text and optional narrative_context.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "narrative_context": {"type": "string"}
                                },
                                "required": ["text"]
                            }
                        },
                        "model": {
                            "type": "string",
                            "description": "Optional model override for all items."
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Optional temperature override for all items."
                        },
                        "context_length": {
                            "type": "integer",
                            "description": "Optional context length override for all items."
                        }
                    },
                    "required": ["items"]
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
            },
            {
                "name": "show_pre_think_state",
                "description": "Inspect pre-think configuration and recent in-process pre-think history for debugging/visibility.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_history": {
                            "type": "boolean",
                            "description": "Whether to include recent pre-think history rows (default true)."
                        },
                        "history_items": {
                            "type": "integer",
                            "description": "Max number of recent history rows to return when include_history=true (default 5)."
                        }
                    }
                }
            }
        ]

        if not self._should_expose_legacy_prethink_tools():
            hidden_tools = {"prethink_utterance", "prethink_batch"}
            tools = [tool for tool in tools if tool.get("name") not in hidden_tools]

        return tools

    def classify_statement(self, text: str) -> Dict[str, Any]:
        """Classify a user utterance for query-vs-ingestion routing."""
        classification = self.statement_classifier.classify(text)
        result = classification.to_dict()
        proposal_check = self._get_proposal_validator().evaluate(
            text,
            kind=result.get("kind", "unknown"),
            needs_speaker_resolution=bool(result.get("needs_speaker_resolution", False)),
        )
        result.update(
            {
                "status": "success",
                "text": text,
                "message": (
                    "Return classification only. Do not act on the statement. "
                    "This is a routing hint, not a write. Runtime write tools exist "
                    "(assert_fact/assert_rule/retract/reset/empty), but classify_statement itself performs no mutation, "
                    "and durable journaled persistence is not implemented yet."
                ),
                "proposal_check": proposal_check,
            }
        )
        return result

    def pre_think(
        self,
        utterance: str,
        narrative_context: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        context_length: Optional[int] = None,
        handoff_mode: Optional[str] = None,
        kb_ingest_mode: Optional[str] = None,
        max_candidate_facts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Preprocess a raw utterance into a cleaner continuation utterance.

        KB mutation is optional and only occurs when kb_ingest_mode=`facts`.
        """
        input_utterance = (utterance or "").strip()
        if not input_utterance:
            return {
                "status": "validation_error",
                "message": "Missing required field: utterance",
                "tool": "pre_think",
            }

        resolved_model = (model or "").strip() or self._get_pre_think_model()
        resolved_temperature = self._coerce_float(
            temperature,
            fallback=self.DEFAULT_PRETHINKER_TEMPERATURE,
            minimum=0.0,
            maximum=2.0,
        )
        resolved_narrative_context = (narrative_context or "").strip()
        resolved_handoff_mode = (handoff_mode or "rewrite").strip().lower()
        if resolved_handoff_mode not in {"rewrite", "answer_proxy"}:
            resolved_handoff_mode = "rewrite"
        resolved_kb_ingest_mode = self._coerce_pre_think_kb_ingest_mode(kb_ingest_mode)
        resolved_max_candidate_facts = self._coerce_positive_int(
            max_candidate_facts,
            fallback=self.DEFAULT_PRE_THINK_MAX_CANDIDATE_FACTS,
        )
        resolved_context_length = self._coerce_positive_int(
            context_length,
            fallback=self.DEFAULT_PRETHINKER_CONTEXT_LENGTH,
        )

        result = self._call_prethink_rewriter(
            utterance=input_utterance,
            model=resolved_model,
            temperature=resolved_temperature,
            context_length=resolved_context_length,
            narrative_context=resolved_narrative_context,
            handoff_mode=resolved_handoff_mode,
            kb_ingest_mode=resolved_kb_ingest_mode,
        )
        assistant_message = result.get("assistant_message", "")
        normalized = self._normalize_pre_think_output(
            assistant_message,
            fallback_utterance=input_utterance,
        )
        candidate_facts = normalized.get("candidate_facts", [])
        if not isinstance(candidate_facts, list):
            candidate_facts = []
        ingest_summary = {
            "requested_candidate_facts": len(candidate_facts),
            "attempted_candidate_facts": 0,
            "ingested_facts_count": 0,
            "rejected_candidate_facts_count": 0,
            "ingested_facts": [],
            "rejected_candidate_facts": [],
        }
        if resolved_kb_ingest_mode == "facts" and candidate_facts:
            ingest_summary = self._ingest_pre_think_candidate_facts(
                candidate_facts,
                max_candidate_facts=resolved_max_candidate_facts,
            )
        self._record_pre_think_turn(
            input_utterance=input_utterance,
            processed_utterance=normalized["processed_utterance"],
        )
        return {
            "status": "success",
            "result_type": "pre_think",
            "input_utterance": input_utterance,
            "processed_utterance": normalized["processed_utterance"],
            "fallback_used": normalized["fallback_used"],
            "normalization_reason": normalized["normalization_reason"],
            "history_turns": len(self._get_pre_think_history()),
            "narrative_context": resolved_narrative_context,
            "handoff_mode": resolved_handoff_mode,
            "kb_ingest_mode": resolved_kb_ingest_mode,
            "max_candidate_facts": resolved_max_candidate_facts,
            "candidate_facts": candidate_facts,
            "requested_candidate_facts": ingest_summary["requested_candidate_facts"],
            "attempted_candidate_facts": ingest_summary["attempted_candidate_facts"],
            "ingested_facts_count": ingest_summary["ingested_facts_count"],
            "rejected_candidate_facts_count": ingest_summary["rejected_candidate_facts_count"],
            "ingested_facts": ingest_summary["ingested_facts"],
            "rejected_candidate_facts": ingest_summary["rejected_candidate_facts"],
            "prethinker_model": resolved_model,
            "pre_think_skill_path": self._get_pre_think_skill_path(),
            "prethinker_base_url": self._get_prethinker_base_url(),
            "temperature": resolved_temperature,
            "context_length": resolved_context_length,
            "assistant_message": assistant_message,
            "raw_response": result.get("raw_response", {}),
            "note": (
                "This tool preprocesses a raw utterance for downstream model reasoning. "
                "KB mutation occurs only when kb_ingest_mode=`facts` and candidate_facts are provided."
            ),
        }

    def prethink_utterance(
        self,
        text: str,
        narrative_context: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        context_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Forward text to pre-thinker LLM, validate output, and project write readiness.

        This method does not mutate KB state. It returns routing and write-path
        projections to support pre-thinker research/automation loops.
        """
        utterance = (text or "").strip()
        if not utterance:
            return {
                "status": "validation_error",
                "message": "Missing required field: text",
                "tool": "prethink_utterance",
            }

        resolved_model = (model or "").strip() or self._get_prethinker_model()
        resolved_temperature = self._coerce_float(
            temperature,
            fallback=self.DEFAULT_PRETHINKER_TEMPERATURE,
            minimum=0.0,
            maximum=2.0,
        )
        resolved_narrative_context = (narrative_context or "").strip()
        resolved_context_length = self._coerce_positive_int(
            context_length,
            fallback=self.DEFAULT_PRETHINKER_CONTEXT_LENGTH,
        )

        result = self._call_prethinker(
            text=utterance,
            model=resolved_model,
            temperature=resolved_temperature,
            context_length=resolved_context_length,
            narrative_context=resolved_narrative_context,
        )
        assistant_message = result.get("assistant_message", "")
        parsed_assessment = self._extract_first_json_object(assistant_message)
        model_assessment = self._normalize_prethinker_assessment(parsed_assessment)
        validation_errors = self._validate_prethinker_assessment(model_assessment)
        assessment_valid = len(validation_errors) == 0
        baseline_assessment = self._build_baseline_prethink_assessment(utterance)
        fallback_used = not assessment_valid
        final_assessment = model_assessment if assessment_valid else baseline_assessment
        agreement_with_baseline = self._assessment_agreement(
            baseline_assessment,
            model_assessment,
        )
        model_kb_projection = self._project_write_path(
            text=utterance,
            assessment=model_assessment,
        )
        baseline_kb_projection = self._project_write_path(
            text=utterance,
            assessment=baseline_assessment,
        )
        kb_projection = model_kb_projection if assessment_valid else baseline_kb_projection
        return {
            "status": "success",
            "result_type": "prethink_assessment",
            "text": utterance,
            "narrative_context": resolved_narrative_context,
            "prethinker_model": resolved_model,
            "prethinker_base_url": self._get_prethinker_base_url(),
            "temperature": resolved_temperature,
            "context_length": resolved_context_length,
            "assistant_message": assistant_message,
            "assessment": final_assessment,
            "model_assessment": model_assessment,
            "baseline_assessment": baseline_assessment,
            "assessment_valid": assessment_valid,
            "assessment_source": "model" if assessment_valid else "baseline_fallback",
            "fallback_used": fallback_used,
            "validation_errors": validation_errors,
            "agreement_with_baseline": agreement_with_baseline,
            "kb_projection": kb_projection,
            "model_kb_projection": model_kb_projection,
            "baseline_kb_projection": baseline_kb_projection,
            "raw_response": result.get("raw_response", {}),
            "note": (
                "This tool forwards utterance text (plus optional narrative context) "
                "to the pre-thinker model, validates structured assessment output, and "
                "falls back to deterministic baseline assessment when model output is invalid. "
                "It also reports deterministic write-path projection (`can_write_now`) and "
                "performs no KB mutation."
            ),
        }

    def prethink_batch(
        self,
        items: Any,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        context_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run pre-thinker assessment across multiple utterances."""
        if not isinstance(items, list):
            return {
                "status": "validation_error",
                "message": "Missing required field: items (array).",
                "tool": "prethink_batch",
            }

        results: List[Dict[str, Any]] = []
        for index, item in enumerate(items):
            if isinstance(item, dict):
                text = item.get("text", "")
                narrative_context = item.get("narrative_context")
            elif isinstance(item, str):
                text = item
                narrative_context = None
            else:
                text = ""
                narrative_context = None

            assessment = self.prethink_utterance(
                text=text,
                narrative_context=narrative_context,
                model=model,
                temperature=temperature,
                context_length=context_length,
            )
            results.append(
                {
                    "index": index,
                    "input": item,
                    "result": assessment,
                }
            )

        processed_count = len(results)
        success_count = sum(
            1
            for row in results
            if isinstance(row.get("result"), dict) and row["result"].get("status") == "success"
        )
        assessment_valid_count = sum(
            1
            for row in results
            if isinstance(row.get("result"), dict) and row["result"].get("assessment_valid") is True
        )
        fallback_count = sum(
            1
            for row in results
            if isinstance(row.get("result"), dict) and row["result"].get("fallback_used") is True
        )
        write_candidate_count = sum(
            1
            for row in results
            if (
                isinstance(row.get("result"), dict)
                and isinstance(row["result"].get("kb_projection"), dict)
                and row["result"]["kb_projection"].get("should_attempt_write") is True
            )
        )
        write_ready_count = sum(
            1
            for row in results
            if (
                isinstance(row.get("result"), dict)
                and isinstance(row["result"].get("kb_projection"), dict)
                and row["result"]["kb_projection"].get("can_write_now") is True
            )
        )

        return {
            "status": "success",
            "result_type": "prethink_batch",
            "requested_count": len(items),
            "processed_count": processed_count,
            "success_count": success_count,
            "assessment_valid_count": assessment_valid_count,
            "fallback_count": fallback_count,
            "write_candidate_count": write_candidate_count,
            "write_ready_count": write_ready_count,
            "items": results,
            "note": (
                "Batch pre-thinker analysis with deterministic write-path projection. "
                "No KB mutation performed."
            ),
        }

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

    def reset_kb(self) -> Dict[str, Any]:
        """Reset in-memory runtime assertions by recreating the baseline skill."""
        self.skill = SemanticPrologSkill(kb_path=str(self.kb_path))
        return {
            "status": "success",
            "result_type": "runtime_reset",
            "message": "Runtime KB reset to baseline seed state.",
            "knowledge_base_path": str(self.kb_path),
        }

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
            "note": "Use reset_kb (baseline restore) or kb_empty (fully empty runtime) to clear runtime changes.",
        }

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

    def assert_rule(self, rule: str) -> Dict[str, Any]:
        """Assert one runtime rule into the current in-memory KB."""
        normalized = (rule or "").strip()
        if not normalized:
            return {
                "status": "validation_error",
                "message": "No rule provided.",
                "rule": rule,
            }
        if not normalized.endswith("."):
            normalized = normalized + "."

        added = self.skill.prolog_skill.add_rule(normalized)
        if not added:
            return {
                "status": "validation_error",
                "message": "Rule assertion failed. Ensure this is a valid rule with ':-' and non-empty body.",
                "rule": normalized,
            }

        if hasattr(self.skill, "validator"):
            self.skill.validator.kb_entities.update(self._extract_entities_from_fact(normalized))

        return {
            "status": "success",
            "result_type": "rule_asserted",
            "rule": normalized,
            "message": "Rule asserted into runtime KB for this server process.",
            "note": "Use reset_kb (baseline restore) or kb_empty (fully empty runtime) to clear runtime changes.",
        }

    def kb_empty(self) -> Dict[str, Any]:
        """Clear all runtime facts/rules from the in-memory KB."""
        engine = getattr(self.skill.prolog_skill, "engine", None)
        if engine is not None and hasattr(engine, "clauses"):
            engine.clauses.clear()

        validator = getattr(self.skill, "validator", None)
        if validator is not None and hasattr(validator, "kb_entities"):
            validator.kb_entities.clear()

        failure_translator = getattr(self.skill, "failure_translator", None)
        if failure_translator is not None and hasattr(failure_translator, "kb_entities"):
            failure_translator.kb_entities.clear()

        return {
            "status": "success",
            "result_type": "runtime_emptied",
            "message": "Runtime KB cleared to empty state.",
            "knowledge_base_path": str(self.kb_path),
            "remaining_clause_count": 0,
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
            "Run 'query_logic' or 'query_rows' with a simpler predicate first"
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
                "The query is ambiguous or malformed for deterministic Prolog parsing."
            )
            suggestions = [
                "Use a single Prolog predicate with explicit arguments",
                "Check punctuation and variable names",
                "Example: 'parent(john, X).' or 'ancestor(alice, bob).'"
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
        control_plane_policy = getattr(
            self,
            "control_plane_policy",
            dict(self.DEFAULT_CONTROL_PLANE_POLICY),
        )
        expose_legacy_prethink_tools = self._should_expose_legacy_prethink_tools()
        capabilities = [
            "Literal Prolog query execution (`query_logic`, `query_rows`)",
            "Statement classification before query or ingestion decisions",
            "Pre-think utterance preprocessing (`pre_think`)",
            "Optional pre-think candidate fact ingestion (`pre_think` with `kb_ingest_mode=facts`)",
            "Deterministic pre-thinker write-path projection (`kb_projection.can_write_now`)",
            "Deterministic knowledge-base reasoning",
            "Runtime fact/rule assertion, retraction, and empty-reset for chat-driven scenarios",
            "Deterministic query and write-path validation",
            "Friendly failure explanations with suggestions",
            "Proof-trace generation",
            "Pre-think state introspection (`show_pre_think_state`)",
        ]
        if expose_legacy_prethink_tools:
            capabilities.append("Pre-thinker utterance forwarding (`prethink_utterance`)")
            capabilities.append("Pre-thinker batch analysis (`prethink_batch`)")
        else:
            capabilities.append(
                "Legacy pre-thinker diagnostic tools are hidden from default tool discovery (`prethink_utterance`, `prethink_batch`)"
            )
        return {
            "status": "success",
            "system": "Prolog Reasoning",
            "version": "0.5",
            "description": (
                "A local-first neuro-symbolic reliability layer for LLM agents. "
                "Deterministic symbolic reasoning decides truth."
            ),
            "knowledge_base_path": str(self.kb_path),
            "core_idea": "Memories are timestamped. Facts are not.",
            "control_plane_policy": {
                "clarification_eagerness": control_plane_policy.get("clarification_eagerness", 0.0),
                "status": "no-op placeholder for future routing policy",
                "note": (
                    "This key is reserved for future clarification policy tuning. "
                    "Current write behavior is unchanged."
                ),
            },
            "capabilities": capabilities,
            "supported_domains": [
                "Family relationships (parent, sibling, ancestor)",
                "Access control (permissions, roles, users)",
                "Clinical medication triage (deterministic risk flags)",
                "Project dependency risk analysis (CPM-like milestone impact)",
                "General knowledge representations"
            ],
            "example_queries": [
                "parent(john, X).",
                "ancestor(alice, bob).",
                "allowed(admin, read).",
                "allergic_to(bob, Substance)."
            ],
            "learn_more": {
                "getting_started": "See training/01-llm-memory-magic.md",
                "kb_design": "See training/02-knowledge-bases-101.md",
                "error_handling": "See training/03-learning-from-failures.md",
                "lm_studio": "See docs/lm-studio-mcp-guide.md",
                "github": "https://github.com/dr3d/prolog-reasoning"
            }
        }

    def show_pre_think_state(
        self,
        include_history: Any = True,
        history_items: Any = 5,
    ) -> Dict[str, Any]:
        """Inspect pre-think configuration and recent history state."""
        include_history_flag = self._coerce_bool(include_history, fallback=True)
        history_items_count = self._coerce_positive_int(history_items, fallback=5)
        history = self._get_pre_think_history()
        skill_text = self._get_pre_think_skill_text()
        history_path = self._get_pre_think_history_path()
        history_file = self._resolve_repo_relative_path(history_path) if history_path else None
        recent_history: List[Dict[str, Any]] = []

        if include_history_flag and history:
            for row in history[-history_items_count:]:
                input_utterance = str(row.get("input_utterance", "")).strip()
                processed_utterance = str(row.get("processed_utterance", "")).strip()
                recent_history.append(
                    {
                        "input_utterance": input_utterance,
                        "processed_utterance": processed_utterance,
                    }
                )

        return {
            "status": "success",
            "result_type": "pre_think_state",
            "pre_think_model": self._get_pre_think_model(),
            "prethinker_base_url": self._get_prethinker_base_url(),
            "pre_think_skill_path": self._get_pre_think_skill_path(),
            "pre_think_skill_loaded": bool(skill_text),
            "pre_think_skill_chars": len(skill_text),
            "prethinker_api_key_configured": bool(self._get_prethinker_api_key()),
            "pre_think_history_path": history_path,
            "pre_think_history_file_exists": bool(history_file and history_file.exists()),
            "history_turns": len(history),
            "max_history_turns": self._get_pre_think_max_history_turns(),
            "recent_history": recent_history,
            "note": (
                "Pre-think state view for debugging. History is kept in memory and mirrored to disk when "
                "PRE_THINK_HISTORY_PATH is configured."
            ),
        }
    
    def handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool calls to appropriate handler."""
        handlers = {
            "query_logic": lambda: self.query_logic(tool_input.get("query", "")),
            "query_rows": lambda: self.query_rows(tool_input.get("query", "")),
            "assert_fact": lambda: self.assert_fact(tool_input.get("fact", "")),
            "bulk_assert_facts": lambda: self.bulk_assert_facts(tool_input.get("facts", [])),
            "retract_fact": lambda: self.retract_fact(tool_input.get("fact", "")),
            "assert_rule": lambda: self.assert_rule(tool_input.get("rule", "")),
            "reset_kb": lambda: self.reset_kb(),
            "kb_empty": lambda: self.kb_empty(),
            "classify_statement": lambda: self.classify_statement(tool_input.get("text", "")),
            "pre_think": lambda: self.pre_think(
                tool_input.get("utterance", "") or tool_input.get("text", ""),
                narrative_context=tool_input.get("narrative_context"),
                model=tool_input.get("model"),
                temperature=tool_input.get("temperature"),
                context_length=tool_input.get("context_length"),
                handoff_mode=tool_input.get("handoff_mode"),
                kb_ingest_mode=tool_input.get("kb_ingest_mode"),
                max_candidate_facts=tool_input.get("max_candidate_facts"),
            ),
            "prethink_utterance": lambda: self.prethink_utterance(
                tool_input.get("text", ""),
                narrative_context=tool_input.get("narrative_context"),
                model=tool_input.get("model"),
                temperature=tool_input.get("temperature"),
                context_length=tool_input.get("context_length"),
            ),
            "prethink_batch": lambda: self.prethink_batch(
                tool_input.get("items"),
                model=tool_input.get("model"),
                temperature=tool_input.get("temperature"),
                context_length=tool_input.get("context_length"),
            ),
            "list_known_facts": lambda: self.list_known_facts(),
            "explain_error": lambda: self.explain_error(tool_input.get("error_message", "")),
            "show_system_info": lambda: self.show_system_info(),
            "show_pre_think_state": lambda: self.show_pre_think_state(
                include_history=tool_input.get("include_history", True),
                history_items=tool_input.get("history_items", 5),
            ),
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
        # `no_results` is a valid deterministic outcome for many queries
        # (for example, no delayed milestones in a healthy baseline).
        # Keep MCP `isError` for genuine execution/validation failures only.
        is_error = sanitized.get("status") in {"error", "validation_error"}
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
                        "Use query_logic/query_rows for deterministic Prolog-native access to "
                        "the knowledge base. Use list_known_facts first if you need to inspect "
                        "available entities and predicate vocabulary."
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
        print('  query_logic({"query": "parent(john, X)."})')
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
                    print("  logic <prolog query>      - Query with literal Prolog")
                    print("  list                     - Show known facts")
                    print("  info                     - System information")
                    print("  help                     - Show this help")
                    print("  quit                     - Exit")
                    print()
                elif user_input.lower().startswith("logic "):
                    query = user_input[6:].strip()
                    result = server.query_logic(query)
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
