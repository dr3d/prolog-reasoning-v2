"""
Tests for agent_skill.PrologSkill domain behavior.
"""

import sys

sys.path.insert(0, "src")

from agent_skill import PrologSkill


class TestAgentSkillClinicalTriage:
    def test_contraindicated_candidate_query_succeeds(self):
        skill = PrologSkill()
        result = skill.query("triage(alice, amoxicillin, Status, Reason).")

        assert result["success"] is True
        assert result["num_solutions"] >= 1

    def test_safe_candidate_true_and_false_cases(self):
        skill = PrologSkill()
        safe_result = skill.query("safe_candidate(alice, acetaminophen).")
        blocked_result = skill.query("safe_candidate(alice, amoxicillin).")

        assert safe_result["success"] is True
        assert blocked_result["success"] is False


class TestAgentSkillRuntimeFacts:
    def test_add_and_retract_fact(self):
        skill = PrologSkill()

        assert skill.add_fact("task(foundation).") is True
        query_after_add = skill.query("task(foundation).")
        assert query_after_add["success"] is True

        assert skill.retract_fact("task(foundation).") is True
        query_after_retract = skill.query("task(foundation).")
        assert query_after_retract["success"] is False

    def test_dependency_rules_derive_blocked_and_milestone_impact(self):
        skill = PrologSkill()
        facts = [
            "task(glazing).",
            "task(enclosure_complete).",
            "depends_on(enclosure_complete, glazing).",
            "milestone(enclosure_complete).",
            "task_supplier(glazing, glass_vendor).",
            "supplier_status(glass_vendor, delayed).",
        ]
        for fact in facts:
            assert skill.add_fact(fact) is True

        blocked_result = skill.query("blocked_task(enclosure_complete, Supplier).")
        delayed_milestone_result = skill.query("delayed_milestone(Milestone, Supplier).")

        assert blocked_result["success"] is True
        assert delayed_milestone_result["success"] is True
