"""
Focused tests for the MCP server wrapper.

These tests cover the behavior LM Studio depends on:
- MCP initialize handshake
- tools/call response wrapping
- JSON-safe formatting
- response shaping for query/list/error tools
"""

import io
import json
import os
import sys
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "src")

from engine.core import Term
from mcp_server import PrologMCPServer
from parser.statement_classifier import StatementClassifier


class DummyValidator:
    def __init__(self, entities=None):
        self.kb_entities = entities or {"john", "alice", "bob", "admin", "read", "write"}


class DummyRawPrologSkill:
    def __init__(self, response, add_fact_result=True, retract_fact_result=True, add_rule_result=True):
        self._response = response
        self._add_fact_result = add_fact_result
        self._retract_fact_result = retract_fact_result
        self._add_rule_result = add_rule_result

    def query(self, query):
        return {**self._response, "query": query}

    def add_fact(self, fact):
        return self._add_fact_result

    def retract_fact(self, fact):
        return self._retract_fact_result

    def add_rule(self, rule):
        return self._add_rule_result


class DummySkill:
    def __init__(
        self,
        response,
        entities=None,
        raw_response=None,
        add_fact_result=True,
        retract_fact_result=True,
        add_rule_result=True,
    ):
        self._response = response
        self.validator = DummyValidator(entities)
        self.prolog_skill = DummyRawPrologSkill(
            raw_response if raw_response is not None else response,
            add_fact_result=add_fact_result,
            retract_fact_result=retract_fact_result,
            add_rule_result=add_rule_result,
        )

    def query_nl(self, query):
        return {**self._response, "nl_query": query}


def make_server(skill=None):
    server = PrologMCPServer.__new__(PrologMCPServer)
    server.kb_path = Path("D:/repo/prolog/core.pl")
    server.skill = skill or DummySkill({})
    server.statement_classifier = StatementClassifier()
    server.expose_legacy_prethink_tools = False
    server._request_id = 0
    return server


class TestMCPServer:
    def test_initialize_negotiates_protocol_and_tools_capability(self):
        server = make_server()

        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                    "capabilities": {},
                },
            }
        )

        assert response["id"] == 1
        assert response["result"]["protocolVersion"] == "2025-03-26"
        assert response["result"]["capabilities"]["tools"]["listChanged"] is False
        assert response["result"]["serverInfo"]["name"] == "prolog-reasoning"

    def test_tools_list_exposes_only_canonical_surface(self):
        server = make_server()

        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
        )

        tool_names = [tool["name"] for tool in response["result"]["tools"]]
        assert "classify_statement" in tool_names
        assert "query_logic" in tool_names
        assert "query_rows" in tool_names
        assert "assert_fact" in tool_names
        assert "bulk_assert_facts" in tool_names
        assert "retract_fact" in tool_names
        assert "assert_rule" in tool_names
        assert "reset_kb" in tool_names
        assert "empty_kb" in tool_names
        assert "pre_think" in tool_names
        assert "prethink_utterance" not in tool_names
        assert "prethink_batch" not in tool_names
        assert "show_pre_think_state" in tool_names
        assert "query_prolog" not in tool_names
        assert "query_prolog_raw" not in tool_names
        assert "query_prolog_rows_raw" not in tool_names
        assert "assert_fact_raw" not in tool_names
        assert "bulk_assert_facts_raw" not in tool_names
        assert "retract_fact_raw" not in tool_names
        assert "reset_runtime_kb" not in tool_names

    def test_tools_list_includes_legacy_prethink_surface_when_enabled(self):
        server = make_server()
        server.expose_legacy_prethink_tools = True

        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
        )

        tool_names = [tool["name"] for tool in response["result"]["tools"]]
        assert "pre_think" in tool_names
        assert "prethink_utterance" in tool_names
        assert "prethink_batch" in tool_names

    def test_tools_call_rejects_removed_tool_name(self):
        server = make_server()

        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "query_prolog", "arguments": {"query": "parent(john, X)."}},
            }
        )
        result = response["result"]["structuredContent"]
        assert result["status"] == "error"
        assert "Unknown tool: query_prolog" in result["error"]

    def test_tools_call_wraps_result_and_makes_it_json_safe(self):
        server = make_server()

        wrapped = server._format_tool_result(
            {
                "status": "success",
                "payload": {"value": Term("alice")},
            }
        )

        assert wrapped["isError"] is False
        assert wrapped["structuredContent"]["payload"]["value"] == "alice"
        assert "\"value\": \"alice\"" in wrapped["content"][0]["text"]

    def test_tools_call_no_results_is_not_marked_error(self):
        server = make_server()

        wrapped = server._format_tool_result(
            {
                "status": "no_results",
                "result_type": "no_result",
                "rows": [],
                "num_rows": 0,
            }
        )

        assert wrapped["isError"] is False
        assert wrapped["structuredContent"]["status"] == "no_results"

    def test_list_known_facts_returns_entities_and_supported_predicates(self):
        server = make_server(DummySkill({}, {"john", "alice"}))

        result = server.list_known_facts()

        assert result["status"] == "success"
        assert result["known_entities"] == ["alice", "john"]
        assert "supported_predicates" in result
        assert "known_relationships" not in result
        assert "supported predicate" in result["note"]

    def test_show_system_info_exposes_noop_clarification_policy_key(self):
        server = make_server()

        result = server.show_system_info()

        assert result["status"] == "success"
        assert "control_plane_policy" in result
        assert result["control_plane_policy"]["clarification_eagerness"] == 0.0
        assert result["control_plane_policy"]["status"] == "no-op placeholder for future routing policy"
        capabilities_text = "\n".join(result["capabilities"])
        assert "pre_think" in capabilities_text
        assert "prethink_utterance" in capabilities_text

    def test_show_pre_think_state_exposes_model_skill_and_history(self):
        server = make_server()
        server.pre_think_model = "qwen/qwen3.5-9b"
        server.pre_think_skill_path = "skills/pre-think/SKILL.md"
        server.pre_think_skill_text = "custom pre-think policy"
        server.pre_think_history_path = ".tmp_pre_think_history.json"
        server.pre_think_history = [
            {"input_utterance": "Maybe my mother was Ann.", "processed_utterance": "Tentative candidate..."},
            {"input_utterance": "Actually not Bob, I meant Alice.", "processed_utterance": "Correction candidate..."},
        ]
        server.pre_think_max_history_turns = 6
        server.prethinker_base_url = "http://127.0.0.1:1234"
        server.prethinker_api_key = "sk-lm-xxxxx"

        result = server.show_pre_think_state(include_history=True, history_items=1)

        assert result["status"] == "success"
        assert result["result_type"] == "pre_think_state"
        assert result["pre_think_model"] == "qwen/qwen3.5-9b"
        assert result["pre_think_skill_loaded"] is True
        assert result["prethinker_api_key_configured"] is True
        assert "pre_think_history_path" in result
        assert result["history_turns"] == 2
        assert len(result["recent_history"]) == 1

    def test_pre_think_history_persists_to_disk_and_reloads(self):
        server = make_server()
        history_path = Path("tests/.tmp_pre_think_history_test.json").resolve()
        if history_path.exists():
            history_path.unlink()

        try:
            server.pre_think_history_path = str(history_path)
            server.pre_think_max_history_turns = 2
            server.pre_think_history = []

            server._record_pre_think_turn(
                input_utterance="first input",
                processed_utterance="first output",
            )
            server._record_pre_think_turn(
                input_utterance="second input",
                processed_utterance="second output",
            )
            server._record_pre_think_turn(
                input_utterance="third input",
                processed_utterance="third output",
            )

            assert history_path.exists()
            payload = json.loads(history_path.read_text(encoding="utf-8"))
            assert isinstance(payload, list)
            assert len(payload) == 2
            assert payload[0]["input_utterance"] == "second input"
            assert payload[1]["input_utterance"] == "third input"

            fresh_server = make_server()
            fresh_server.pre_think_history_path = str(history_path)
            fresh_server.pre_think_max_history_turns = 2
            loaded = fresh_server._load_pre_think_history_from_disk(str(history_path))

            assert len(loaded) == 2
            assert loaded[0]["input_utterance"] == "second input"
            assert loaded[1]["input_utterance"] == "third input"
        finally:
            if history_path.exists():
                history_path.unlink()

    def test_classify_statement_detects_query(self):
        server = make_server()

        result = server.classify_statement("Who is John's parent?")

        assert result["status"] == "success"
        assert result["kind"] == "query"
        assert result["can_query_now"] is True
        assert result["suggested_operation"] == "query"
        assert result["proposal_check"]["status"] == "reject"

    def test_classify_statement_detects_first_person_candidate_fact(self):
        server = make_server()

        result = server.classify_statement("My mother was Ann.")

        assert result["kind"] == "hard_fact"
        assert result["needs_speaker_resolution"] is True
        assert result["can_persist_now"] is False
        assert result["suggested_operation"] == "store_fact"
        assert result["proposal_check"]["status"] == "needs_clarification"
        assert result["proposal_check"]["candidate"]["canonical_predicate"] == "parent"

    def test_classify_statement_detects_correction(self):
        server = make_server()

        result = server.classify_statement("Actually, I meant Alice.")

        assert result["kind"] == "correction"
        assert result["suggested_operation"] == "revise_memory"
        assert result["proposal_check"]["status"] in {"needs_clarification", "reject"}

    def test_classify_statement_includes_valid_proposal_for_prolog_literal(self):
        server = make_server()

        result = server.classify_statement("parent(ann, scott).")

        assert result["status"] == "success"
        assert "proposal_check" in result
        assert result["proposal_check"]["status"] == "valid"
        assert result["proposal_check"]["candidate"]["canonical_predicate"] == "parent"

    def test_prethink_utterance_validation_requires_text(self):
        server = make_server()

        result = server.prethink_utterance("")

        assert result["status"] == "validation_error"
        assert "text" in result["message"].lower()

    def test_pre_think_validation_requires_utterance(self):
        server = make_server()

        result = server.pre_think("")

        assert result["status"] == "validation_error"
        assert "utterance" in result["message"].lower()

    def test_pre_think_processes_utterance_for_downstream_model(self):
        server = make_server()
        captured = {}

        def fake_call_prethink_rewriter(
            *,
            utterance,
            model,
            temperature,
            context_length,
            narrative_context,
            handoff_mode,
            kb_ingest_mode,
        ):
            captured["utterance"] = utterance
            captured["model"] = model
            captured["temperature"] = temperature
            captured["context_length"] = context_length
            captured["narrative_context"] = narrative_context
            captured["handoff_mode"] = handoff_mode
            captured["kb_ingest_mode"] = kb_ingest_mode
            return {
                "assistant_message": "Please classify this as a tentative fact before any write attempt.",
                "raw_response": {"output": [{"type": "message", "content": "Please classify this as a tentative fact before any write attempt."}]},
            }

        server._call_prethink_rewriter = fake_call_prethink_rewriter
        result = server.pre_think(
            "Maybe my mother was Ann.",
            narrative_context="Speaker identity unresolved.",
            model="qwen3.5-4b",
            temperature=0.1,
            context_length=2048,
        )

        assert result["status"] == "success"
        assert result["result_type"] == "pre_think"
        assert result["input_utterance"] == "Maybe my mother was Ann."
        assert result["processed_utterance"] == "Please classify this as a tentative fact before any write attempt."
        assert result["fallback_used"] is False
        assert result["normalization_reason"] == "model_output"
        assert result["pre_think_skill_path"] == "skills/pre-think/SKILL.md"
        assert captured["utterance"] == "Maybe my mother was Ann."
        assert captured["narrative_context"] == "Speaker identity unresolved."
        assert captured["model"] == "qwen3.5-4b"
        assert captured["temperature"] == 0.1
        assert captured["context_length"] == 2048
        assert captured["handoff_mode"] == "rewrite"
        assert captured["kb_ingest_mode"] == "none"
        assert "kb mutation occurs only" in result["note"].lower()

    def test_build_pre_think_input_includes_skill_guidance(self):
        server = make_server()
        server._get_pre_think_skill_text = lambda: "Use correction-safe phrasing."

        prompt = server._build_pre_think_input(
            utterance="Actually not Bob, I meant Alice.",
            narrative_context="Prior candidate used Bob.",
        )

        assert "Pre-think SKILL guidance:" in prompt
        assert "Use correction-safe phrasing." in prompt
        assert "first shot" in prompt.lower()

    def test_build_pre_think_input_answer_proxy_mode_changes_instructions(self):
        server = make_server()
        server._get_pre_think_skill_text = lambda: "Return direct user-ready text."

        prompt = server._build_pre_think_input_with_mode(
            utterance="Who supervises A-3 at T0?",
            narrative_context="Scenario-2 baseline context.",
            handoff_mode="answer_proxy",
        )

        assert "final user-facing answer text directly" in prompt.lower()
        assert "echo your output verbatim" in prompt.lower()

    def test_build_pre_think_input_includes_candidate_fact_json_contract_when_ingest_enabled(self):
        server = make_server()
        server._get_pre_think_skill_text = lambda: "Extract only high-confidence facts."

        prompt = server._build_pre_think_input_with_mode(
            utterance="A-3 is supervised by P-002 at T0.",
            narrative_context="Scenario context.",
            handoff_mode="rewrite",
            kb_ingest_mode="facts",
        )

        assert "return json only" in prompt.lower()
        assert "candidate_facts" in prompt

    def test_pre_think_falls_back_to_input_when_model_output_empty(self):
        server = make_server()

        def fake_call_prethink_rewriter(
            *,
            utterance,
            model,
            temperature,
            context_length,
            narrative_context,
            handoff_mode,
            kb_ingest_mode,
        ):
            return {
                "assistant_message": "",
                "raw_response": {"output": [{"type": "message", "content": ""}]},
            }

        server._call_prethink_rewriter = fake_call_prethink_rewriter
        result = server.pre_think("Who is John's parent?")

        assert result["status"] == "success"
        assert result["processed_utterance"] == "Who is John's parent?"
        assert result["fallback_used"] is True
        assert result["normalization_reason"] == "empty_model_output"

    def test_pre_think_uses_qwen_9b_default_model(self):
        server = make_server()
        captured = {}

        def fake_call_prethink_rewriter(
            *,
            utterance,
            model,
            temperature,
            context_length,
            narrative_context,
            handoff_mode,
            kb_ingest_mode,
        ):
            captured["model"] = model
            return {
                "assistant_message": "normalized utterance",
                "raw_response": {"output": [{"type": "message", "content": "normalized utterance"}]},
            }

        server._call_prethink_rewriter = fake_call_prethink_rewriter
        result = server.pre_think("Maybe my mother was Ann.")

        assert result["status"] == "success"
        assert captured["model"] == "qwen/qwen3.5-9b"

    def test_pre_think_accepts_answer_proxy_handoff_mode(self):
        server = make_server()
        captured = {}

        def fake_call_prethink_rewriter(
            *,
            utterance,
            model,
            temperature,
            context_length,
            narrative_context,
            handoff_mode,
            kb_ingest_mode,
        ):
            captured["handoff_mode"] = handoff_mode
            return {
                "assistant_message": "P-002 supervises A-3 at T0.",
                "raw_response": {"output": [{"type": "message", "content": "P-002 supervises A-3 at T0."}]},
            }

        server._call_prethink_rewriter = fake_call_prethink_rewriter
        result = server.pre_think(
            "Who supervises A-3 at T0?",
            handoff_mode="answer_proxy",
        )

        assert result["status"] == "success"
        assert result["handoff_mode"] == "answer_proxy"
        assert captured["handoff_mode"] == "answer_proxy"

    def test_pre_think_can_ingest_candidate_facts_when_enabled(self):
        server = make_server()
        ingested = []

        def fake_call_prethink_rewriter(
            *,
            utterance,
            model,
            temperature,
            context_length,
            narrative_context,
            handoff_mode,
            kb_ingest_mode,
        ):
            return {
                "assistant_message": (
                    '{"processed_utterance":"A-3 supervisor at T0 is P-002.",'
                    '"candidate_facts":["parent(john, alice).","role(alice, admin)."]}'
                ),
                "raw_response": {},
            }

        def fake_assert_fact(fact):
            ingested.append(fact)
            if "parent(" in fact:
                return {"status": "success", "fact": fact}
            return {"status": "validation_error", "message": "rejected in test"}

        server._call_prethink_rewriter = fake_call_prethink_rewriter
        server.assert_fact = fake_assert_fact
        result = server.pre_think(
            "Who supervises A-3 at T0?",
            handoff_mode="answer_proxy",
            kb_ingest_mode="facts",
            max_candidate_facts=10,
        )

        assert result["status"] == "success"
        assert result["kb_ingest_mode"] == "facts"
        assert result["requested_candidate_facts"] == 2
        assert result["attempted_candidate_facts"] == 2
        assert result["ingested_facts_count"] == 1
        assert result["rejected_candidate_facts_count"] == 1
        assert len(ingested) == 2

    def test_prethink_utterance_forwards_text_to_prethinker_model(self):
        server = make_server()
        captured = {}

        def fake_call_prethinker(*, text, model, temperature, context_length, narrative_context):
            captured["text"] = text
            captured["model"] = model
            captured["temperature"] = temperature
            captured["context_length"] = context_length
            captured["narrative_context"] = narrative_context
            return {
                "assistant_message": (
                    '{"kind":"tentative_fact","confidence":0.72,"needs_clarification":true,'
                    '"can_persist_now":false,"suggested_operation":"store_tentative",'
                    '"rationale":"Hedged language."}'
                ),
                "raw_response": {
                    "output": [
                        {
                            "type": "message",
                            "content": (
                                '{"kind":"tentative_fact","confidence":0.72,"needs_clarification":true,'
                                '"can_persist_now":false,"suggested_operation":"store_tentative",'
                                '"rationale":"Hedged language."}'
                            ),
                        }
                    ]
                },
            }

        server._call_prethinker = fake_call_prethinker

        result = server.prethink_utterance(
            "My mother was Ann.",
            narrative_context="Speaker identity unresolved.",
            model="qwen3.5-4b",
            temperature=0.1,
            context_length=2048,
        )

        assert result["status"] == "success"
        assert result["result_type"] == "prethink_assessment"
        assert result["assessment_valid"] is True
        assert result["assessment_source"] == "model"
        assert result["fallback_used"] is False
        assert result["assessment"]["kind"] == "tentative_fact"
        assert result["model_assessment"]["kind"] == "tentative_fact"
        assert "baseline_assessment" in result
        assert "kb_projection" in result
        assert result["kb_projection"]["should_attempt_write"] is True
        assert result["kb_projection"]["can_write_now"] is False
        assert result["agreement_with_baseline"]["kind"] in {True, False}
        assert captured["text"] == "My mother was Ann."
        assert captured["narrative_context"] == "Speaker identity unresolved."
        assert captured["model"] == "qwen3.5-4b"
        assert captured["temperature"] == 0.1
        assert captured["context_length"] == 2048
        assert "no kb mutation" in result["note"].lower()

    def test_prethink_utterance_marks_invalid_json_assessment(self):
        server = make_server()

        def fake_call_prethinker(*, text, model, temperature, context_length, narrative_context):
            return {
                "assistant_message": "Likely tentative_fact; needs clarification.",
                "raw_response": {"output": [{"type": "message", "content": "Likely tentative_fact; needs clarification."}]},
            }

        server._call_prethinker = fake_call_prethinker
        result = server.prethink_utterance("Maybe John is Bob's parent.")

        assert result["status"] == "success"
        assert result["assessment_valid"] is False
        assert result["assessment_source"] == "baseline_fallback"
        assert result["fallback_used"] is True
        assert result["validation_errors"]
        assert result["model_assessment"] == {}
        assert result["assessment"]
        assert "kb_projection" in result
        assert result["kb_projection"]["can_write_now"] is False
        assert result["assessment"]["kind"] in {
            "query",
            "hard_fact",
            "tentative_fact",
            "correction",
            "preference",
            "session_context",
            "instruction",
            "unknown",
        }

    def test_tools_call_routes_prethink_utterance(self):
        server = make_server()

        def fake_call_prethinker(*, text, model, temperature, context_length, narrative_context):
            return {
                "assistant_message": (
                    '{"kind":"query","confidence":0.94,"needs_clarification":false,'
                    '"can_persist_now":false,"suggested_operation":"query","rationale":"Question form."}'
                ),
                "raw_response": {
                    "output": [
                        {
                            "type": "message",
                            "content": (
                                '{"kind":"query","confidence":0.94,"needs_clarification":false,'
                                '"can_persist_now":false,"suggested_operation":"query","rationale":"Question form."}'
                            ),
                        }
                    ]
                },
            }

        server._call_prethinker = fake_call_prethinker
        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 42,
                "method": "tools/call",
                "params": {"name": "prethink_utterance", "arguments": {"text": "Who is John's parent?"}},
            }
        )

        structured = response["result"]["structuredContent"]
        assert structured["status"] == "success"
        assert structured["result_type"] == "prethink_assessment"
        assert structured["assessment_valid"] is True
        assert structured["assessment"]["kind"] == "query"
        assert "kb_projection" in structured

    def test_tools_call_routes_pre_think(self):
        server = make_server()

        def fake_pre_think(
            utterance,
            narrative_context=None,
            model=None,
            temperature=None,
            context_length=None,
            handoff_mode=None,
            kb_ingest_mode=None,
            max_candidate_facts=None,
        ):
            return {
                "status": "success",
                "result_type": "pre_think",
                "input_utterance": utterance,
                "processed_utterance": "clarify speaker identity, then classify",
                "fallback_used": False,
                "normalization_reason": "model_output",
            }

        server.pre_think = fake_pre_think
        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 420,
                "method": "tools/call",
                "params": {"name": "pre_think", "arguments": {"utterance": "Maybe my mother was Ann."}},
            }
        )

        structured = response["result"]["structuredContent"]
        assert structured["status"] == "success"
        assert structured["result_type"] == "pre_think"
        assert structured["input_utterance"] == "Maybe my mother was Ann."
        assert structured["processed_utterance"] == "clarify speaker identity, then classify"

    def test_tools_call_routes_show_pre_think_state(self):
        server = make_server()

        def fake_show_pre_think_state(include_history=True, history_items=5):
            return {
                "status": "success",
                "result_type": "pre_think_state",
                "pre_think_model": "qwen/qwen3.5-9b",
                "history_turns": 3,
                "recent_history": [],
            }

        server.show_pre_think_state = fake_show_pre_think_state
        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 421,
                "method": "tools/call",
                "params": {"name": "show_pre_think_state", "arguments": {"include_history": False}},
            }
        )

        structured = response["result"]["structuredContent"]
        assert structured["status"] == "success"
        assert structured["result_type"] == "pre_think_state"
        assert structured["pre_think_model"] == "qwen/qwen3.5-9b"

    def test_post_json_retries_localhost_401_with_default_key(self):
        server = make_server()
        requests = []

        class DummyResponse:
            def __init__(self, body: bytes):
                self._body = body

            def read(self):
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(request, timeout):
            requests.append(request)
            if len(requests) == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(b'{"error":"unauthorized"}'),
                )
            assert request.headers.get("Authorization") == "Bearer lm-studio"
            return DummyResponse(b'{"status":"ok"}')

        with patch("mcp_server.urllib.request.urlopen", side_effect=fake_urlopen):
            result = server._post_json(
                url="http://127.0.0.1:1234/api/v1/chat",
                payload={"model": "qwen/qwen3.5-9b", "input": "hello"},
                api_key=None,
                timeout_seconds=5,
            )

        assert result["status"] == "ok"
        assert len(requests) == 2
        assert requests[0].headers.get("Authorization") is None

    def test_load_env_file_reads_missing_values_without_overriding_existing(self):
        server = make_server()
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as handle:
            handle.write("LMSTUDIO_API_KEY=from_env_file\n")
            handle.write("PRETHINKER_MODEL=qwen/qwen3.5-9b\n")
            env_path = handle.name

        try:
            with patch.dict("os.environ", {"PRETHINKER_MODEL": "keep_existing"}, clear=False):
                server._load_env_file(env_path)
                assert "LMSTUDIO_API_KEY" in os.environ
                assert os.environ["LMSTUDIO_API_KEY"] == "from_env_file"
                assert os.environ["PRETHINKER_MODEL"] == "keep_existing"
        finally:
            os.remove(env_path)

    def test_prethink_utterance_normalizes_string_booleans_and_aliases(self):
        server = make_server()

        def fake_call_prethinker(*, text, model, temperature, context_length, narrative_context):
            return {
                "assistant_message": (
                    '{"kind":"question","confidence":"0.8","needs_clarification":"false",'
                    '"can_persist_now":"false","suggested_operation":"ask","rationale":"Looks like a query."}'
                ),
                "raw_response": {
                    "output": [
                        {
                            "type": "message",
                            "content": (
                                '{"kind":"question","confidence":"0.8","needs_clarification":"false",'
                                '"can_persist_now":"false","suggested_operation":"ask","rationale":"Looks like a query."}'
                            ),
                        }
                    ]
                },
            }

        server._call_prethinker = fake_call_prethinker
        result = server.prethink_utterance("Who is John's parent?")

        assert result["status"] == "success"
        assert result["assessment_valid"] is True
        assert result["assessment_source"] == "model"
        assert result["assessment"]["kind"] == "query"
        assert result["assessment"]["suggested_operation"] == "query"
        assert result["assessment"]["needs_clarification"] is False
        assert result["assessment"]["can_persist_now"] is False

    def test_prethink_batch_aggregates_results(self):
        server = make_server()

        def fake_prethink_utterance(text, narrative_context=None, model=None, temperature=None, context_length=None):
            return {
                "status": "success",
                "assessment_valid": text.strip().endswith("?"),
                "fallback_used": not text.strip().endswith("?"),
                "assessment": {"kind": "query" if text.strip().endswith("?") else "unknown"},
                "kb_projection": {
                    "should_attempt_write": not text.strip().endswith("?"),
                    "can_write_now": False,
                },
            }

        server.prethink_utterance = fake_prethink_utterance
        result = server.prethink_batch(
            [{"text": "Who is John's parent?"}, {"text": "Blue ideas sleep quickly."}]
        )

        assert result["status"] == "success"
        assert result["result_type"] == "prethink_batch"
        assert result["requested_count"] == 2
        assert result["processed_count"] == 2
        assert result["success_count"] == 2
        assert result["assessment_valid_count"] == 1
        assert result["fallback_count"] == 1
        assert result["write_candidate_count"] == 1
        assert result["write_ready_count"] == 0
        assert len(result["items"]) == 2

    def test_tools_call_routes_prethink_batch(self):
        server = make_server()

        def fake_prethink_batch(items, model=None, temperature=None, context_length=None):
            return {
                "status": "success",
                "result_type": "prethink_batch",
                "requested_count": len(items),
                "processed_count": len(items),
                "success_count": len(items),
                "assessment_valid_count": len(items),
                "fallback_count": 0,
                "write_candidate_count": 0,
                "write_ready_count": 0,
                "items": [{"index": 0, "input": items[0], "result": {"status": "success"}}],
            }

        server.prethink_batch = fake_prethink_batch
        response = server.process_request(
            {
                "jsonrpc": "2.0",
                "id": 43,
                "method": "tools/call",
                "params": {
                    "name": "prethink_batch",
                    "arguments": {"items": [{"text": "Who is John's parent?"}]},
                },
            }
        )

        structured = response["result"]["structuredContent"]
        assert structured["status"] == "success"
        assert structured["result_type"] == "prethink_batch"
        assert structured["requested_count"] == 1

    def test_explain_error_classifies_undefined_entity(self):
        server = make_server()

        result = server.explain_error('Entity "charlie" not in KB')

        assert result["error_type"] == "undefined_entity"
        assert "charlie" in result["explanation"]
        assert any("known entity" in suggestion for suggestion in result["suggestions"])

    def test_explain_error_classifies_unknown_predicate(self):
        server = make_server()

        result = server.explain_error("ungrounded predicate: can_fly")

        assert result["error_type"] == "unknown_predicate"
        assert "predicate" in result["explanation"].lower()
        assert any("supported predicate" in suggestion for suggestion in result["suggestions"])

    def test_query_logic_shapes_success_response(self):
        skill = DummySkill(
            response={},
            raw_response={
                "success": True,
                "explanation": "SUCCESS: Query 'parent(john, X)' succeeded with 1 solution(s).",
                "proof_trace": [],
                "bindings": {"X": "alice"},
                "num_solutions": 1,
                "confidence": 1.0,
            },
        )
        server = make_server(skill)

        result = server.query_logic("parent(john, X).")

        assert result["status"] == "success"
        assert result["result_type"] == "success"
        assert result["predicate"] == "parent"
        assert result["metadata"]["bindings"] == {"X": "alice"}
        assert result["prolog_query"] == "parent(john, X)."

    def test_query_rows_returns_projected_rows(self):
        server = PrologMCPServer(kb_path="prolog/core.pl")
        server.reset_kb()
        server.assert_fact("task(foundation).")
        server.assert_fact("task(structural_frame).")
        server.assert_fact("depends_on(structural_frame, foundation).")

        result = server.query_rows("depends_on(Task, Prereq).")

        assert result["status"] == "success"
        assert result["result_type"] == "table"
        assert result["variables"] == ["Task", "Prereq"]
        assert any(row == {"Task": "structural_frame", "Prereq": "foundation"} for row in result["rows"])

    def test_query_rows_normalizes_bullet_prefix(self):
        server = PrologMCPServer(kb_path="prolog/core.pl")
        server.reset_kb()
        server.assert_fact("task(site_prep).")

        result = server.query_rows("- task(Task).")

        assert result["status"] == "success"
        assert result["result_type"] == "table"
        assert result["prolog_query"] == "task(Task)."
        assert any(row == {"Task": "site_prep"} for row in result["rows"])

    def test_assert_fact_updates_entities(self):
        server = make_server(DummySkill({}, {"john"}))

        result = server.assert_fact("task(foundation).")

        assert result["status"] == "success"
        assert result["result_type"] == "fact_asserted"
        assert "foundation" in server.skill.validator.kb_entities

    def test_bulk_assert_facts_reports_counts(self):
        server = make_server(DummySkill({}, {"john"}))

        result = server.bulk_assert_facts(["task(foundation).", "task(structural_frame)."])

        assert result["status"] == "success"
        assert result["result_type"] == "bulk_fact_assertion"
        assert result["requested_count"] == 2
        assert result["asserted_count"] == 2
        assert result["failed_count"] == 0

    def test_retract_fact_returns_no_result_when_missing(self):
        server = make_server(DummySkill({}, {"john"}, retract_fact_result=False))

        result = server.retract_fact("task(unknown_task).")

        assert result["status"] == "no_results"
        assert result["result_type"] == "no_result"

    def test_reset_kb_rebuilds_skill(self):
        server = PrologMCPServer(kb_path="prolog/core.pl")
        original_skill = server.skill

        result = server.reset_kb()

        assert result["status"] == "success"
        assert result["result_type"] == "runtime_reset"
        assert server.skill is not original_skill

    def test_assert_rule_enables_derived_query(self):
        server = PrologMCPServer(kb_path="prolog/core.pl")
        server.reset_kb()

        rule_result = server.assert_rule(
            "can_enter(Person, server_room) :- employee(Person), security_clearance(Person, 5)."
        )
        assert rule_result["status"] == "success"
        assert rule_result["result_type"] == "rule_asserted"

        server.assert_fact("employee(alice).")
        server.assert_fact("security_clearance(alice, 5).")
        query_result = server.query_logic("can_enter(alice, server_room).")

        assert query_result["status"] == "success"
        assert query_result["result_type"] == "success"

    def test_empty_kb_clears_runtime_and_reset_kb_restores_baseline(self):
        server = PrologMCPServer(kb_path="prolog/core.pl")

        baseline = server.query_rows("parent(X, Y).")
        assert baseline["status"] == "success"
        assert baseline["num_rows"] > 0

        emptied = server.empty_kb()
        assert emptied["status"] == "success"
        assert emptied["result_type"] == "runtime_emptied"
        assert emptied["remaining_clause_count"] == 0

        after_empty = server.query_rows("parent(X, Y).")
        assert after_empty["status"] == "no_results"
        assert after_empty["num_rows"] == 0

        restored = server.reset_kb()
        assert restored["status"] == "success"
        assert restored["result_type"] == "runtime_reset"

        after_reset = server.query_rows("parent(X, Y).")
        assert after_reset["status"] == "success"
        assert after_reset["num_rows"] > 0
