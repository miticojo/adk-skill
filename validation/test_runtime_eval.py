"""Execute documented runtime examples and validate eval fixtures without models."""

import asyncio
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from google.adk.evaluation.conversation_scenarios import ConversationScenarios
from google.adk.evaluation.eval_case import EvalCase
from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation.eval_set import EvalSet
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types


REFERENCES = Path(__file__).resolve().parents[1] / "adk-skill" / "references"


def example(heading):
    text = (REFERENCES / "advanced-patterns.md").read_text()
    section = text.split(heading, 1)[1]
    return re.search(r"```python\n(.*?)\n```", section, re.S).group(1)


def execute(heading, **names):
    exec(compile(example(heading), heading, "exec"), names)
    return names


class RuntimeExamplesTest(unittest.TestCase):
    def test_before_model_guardrail_returns_llm_response(self):
        callback = execute(
            "### Before-Model Guardrail", is_unsafe=lambda text: "blocked" in text
        )["content_safety_check"]
        request = LlmRequest(contents=[types.Content(
            role="user", parts=[types.Part.from_text(text="blocked")]
        )])
        response = callback(SimpleNamespace(state={}), request)
        self.assertIsInstance(response, LlmResponse)
        self.assertEqual(response.content.role, "model")
        self.assertIsNone(callback(None, LlmRequest(contents=[])))

    def test_before_tool_validation_does_not_short_circuit_valid_calls(self):
        callback = execute("### Input Validation")["validate_before_tool"]
        self.assertIsNone(callback(None, {"customer_id": "CUST-123"}, None))
        self.assertIn("error", callback(None, {"customer_id": 123}, None))

    def test_rate_limit_wait_is_awaited_and_window_resets(self):
        namespace = execute("### Rate Limiting")
        context = SimpleNamespace(state={
            "rate_window_start": 100.0, "rate_request_count": 15
        })
        with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
            with patch("time.time", side_effect=[100.0, 160.0]):
                asyncio.run(namespace["rate_limit_callback"](context, None))
            sleep.assert_awaited_once_with(60.0)
        self.assertEqual(context.state["rate_request_count"], 1)
        self.assertEqual(context.state["rate_window_start"], 160.0)

    def test_model_construction_examples(self):
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "offline-test-key",
            "OPENAI_API_KEY": "offline-test-key",
            "OPENAI_MODEL": "gpt-4o",
            "MANAGED_AGENT_ID": "agents/offline-test",
        }):
            managed = execute("## Managed Agents (Preview, 2.4+)")["agent"]
            self.assertEqual(managed.agent_id, "agents/offline-test")
            openai = execute("## Multi-Model Support")["agent"]
            self.assertEqual(openai.model.model, "gpt-4o")
            voice = execute("## Live Voice Integrations (Experimental)")["voice_agent"]
            self.assertEqual(voice.model.model, "gemini-flash-latest")

    def test_creative_pipeline_constructs_with_distinct_state_keys(self):
        pipeline = execute("### Creative Pipeline (Parallel Writers + Judge)")["root_agent"]
        writers = pipeline.sub_agents[0].sub_agents
        self.assertEqual(len({agent.output_key for agent in writers}), len(writers))

    def test_all_documented_eval_json_matches_adk_schemas(self):
        text = (REFERENCES / "evaluation.md").read_text()
        blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
        self.assertTrue(blocks)
        for index, block in enumerate(blocks):
            with self.subTest(index=index):
                data = json.loads(block)
                if "criteria" in data:
                    EvalConfig.model_validate(data)
                elif "eval_set_id" in data:
                    EvalSet.model_validate(data)
                elif "eval_id" in data:
                    EvalCase.model_validate(data)
                elif "scenarios" in data:
                    ConversationScenarios.model_validate(data)
                else:
                    self.fail("Unvalidated JSON example")


if __name__ == "__main__":
    unittest.main()
