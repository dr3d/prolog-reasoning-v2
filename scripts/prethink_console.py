#!/usr/bin/env python3
"""
Pre-think operator console backend.

This starts a local FastAPI app with a small JSON API and serves a static
operator page for pre-think/session experimentation.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    import uvicorn
except ImportError as error:
    raise SystemExit(
        "Missing dependency: install `fastapi` and `uvicorn` to run prethink_console.py."
    ) from error


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mcp_server import PrologMCPServer


DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen3.5-4b"
DEFAULT_INTEGRATION = "mcp/prolog-reasoning"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_CONTEXT_LENGTH = 4000
DEFAULT_TEMPERATURE = 0.0
DEFAULT_UI_PATH = "docs/secondary/prethink-console.html"
DEFAULT_RUN_LOG_PATH = ".tmp_prethink_console_runs.jsonl"
DEFAULT_HISTORY_ITEMS = 6
DEFAULT_SNAPSHOT_ROOT = "docs/research/conversations/prethink-console"


def _utc_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_bool(value: Any, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        return bool(value)
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on", "enabled"}:
        return True
    if lowered in {"0", "false", "no", "off", "disabled"}:
        return False
    return fallback


def _slugify(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text.strip().lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-_") or "snapshot"


def _relative_display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _build_utterance_diff(raw_text: str, processed_text: str) -> Dict[str, Any]:
    raw_lines = raw_text.splitlines() or [raw_text]
    processed_lines = processed_text.splitlines() or [processed_text]
    unified = "\n".join(
        difflib.unified_diff(
            raw_lines,
            processed_lines,
            fromfile="raw_utterance",
            tofile="processed_utterance",
            lineterm="",
        )
    ).strip()
    ratio = difflib.SequenceMatcher(a=raw_text, b=processed_text).ratio()
    return {
        "changed": raw_text != processed_text,
        "similarity_ratio": ratio,
        "unified_diff": unified,
    }


def _json_dumps_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True)


def _snapshot_markdown(snapshot: Dict[str, Any]) -> str:
    label = str(snapshot.get("label") or "prethink-console-snapshot")
    captured_at = str(snapshot.get("captured_at") or _utc_iso())
    notes = str(snapshot.get("notes") or "").strip()
    runtime = snapshot.get("runtime", {})
    kpi = snapshot.get("kpi", {})
    latest_turn = snapshot.get("latest_turn")
    recent_turns = snapshot.get("recent_turns", [])
    state = snapshot.get("pre_think_state", {})

    lines: list[str] = []
    lines.append(f"# Pre-Think Console Snapshot - {label}")
    lines.append("")
    lines.append(f"- Captured at: `{captured_at}`")
    lines.append(f"- Model: `{runtime.get('default_model', 'unknown')}`")
    lines.append(f"- Integration: `{runtime.get('default_integration', 'unknown')}`")
    lines.append(f"- Context length: `{runtime.get('default_context_length', 'unknown')}`")
    lines.append("")
    if notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(notes)
        lines.append("")

    lines.append("## KPI Snapshot")
    lines.append("")
    lines.append(f"- turns_total: `{kpi.get('turns_total')}`")
    lines.append(f"- prethink_calls_total: `{kpi.get('prethink_calls_total')}`")
    lines.append(f"- write_precision_proxy: `{kpi.get('write_precision_proxy')}`")
    lines.append(f"- false_write_proxy_rate: `{kpi.get('false_write_proxy_rate')}`")
    lines.append(f"- cloud_escalation_rate: `{kpi.get('cloud_escalation_rate')}`")
    lines.append(f"- avg_prethink_latency_ms: `{kpi.get('avg_prethink_latency_ms')}`")
    lines.append(f"- avg_main_latency_ms: `{kpi.get('avg_main_latency_ms')}`")
    lines.append(f"- avg_end_to_end_latency_ms: `{kpi.get('avg_end_to_end_latency_ms')}`")
    lines.append("")

    lines.append("## Session State")
    lines.append("")
    lines.append("```json")
    lines.append(_json_dumps_pretty(state))
    lines.append("```")
    lines.append("")

    if latest_turn is not None:
        lines.append("## Latest Turn")
        lines.append("")
        lines.append("```json")
        lines.append(_json_dumps_pretty(latest_turn))
        lines.append("```")
        lines.append("")

    if recent_turns:
        lines.append("## Recent Turns (tail)")
        lines.append("")
        lines.append("```json")
        lines.append(_json_dumps_pretty(recent_turns))
        lines.append("```")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _timeline_step(
    *,
    step: str,
    status: str,
    detail: str = "",
    latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "step": step,
        "status": status,
        "detail": detail,
        "latency_ms": latency_ms,
    }


def _post_json(
    *,
    url: str,
    payload: Dict[str, Any],
    api_key: Optional[str],
    timeout_seconds: int,
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {raw}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Connection error: {error}") from error


def _extract_message_text(response: Dict[str, Any]) -> str:
    items = response.get("output", [])
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
            continue
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
    return "\n\n".join(parts).strip()


class KPITracker:
    """Tracks lightweight KPI proxies for operator runs."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._lock = threading.Lock()
        self._stats: Dict[str, float] = {}
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._stats = {
                "turns_total": 0.0,
                "prethink_calls_total": 0.0,
                "forwarded_to_main_total": 0.0,
                "candidate_facts_attempted_total": 0.0,
                "facts_ingested_total": 0.0,
                "facts_rejected_total": 0.0,
                "prethink_fallback_total": 0.0,
                "prethink_latency_total_ms": 0.0,
                "main_latency_total_ms": 0.0,
                "end_to_end_latency_total_ms": 0.0,
            }

    def _append_log(self, entry: Dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")

    def record_turn(
        self,
        *,
        source: str,
        utterance: str,
        apply_pre_think: bool,
        forwarded_to_main: bool,
        pre_think_result: Optional[Dict[str, Any]],
        pre_think_latency_ms: Optional[float],
        main_latency_ms: Optional[float],
        end_to_end_latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        metadata = metadata or {}
        attempted = 0
        ingested = 0
        rejected = 0
        fallback_used = False
        if isinstance(pre_think_result, dict):
            attempted = _safe_int(pre_think_result.get("attempted_candidate_facts"))
            ingested = _safe_int(pre_think_result.get("ingested_facts_count"))
            rejected = _safe_int(pre_think_result.get("rejected_candidate_facts_count"))
            fallback_used = _coerce_bool(pre_think_result.get("fallback_used"), fallback=False)

        entry = {
            "timestamp": _utc_iso(),
            "source": source,
            "utterance": utterance,
            "apply_pre_think": apply_pre_think,
            "forwarded_to_main": forwarded_to_main,
            "pre_think_latency_ms": pre_think_latency_ms,
            "main_latency_ms": main_latency_ms,
            "end_to_end_latency_ms": end_to_end_latency_ms,
            "attempted_candidate_facts": attempted,
            "ingested_facts_count": ingested,
            "rejected_candidate_facts_count": rejected,
            "prethink_fallback_used": fallback_used,
            "metadata": metadata,
        }

        with self._lock:
            self._stats["turns_total"] += 1.0
            if apply_pre_think:
                self._stats["prethink_calls_total"] += 1.0
            if forwarded_to_main:
                self._stats["forwarded_to_main_total"] += 1.0
            self._stats["candidate_facts_attempted_total"] += float(attempted)
            self._stats["facts_ingested_total"] += float(ingested)
            self._stats["facts_rejected_total"] += float(rejected)
            if fallback_used:
                self._stats["prethink_fallback_total"] += 1.0
            if pre_think_latency_ms is not None:
                self._stats["prethink_latency_total_ms"] += float(pre_think_latency_ms)
            if main_latency_ms is not None:
                self._stats["main_latency_total_ms"] += float(main_latency_ms)
            self._stats["end_to_end_latency_total_ms"] += float(end_to_end_latency_ms)
            try:
                self._append_log(entry)
            except OSError:
                # Logging failure should not break the live console.
                pass

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            turns = int(self._stats["turns_total"])
            prethink_calls = int(self._stats["prethink_calls_total"])
            forwarded = int(self._stats["forwarded_to_main_total"])
            attempted = int(self._stats["candidate_facts_attempted_total"])
            ingested = int(self._stats["facts_ingested_total"])
            rejected = int(self._stats["facts_rejected_total"])
            fallback_total = int(self._stats["prethink_fallback_total"])
            prethink_latency_total_ms = self._stats["prethink_latency_total_ms"]
            main_latency_total_ms = self._stats["main_latency_total_ms"]
            end_to_end_total_ms = self._stats["end_to_end_latency_total_ms"]

        attempted_writes = attempted if attempted > 0 else (ingested + rejected)
        write_precision_proxy = (
            float(ingested) / float(attempted_writes) if attempted_writes > 0 else None
        )
        false_write_proxy_rate = (
            float(rejected) / float(attempted_writes) if attempted_writes > 0 else None
        )
        cloud_escalation_rate = float(forwarded) / float(turns) if turns > 0 else None
        avg_prethink_latency_ms = (
            prethink_latency_total_ms / float(prethink_calls)
            if prethink_calls > 0
            else None
        )
        avg_main_latency_ms = (
            main_latency_total_ms / float(forwarded)
            if forwarded > 0
            else None
        )
        avg_end_to_end_latency_ms = (
            end_to_end_total_ms / float(turns) if turns > 0 else None
        )

        return {
            "turns_total": turns,
            "prethink_calls_total": prethink_calls,
            "forwarded_to_main_total": forwarded,
            "candidate_facts_attempted_total": attempted,
            "facts_ingested_total": ingested,
            "facts_rejected_total": rejected,
            "prethink_fallback_total": fallback_total,
            "write_precision_proxy": write_precision_proxy,
            "false_write_proxy_rate": false_write_proxy_rate,
            "cloud_escalation_rate": cloud_escalation_rate,
            "avg_prethink_latency_ms": avg_prethink_latency_ms,
            "avg_main_latency_ms": avg_main_latency_ms,
            "avg_end_to_end_latency_ms": avg_end_to_end_latency_ms,
            "note": (
                "write_precision_proxy/false_write_proxy_rate are candidate-write proxies "
                "based on attempted, ingested, and rejected candidate facts."
            ),
        }


def _build_runtime_config(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "base_url": args.base_url,
        "default_model": args.model,
        "default_integration": args.integration,
        "default_context_length": int(args.context_length),
        "default_temperature": float(args.temperature),
        "timeout_seconds": int(args.timeout_seconds),
        "run_log_path": args.run_log_path,
        "snapshot_root": args.snapshot_root,
    }


def create_app(args: argparse.Namespace) -> FastAPI:
    ui_path = (REPO_ROOT / args.ui_path).resolve()
    if not ui_path.exists():
        raise SystemExit(f"UI file not found: {ui_path}")

    server = PrologMCPServer(kb_path=args.kb_path)
    server.set_pre_think_session(
        enabled=not args.disable_pre_think,
        handoff_mode=args.pre_think_handoff_mode,
        kb_ingest_mode=args.pre_think_kb_ingest_mode,
    )

    api_key = args.api_key.strip() or os.environ.get("LMSTUDIO_API_KEY", "").strip() or None
    chat_url = f"{args.base_url.rstrip('/')}/api/v1/chat"
    tracker = KPITracker((REPO_ROOT / args.run_log_path).resolve())
    runtime_config = _build_runtime_config(args)
    snapshot_root = (REPO_ROOT / args.snapshot_root).resolve()
    latest_turn_lock = threading.Lock()
    turn_store: Dict[str, Any] = {"latest": None, "recent": []}

    app = FastAPI(title="Pre-Think Console", version="0.1.0")

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(str(ui_path))

    @app.get("/api/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "timestamp": _utc_iso()}

    @app.get("/api/state")
    def state() -> Dict[str, Any]:
        pre_think_state = server.show_pre_think_state(
            include_history=True,
            history_items=max(1, int(args.history_items)),
        )
        return {
            "status": "success",
            "timestamp": _utc_iso(),
            "pre_think_state": pre_think_state,
            "kpi": tracker.snapshot(),
            "runtime": runtime_config,
        }

    @app.post("/api/session")
    def set_session(payload: Dict[str, Any]) -> Dict[str, Any]:
        current_state = server.show_pre_think_state(include_history=False)
        current_session = current_state.get("pre_think_session", {})
        enabled = _coerce_bool(payload.get("enabled"), fallback=bool(current_session.get("enabled", False)))
        handoff_mode = str(
            payload.get("handoff_mode", current_session.get("handoff_mode", "rewrite"))
        )
        kb_ingest_mode = str(
            payload.get("kb_ingest_mode", current_session.get("kb_ingest_mode", "none"))
        )
        result = server.set_pre_think_session(
            enabled=enabled,
            handoff_mode=handoff_mode,
            kb_ingest_mode=kb_ingest_mode,
        )
        return {"status": "success", "result": result, "kpi": tracker.snapshot()}

    @app.post("/api/prethink")
    def run_prethink(payload: Dict[str, Any]) -> Dict[str, Any]:
        utterance = str(payload.get("utterance", "")).strip()
        if not utterance:
            raise HTTPException(status_code=400, detail="`utterance` is required.")

        handoff_mode = payload.get("handoff_mode")
        kb_ingest_mode = payload.get("kb_ingest_mode")
        max_candidate_facts = payload.get("max_candidate_facts")

        pre_start = time.perf_counter()
        try:
            result = server.pre_think(
                utterance=utterance,
                handoff_mode=handoff_mode,
                kb_ingest_mode=kb_ingest_mode,
                max_candidate_facts=max_candidate_facts,
            )
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        pre_latency_ms = (time.perf_counter() - pre_start) * 1000.0
        processed_utterance = str(result.get("processed_utterance", utterance))
        utterance_diff = _build_utterance_diff(utterance, processed_utterance)
        routing_timeline = [
            _timeline_step(step="input_received", status="ok", detail="utterance accepted"),
            _timeline_step(step="pre_think", status="ok", detail="pre_think applied", latency_ms=pre_latency_ms),
            _timeline_step(step="main_model", status="skipped", detail="pre_think only endpoint"),
        ]

        tracker.record_turn(
            source="prethink_only",
            utterance=utterance,
            apply_pre_think=True,
            forwarded_to_main=False,
            pre_think_result=result,
            pre_think_latency_ms=pre_latency_ms,
            main_latency_ms=None,
            end_to_end_latency_ms=pre_latency_ms,
        )
        response_payload = {
            "status": "success",
            "latency_ms": {"pre_think": pre_latency_ms, "end_to_end": pre_latency_ms},
            "routing_timeline": routing_timeline,
            "utterance_diff": utterance_diff,
            "result": result,
            "kpi": tracker.snapshot(),
        }
        with latest_turn_lock:
            snapshot_turn = {
                "endpoint": "prethink",
                "captured_at": _utc_iso(),
                "response": response_payload,
            }
            turn_store["latest"] = snapshot_turn
            turn_store["recent"] = (turn_store["recent"] + [snapshot_turn])[-20:]
        return response_payload

    @app.post("/api/chat_turn")
    def run_chat_turn(payload: Dict[str, Any]) -> Dict[str, Any]:
        utterance = str(payload.get("utterance", "")).strip()
        if not utterance:
            raise HTTPException(status_code=400, detail="`utterance` is required.")

        session_state = server.show_pre_think_state(include_history=False).get("pre_think_session", {})
        session_enabled = bool(session_state.get("enabled", False))
        force_pre_think = _coerce_bool(payload.get("force_pre_think"), fallback=False)
        apply_pre_think = force_pre_think or session_enabled
        forward_to_main = _coerce_bool(payload.get("forward_to_main"), fallback=True)
        forward_directive_to_main = _coerce_bool(
            payload.get("forward_directive_to_main"),
            fallback=False,
        )
        include_raw_main_response = _coerce_bool(payload.get("include_raw_main_response"), fallback=False)
        integration_enabled = _coerce_bool(payload.get("integration_enabled"), fallback=True)

        model = str(payload.get("model", args.model)).strip() or args.model
        integration = str(payload.get("integration", args.integration)).strip()
        context_length = _safe_int(payload.get("context_length"), fallback=int(args.context_length))
        temperature = _safe_float(payload.get("temperature"), fallback=float(args.temperature))
        timeout_seconds = _safe_int(payload.get("timeout_seconds"), fallback=int(args.timeout_seconds))

        start = time.perf_counter()
        pre_latency_ms: Optional[float] = None
        main_latency_ms: Optional[float] = None
        pre_result: Optional[Dict[str, Any]] = None
        main_raw: Optional[Dict[str, Any]] = None
        main_text = ""
        processed_utterance = utterance
        routing_timeline = [
            _timeline_step(step="input_received", status="ok", detail="utterance accepted"),
        ]

        if apply_pre_think:
            handoff_mode = payload.get("handoff_mode")
            kb_ingest_mode = payload.get("kb_ingest_mode")
            max_candidate_facts = payload.get("max_candidate_facts")
            pre_start = time.perf_counter()
            try:
                pre_result = server.pre_think(
                    utterance=utterance,
                    handoff_mode=handoff_mode,
                    kb_ingest_mode=kb_ingest_mode,
                    max_candidate_facts=max_candidate_facts,
                )
            except Exception as error:
                raise HTTPException(status_code=500, detail=f"pre_think failure: {error}") from error
            pre_latency_ms = (time.perf_counter() - pre_start) * 1000.0
            if pre_result.get("status") != "success":
                raise HTTPException(status_code=500, detail={"pre_think_result": pre_result})
            processed_utterance = str(pre_result.get("processed_utterance", utterance))
            session_directive = pre_result.get("session_directive", {})
            routing_timeline.append(
                _timeline_step(
                    step="pre_think",
                    status="ok",
                    detail=f"handoff={pre_result.get('handoff_mode')} ingest={pre_result.get('kb_ingest_mode')}",
                    latency_ms=pre_latency_ms,
                )
            )
            if (
                isinstance(session_directive, dict)
                and session_directive.get("detected")
                and not forward_directive_to_main
            ):
                forward_to_main = False
                routing_timeline.append(
                    _timeline_step(
                        step="directive_gate",
                        status="skipped_forward",
                        detail=f"session directive detected ({session_directive.get('action')})",
                    )
                )
        else:
            routing_timeline.append(
                _timeline_step(step="pre_think", status="skipped", detail="session disabled and no force flag")
            )

        if forward_to_main:
            chat_payload: Dict[str, Any] = {
                "model": model,
                "input": processed_utterance,
                "temperature": temperature,
                "context_length": context_length,
            }
            if integration_enabled and integration:
                chat_payload["integrations"] = [integration]
            main_start = time.perf_counter()
            try:
                main_raw = _post_json(
                    url=chat_url,
                    payload=chat_payload,
                    api_key=api_key,
                    timeout_seconds=timeout_seconds,
                )
            except Exception as error:
                raise HTTPException(status_code=500, detail=f"main model failure: {error}") from error
            main_latency_ms = (time.perf_counter() - main_start) * 1000.0
            main_text = _extract_message_text(main_raw) or "(empty response)"
            routing_timeline.append(
                _timeline_step(
                    step="main_model",
                    status="ok",
                    detail=f"model={model} integration={'on' if integration_enabled else 'off'}",
                    latency_ms=main_latency_ms,
                )
            )
        else:
            routing_timeline.append(
                _timeline_step(step="main_model", status="skipped", detail="forward_to_main disabled")
            )

        end_to_end_ms = (time.perf_counter() - start) * 1000.0
        utterance_diff = _build_utterance_diff(utterance, processed_utterance)
        tracker.record_turn(
            source="chat_turn",
            utterance=utterance,
            apply_pre_think=apply_pre_think,
            forwarded_to_main=forward_to_main,
            pre_think_result=pre_result,
            pre_think_latency_ms=pre_latency_ms,
            main_latency_ms=main_latency_ms,
            end_to_end_latency_ms=end_to_end_ms,
            metadata={
                "model": model,
                "integration": integration if integration_enabled else "(disabled)",
            },
        )

        result: Dict[str, Any] = {
            "status": "success",
            "apply_pre_think": apply_pre_think,
            "forwarded_to_main": forward_to_main,
            "utterance": utterance,
            "processed_utterance": processed_utterance,
            "main_model_response": main_text,
            "routing_timeline": routing_timeline,
            "utterance_diff": utterance_diff,
            "latency_ms": {
                "pre_think": pre_latency_ms,
                "main_model": main_latency_ms,
                "end_to_end": end_to_end_ms,
            },
            "kpi": tracker.snapshot(),
        }
        if pre_result is not None:
            result["pre_think_result"] = pre_result
        if include_raw_main_response and main_raw is not None:
            result["main_model_raw"] = main_raw
        with latest_turn_lock:
            snapshot_turn = {
                "endpoint": "chat_turn",
                "captured_at": _utc_iso(),
                "response": result,
            }
            turn_store["latest"] = snapshot_turn
            turn_store["recent"] = (turn_store["recent"] + [snapshot_turn])[-20:]
        return result

    @app.post("/api/query")
    def query_rows(payload: Dict[str, Any]) -> Dict[str, Any]:
        query = str(payload.get("query", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="`query` is required.")
        try:
            result = server.query_rows(query)
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        return {"status": "success", "result": result}

    @app.post("/api/kb/reset")
    def reset_kb(_: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = server.reset_kb()
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        return {"status": "success", "result": result}

    @app.post("/api/kb/empty")
    def empty_kb(_: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = server.empty_kb()
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        return {"status": "success", "result": result}

    @app.post("/api/kpi/reset")
    def reset_kpi(_: Dict[str, Any]) -> Dict[str, Any]:
        tracker.reset()
        return {"status": "success", "kpi": tracker.snapshot()}

    @app.post("/api/snapshot/save")
    def save_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
        label = str(payload.get("label", "")).strip() or "run-snapshot"
        notes = str(payload.get("notes", "")).strip()
        include_state_history = _coerce_bool(payload.get("include_state_history"), fallback=True)
        history_items = _safe_int(payload.get("history_items"), fallback=int(args.history_items))
        captured_at = _utc_iso()

        with latest_turn_lock:
            latest_turn = turn_store.get("latest")
            recent_tail = list(turn_store.get("recent", []))[-10:]

        external_latest_turn = payload.get("latest_turn")
        if isinstance(external_latest_turn, dict):
            latest_turn = external_latest_turn

        pre_think_state = server.show_pre_think_state(
            include_history=include_state_history,
            history_items=max(1, history_items),
        )
        snapshot_payload: Dict[str, Any] = {
            "captured_at": captured_at,
            "label": label,
            "notes": notes,
            "runtime": runtime_config,
            "kpi": tracker.snapshot(),
            "pre_think_state": pre_think_state,
            "latest_turn": latest_turn,
            "recent_turns": recent_tail,
        }

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        slug = _slugify(label)
        out_dir = (snapshot_root / f"{stamp}-{slug}").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        json_path = out_dir / "snapshot.json"
        md_path = out_dir / "snapshot.md"
        json_path.write_text(_json_dumps_pretty(snapshot_payload) + "\n", encoding="utf-8")
        md_path.write_text(_snapshot_markdown(snapshot_payload), encoding="utf-8")

        return {
            "status": "success",
            "snapshot": {
                "captured_at": captured_at,
                "label": label,
                "output_dir": _relative_display_path(out_dir),
                "json_path": _relative_display_path(json_path),
                "markdown_path": _relative_display_path(md_path),
            },
        }

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-think operator console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Default main model id")
    parser.add_argument("--integration", default=DEFAULT_INTEGRATION, help="Default integration id")
    parser.add_argument("--kb-path", default="prolog/core.pl", help="Baseline KB path")
    parser.add_argument("--api-key", default="", help="Optional LM Studio API key override")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--ui-path", default=DEFAULT_UI_PATH, help="Path to static HTML UI")
    parser.add_argument(
        "--run-log-path",
        default=DEFAULT_RUN_LOG_PATH,
        help="JSONL log path for turn-level audit records",
    )
    parser.add_argument(
        "--snapshot-root",
        default=DEFAULT_SNAPSHOT_ROOT,
        help="Directory root for saved run snapshots",
    )
    parser.add_argument(
        "--history-items",
        type=int,
        default=DEFAULT_HISTORY_ITEMS,
        help="Number of recent pre-think history entries returned by /api/state",
    )
    parser.add_argument(
        "--pre-think-handoff-mode",
        default="rewrite",
        choices=["rewrite", "answer_proxy"],
    )
    parser.add_argument(
        "--pre-think-kb-ingest-mode",
        default="none",
        choices=["none", "facts"],
    )
    parser.add_argument(
        "--disable-pre-think",
        action="store_true",
        help="Start with session-level pre-think disabled",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app(args)
    uvicorn.run(app, host=args.host, port=int(args.port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
