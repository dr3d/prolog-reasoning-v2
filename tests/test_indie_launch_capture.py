import importlib.util
import json
from pathlib import Path


def _load_capture_module():
    module_path = Path("scripts/capture_indie_launch_warroom_session.py")
    spec = importlib.util.spec_from_file_location("capture_indie_launch_warroom_session", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_indie_launch_captured_transcript_validates():
    module = _load_capture_module()
    transcript_path = Path("docs/examples/indie-launch-warroom-session.json")
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))

    findings = module.validate_transcript(transcript)

    assert findings == []


def test_indie_launch_validator_flags_missing_required_tools():
    module = _load_capture_module()
    transcript = {
        "captured_at": "2026-04-07T00:00:00+00:00",
        "model": "test",
        "integration": "test",
        "steps": [
            {
                "step": step_name,
                "prompt": "test",
                "tool_calls": [{"tool": "query_rows", "arguments": {"query": "task(Task)."}, "output": None}],
                "assistant_message": "ok",
            }
            for step_name in module.STEP_NAMES
        ],
    }

    findings = module.validate_transcript(transcript)

    assert any("Missing required tool usage:" in finding for finding in findings)
