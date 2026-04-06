import sys

sys.path.insert(0, "src")

from parser.statement_classifier import StatementClassifier


class TestStatementClassifier:
    def setup_method(self):
        self.classifier = StatementClassifier()

    def test_query_classification(self):
        result = self.classifier.classify("Who is John's parent?").to_dict()
        assert result["kind"] == "query"
        assert result["can_query_now"] is True
        assert result["suggested_operation"] == "query"

    def test_hard_fact_with_speaker_resolution(self):
        result = self.classifier.classify("My manager is Dana.").to_dict()
        assert result["kind"] == "hard_fact"
        assert result["needs_speaker_resolution"] is True
        assert result["suggested_operation"] == "store_fact"

    def test_tentative_fact(self):
        result = self.classifier.classify("Maybe Alice reports to Dana.").to_dict()
        assert result["kind"] == "tentative_fact"
        assert result["suggested_operation"] == "store_tentative_fact"

    def test_correction(self):
        result = self.classifier.classify("Actually, I meant Alice.").to_dict()
        assert result["kind"] == "correction"
        assert result["suggested_operation"] == "revise_memory"

    def test_preference(self):
        result = self.classifier.classify("Keep responses concise.").to_dict()
        assert result["kind"] == "preference"
        assert result["suggested_operation"] == "store_preference"

    def test_session_context(self):
        result = self.classifier.classify("For this session, treat Alice as admin.").to_dict()
        assert result["kind"] == "session_context"
        assert result["suggested_operation"] == "store_session_context"

    def test_instruction(self):
        result = self.classifier.classify("Do not store anything yet.").to_dict()
        assert result["kind"] == "instruction"
        assert result["suggested_operation"] == "follow_instruction"

    def test_unknown(self):
        result = self.classifier.classify("Blue clocks breathe in triangles.").to_dict()
        assert result["kind"] == "unknown"
        assert result["suggested_operation"] == "none"
