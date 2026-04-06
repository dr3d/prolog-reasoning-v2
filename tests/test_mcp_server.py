"""
Focused tests for the MCP server wrapper.

These tests cover the behavior LM Studio depends on:
- MCP initialize handshake
- tools/call response wrapping
- JSON-safe formatting
- response shaping for query/list/error tools
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from engine.core import Term
from mcp_server import PrologMCPServer
from parser.statement_classifier import StatementClassifier


class DummyValidator:
    def __init__(self, entities=None):
        self.kb_entities = entities or {"john", "alice", "bob", "admin", "read", "write"}


class DummySkill:
    def __init__(self, response, entities=None):
        self._response = response
        self.validator = DummyValidator(entities)

    def query_nl(self, query):
        return {**self._response, "nl_query": query}


def make_server(skill=None):
    server = PrologMCPServer.__new__(PrologMCPServer)
    server.kb_path = Path("D:/repo/prolog/core.pl")
    server.skill = skill or DummySkill({})
    server.statement_classifier = StatementClassifier()
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

    def test_tools_list_includes_classify_statement(self):
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

    def test_list_known_facts_returns_entities_and_supported_predicates(self):
        server = make_server(DummySkill({}, {"john", "alice"}))

        result = server.list_known_facts()

        assert result["status"] == "success"
        assert result["known_entities"] == ["alice", "john"]
        assert "supported_predicates" in result
        assert "known_relationships" not in result
        assert "supported predicate" in result["note"]

    def test_classify_statement_detects_query(self):
        server = make_server()

        result = server.classify_statement("Who is John's parent?")

        assert result["status"] == "success"
        assert result["kind"] == "query"
        assert result["can_query_now"] is True
        assert result["suggested_operation"] == "query"

    def test_classify_statement_detects_first_person_candidate_fact(self):
        server = make_server()

        result = server.classify_statement("My mother was Ann.")

        assert result["kind"] == "hard_fact"
        assert result["needs_speaker_resolution"] is True
        assert result["can_persist_now"] is False
        assert result["suggested_operation"] == "store_fact"

    def test_classify_statement_detects_correction(self):
        server = make_server()

        result = server.classify_statement("Actually, I meant Alice.")

        assert result["kind"] == "correction"
        assert result["suggested_operation"] == "revise_memory"

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

    def test_query_prolog_shapes_success_response(self):
        parsed_ir = json.dumps({"predicate": "parent", "args": ["john", "X"]})
        skill = DummySkill(
            {
                "success": True,
                "explanation": "SUCCESS: Query 'parent(john, X)' succeeded with 1 solution(s).\n  Bindings: X: alice",
                "proof_trace": [],
                "bindings": {"X": "alice"},
                "num_solutions": 1,
                "validation_confidence": 1.0,
                "parsing_confidence": 0.9,
                "domain": "family",
                "parsed_ir": parsed_ir,
            }
        )
        server = make_server(skill)

        result = server.query_prolog("Who is John's parent?")

        assert result["status"] == "success"
        assert result["result_type"] == "success"
        assert result["predicate"] == "parent"
        assert result["reasoning_basis"]["kind"] == "fact-backed"
        assert result["metadata"]["bindings"] == {"X": "alice"}

    def test_query_prolog_shapes_validation_error_response(self):
        parsed_ir = json.dumps({"predicate": "parent", "args": ["charlie", "X"]})
        skill = DummySkill(
            {
                "success": False,
                "validation_errors": [
                    {"type": "undefined_entity", "message": "Entity 'charlie' not in KB"}
                ],
                "validation_confidence": 0.1,
                "parsing_confidence": 0.8,
                "domain": "family",
                "parsed_ir": parsed_ir,
            }
        )
        server = make_server(skill)

        result = server.query_prolog("Who is Charlie's parent?")

        assert result["status"] == "validation_error"
        assert result["result_type"] == "validation_error"
        assert result["error_types"] == ["undefined_entity"]
        assert result["predicate"] == "parent"

    def test_query_prolog_shapes_no_result_response(self):
        parsed_ir = json.dumps({"predicate": "ancestor", "args": ["alice", "nobody"]})
        skill = DummySkill(
            {
                "success": False,
                "why_it_failed": "No ancestor relationship was found.",
                "what_to_try": "Ask about a known descendant.",
                "failure_explanation": "No matching derived fact was found.",
                "validation_confidence": 1.0,
                "parsing_confidence": 0.85,
                "domain": "family",
                "parsed_ir": parsed_ir,
            }
        )
        server = make_server(skill)

        result = server.query_prolog("Is Alice an ancestor of nobody?")

        assert result["status"] == "no_results"
        assert result["result_type"] == "no_result"
        assert result["predicate"] == "ancestor"
        assert result["reasoning_basis"]["kind"] == "rule-derived"
