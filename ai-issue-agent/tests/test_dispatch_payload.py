"""Tests of the payload validator of reusable-ai-agent-execution.yml.

The validator is a Python script inline in the workflow, which a reusable workflow needs:
it has no checkout of this repository. The test extracts that script from the YAML and runs
it as the runner does, so it tests what ships and never a copy.
"""

import json
import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/reusable-ai-agent-execution.yml"


def extract_validator() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"python3 -I - <<'PY'\n(.*?)\n\s*PY\n", text, re.S)
    if not match:
        raise AssertionError("the validator heredoc is not in the workflow")
    return textwrap.dedent(match.group(1)) + "\n"


VALIDATOR = extract_validator()
ORIGIN = {"repository": "Jahia/sandbox", "number": 12}


class Result:
    def __init__(self, completed, outputs, summary):
        self.returncode = completed.returncode
        self.stdout = completed.stdout
        self.outputs = outputs
        self.summary = summary


def run(payload, prompt="Fix the bug", owner="Jahia"):
    """Run the validator on `payload` (a dict, or a raw string) and return what it wrote."""
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    with tempfile.TemporaryDirectory() as tmp:
        output, summary = Path(tmp, "output"), Path(tmp, "summary")
        env = {
            "PATH": os.environ["PATH"],
            "PAYLOAD": raw,
            "PROMPT": prompt,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
            "GITHUB_REPOSITORY_OWNER": owner,
            "GITHUB_SERVER_URL": "https://github.com",
        }
        completed = subprocess.run(
            ["python3", "-I", "-"], input=VALIDATOR, env=env, capture_output=True, text=True, check=False
        )
        outputs = {}
        if output.exists():
            for line in output.read_text(encoding="utf-8").splitlines():
                key, _, value = line.partition("=")
                outputs[key] = value
        return Result(completed, outputs, summary.read_text(encoding="utf-8") if summary.exists() else "")


def valid(**overrides):
    return {"origin": dict(ORIGIN), **overrides}


class AcceptedPayloads(unittest.TestCase):
    def test_minimal_payload_takes_the_defaults(self):
        result = run(valid())
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.outputs["runs_on"], '"self-hosted"')
        self.assertEqual(result.outputs["timeout_minutes"], "65")
        self.assertEqual(result.outputs["model"], "opus")
        self.assertEqual(result.outputs["session_index"], "1")
        self.assertEqual(result.outputs["remaining_seconds"], str(65 * 60))
        self.assertEqual(result.outputs["guard_run_id"], "")
        self.assertEqual(result.outputs["cortex_ref"], "main")
        self.assertEqual(result.outputs["claude_code_version"], "stable")
        for flag in ("debug", "skip_smoke_tests", "reuse_claude_code"):
            self.assertEqual(result.outputs[flag], "false")
        self.assertEqual(result.outputs["origin_target"], "issue")
        self.assertEqual(result.outputs["issue_url"], "https://github.com/Jahia/sandbox/issues/12")

    def test_pull_request_target_builds_a_pull_url(self):
        origin = {**ORIGIN, "target": "pull_request"}
        result = run({"origin": origin})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.outputs["issue_url"], "https://github.com/Jahia/sandbox/pull/12")
        self.assertEqual(result.outputs["origin_target"], "pull_request")

    def test_default_runner_reads_as_self_hosted(self):
        result = run(valid(runner="default"))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.outputs["runs_on"], '"self-hosted"')

    def test_a_list_of_labels_stays_a_list(self):
        result = run(valid(runner=["self-hosted", "small"]))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.outputs["runs_on"], '["self-hosted", "small"]')

    def test_remaining_seconds_defaults_to_the_timeout(self):
        result = run(valid(timeout_minutes=30))
        self.assertEqual(result.outputs["remaining_seconds"], str(30 * 60))

    def test_explicit_fields_pass_through(self):
        result = run(
            valid(
                model="sonnet",
                session_index=3,
                remaining_seconds=900,
                guard_run_id=123456,
                cortex_ref="feat/x",
                claude_code_version="2.1.0",
                debug=True,
                skip_smoke_tests=True,
                reuse_claude_code=True,
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.outputs["model"], "sonnet")
        self.assertEqual(result.outputs["session_index"], "3")
        self.assertEqual(result.outputs["remaining_seconds"], "900")
        self.assertEqual(result.outputs["guard_run_id"], "123456")
        self.assertEqual(result.outputs["cortex_ref"], "feat/x")
        self.assertEqual(result.outputs["claude_code_version"], "2.1.0")
        self.assertEqual(
            [result.outputs[k] for k in ("debug", "skip_smoke_tests", "reuse_claude_code")],
            ["true", "true", "true"],
        )

    def test_the_owner_check_ignores_case(self):
        result = run({"origin": {"repository": "jahia/sandbox", "number": 1}}, owner="Jahia")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_the_summary_lists_the_decision(self):
        result = run(valid(), prompt="Fix the bug")
        self.assertIn("### AI agent execution", result.summary)
        self.assertIn("| timeout_minutes | `65` |", result.summary)
        self.assertIn("| prompt length | 11 characters |", result.summary)


class RefusedPayloads(unittest.TestCase):
    def assertRefused(self, payload, fragment, **kwargs):
        result = run(payload, **kwargs)
        self.assertEqual(result.returncode, 1, f"expected a refusal, got {result.outputs}")
        self.assertIn("::error title=Invalid dispatch payload::", result.stdout)
        self.assertIn(fragment, result.stdout)
        self.assertEqual(result.outputs, {}, "a refused payload must write no output")

    def test_empty_or_blank_prompt(self):
        self.assertRefused(valid(), "the prompt is empty", prompt="")
        self.assertRefused(valid(), "the prompt is empty", prompt="   \n")

    def test_payload_that_is_not_json(self):
        self.assertRefused("{not json", "the payload is not JSON")

    def test_payload_that_is_not_an_object(self):
        self.assertRefused("[1, 2]", "must be a JSON object")
        self.assertRefused("null", "must be a JSON object")

    def test_unsupported_version(self):
        self.assertRefused(valid(version=2), "version must be an integer from 1 to 1")

    def test_timeout_bounds(self):
        self.assertRefused(valid(timeout_minutes=5), "timeout_minutes must be an integer from 6 to 360")
        self.assertRefused(valid(timeout_minutes=361), "timeout_minutes must be an integer from 6 to 360")
        for accepted in (6, 360):
            self.assertEqual(run(valid(timeout_minutes=accepted)).returncode, 0)

    def test_a_boolean_is_not_an_integer(self):
        self.assertRefused(valid(timeout_minutes=True), "timeout_minutes must be an integer")
        self.assertRefused(valid(session_index=True), "session_index must be an integer")

    def test_a_string_is_not_an_integer(self):
        self.assertRefused(valid(timeout_minutes="65"), "timeout_minutes must be an integer")

    def test_origin_is_required(self):
        self.assertRefused({}, "origin is required")
        self.assertRefused({"origin": "Jahia/sandbox#1"}, "origin is required")

    def test_origin_repository_shape(self):
        self.assertRefused({"origin": {"repository": "sandbox", "number": 1}}, "origin.repository must be owner/repo")
        self.assertRefused(
            {"origin": {"repository": "Jahia/sandbox/extra", "number": 1}}, "origin.repository must be owner/repo"
        )
        self.assertRefused({"origin": {"number": 1}}, "origin.repository must be owner/repo")

    def test_origin_repository_of_another_owner(self):
        self.assertRefused({"origin": {"repository": "evil/repo", "number": 1}}, "must belong to Jahia")

    def test_origin_number(self):
        for bad in (0, -1, "1", True, None):
            with self.subTest(number=bad):
                self.assertRefused({"origin": {"repository": "Jahia/sandbox", "number": bad}}, "origin.number")

    def test_origin_target(self):
        self.assertRefused({"origin": {**ORIGIN, "target": "discussion"}}, "origin.target must be issue or pull_request")

    def test_runner_with_expression_syntax(self):
        self.assertRefused(valid(runner="${{ secrets.X }}"), "runner must be a label")
        self.assertRefused(valid(runner=["ok", "a b"]), "runner must be a label")

    def test_runner_list_limits(self):
        self.assertRefused(valid(runner=[]), "runner must be a label")
        self.assertRefused(valid(runner=["a"] * 6), "runner must be a label")
        self.assertEqual(run(valid(runner=["a"] * 5)).returncode, 0)
        self.assertRefused(valid(runner=5), "runner must be a label")

    def test_guard_run_id(self):
        for bad in (0, -3, "7", True):
            with self.subTest(guard_run_id=bad):
                self.assertRefused(valid(guard_run_id=bad), "guard_run_id must be a positive integer")

    def test_text_fields_refuse_unsafe_characters(self):
        # An output is read as an expression later on: no quote, brace, space or newline gets through.
        self.assertRefused(valid(model="opus; rm -rf /"), "model must be a string matching")
        self.assertRefused(valid(model="a\nb"), "model must be a string matching")
        self.assertRefused(valid(cortex_ref="main'}"), "cortex_ref must be a string matching")
        self.assertRefused(valid(cortex_ref=""), "cortex_ref must be a string matching")
        self.assertRefused(valid(claude_code_version="x" * 31), "claude_code_version must be a string matching")
        self.assertRefused(valid(model=7), "model must be a string matching")

    def test_flags_must_be_booleans(self):
        for name in ("debug", "skip_smoke_tests", "reuse_claude_code"):
            with self.subTest(flag=name):
                self.assertRefused(valid(**{name: "true"}), f"{name} must be true or false")
                self.assertRefused(valid(**{name: 1}), f"{name} must be true or false")

    def test_remaining_seconds_bounds(self):
        self.assertRefused(valid(remaining_seconds=-1), "remaining_seconds must be an integer")
        self.assertEqual(run(valid(remaining_seconds=0)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
