"""Execute documented examples against ADK 2.13.0 without model or cloud calls.

Run: python -m unittest discover -s validation -v
Dependencies: google-adk[a2a,eval,openai,mcp]==2.13.0 (checked 2026-10-25).
"""

import math
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from google.adk.agents import Context
from google.adk.agents.invocation_context import InvocationContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService


SKILL = Path(__file__).resolve().parents[1] / "adk-skill"


def example(filename, heading):
    text = (SKILL / filename).read_text()
    section = text.split(heading, 1)[1]
    code = re.search(r"```python\n(.*?)\n```", section, re.S).group(1)
    namespace = {}
    exec(compile(code, filename, "exec"), namespace)
    return namespace


class ToolExamples(unittest.TestCase):
    def test_calculator_validates_operands_and_result(self):
        calculate = example("references/tools-reference.md", "## FunctionTool")["calculate"]
        self.assertEqual(calculate(2.0, 3.0), {"result": 5.0})
        for invalid in ("__import__('os')", True, math.nan, math.inf):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                calculate(invalid, 1.0)
        with self.assertRaises(ValueError):
            calculate(1e308, 1e308)

    def test_authenticated_tool_does_not_expose_credentials(self):
        with patch.dict(os.environ, {"CRM_API_KEY": "offline-test-key"}):
            ns = example("references/tools-reference.md", "## Tool Authentication")
        declaration = ns["tool"]._get_declaration()
        self.assertIn("customer_id", declaration.parameters_json_schema["properties"])
        self.assertNotIn("credential", declaration.parameters_json_schema["properties"])
        self.assertNotIn("offline-test-key", str(declaration))
        credential = ns["AuthCredential"](
            auth_type=ns["AuthCredentialTypes"].API_KEY, api_key="offline-test-key",
        )
        self.assertNotIn("offline-test-key", str(ns["get_customer_data"]("CUST-1", credential)))


class ArtifactExamples(unittest.IsolatedAsyncioTestCase):
    async def test_save_load_list_and_missing_file(self):
        ns = example("references/memory-artifacts.md", "### Saving and Loading Artifacts")
        sessions = InMemorySessionService()
        session = await sessions.create_session(app_name="test", user_id="user")
        context = Context(InvocationContext(
            session_service=sessions, session=session, invocation_id="offline-test",
            artifact_service=InMemoryArtifactService(),
        ))
        self.assertIn("version 0", await ns["save_report"]("report.txt", context))
        self.assertIn("version 1", await ns["save_report"]("report.txt", context))
        self.assertEqual(await ns["list_files"](context), ["report.txt"])
        metadata = await ns["load_latest_report"]("report.txt", context)
        self.assertEqual(metadata, {"mime_type": "text/plain", "size": len(b"Report ready\n")})
        self.assertEqual(await ns["load_latest_report"]("missing.txt", context),
                         {"error": "missing.txt not found"})


if __name__ == "__main__":
    unittest.main()
