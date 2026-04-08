"""
Focused tests for the MCP server wrapper.

These tests cover the behavior LM Studio depends on:
- MCP initialize handshake
- tools/call response wrapping
- JSON-safe formatting
- response shaping for query/list/error tools
"""

import sys
from pathlib import Path

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
        assert "kb_empty" in tool_names
        assert "query_prolog" not in tool_names
        assert "query_prolog_raw" not in tool_names
        assert "query_prolog_rows_raw" not in tool_names
        assert "assert_fact_raw" not in tool_names
        assert "bulk_assert_facts_raw" not in tool_names
        assert "retract_fact_raw" not in tool_names
        assert "reset_runtime_kb" not in tool_names

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

    def test_kb_empty_clears_runtime_and_reset_kb_restores_baseline(self):
        server = PrologMCPServer(kb_path="prolog/core.pl")

        baseline = server.query_rows("parent(X, Y).")
        assert baseline["status"] == "success"
        assert baseline["num_rows"] > 0

        emptied = server.kb_empty()
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
