"""Execute documented examples against ADK 2.13.0 without model or cloud calls.

Run: python -m unittest discover -s validation -v
Dependencies: google-adk[a2a,eval,openai,mcp]==2.13.0 (checked 2026-10-25).
"""

import math
import asyncio
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from google.adk.agents import Context
from google.adk import Workflow
from google.adk.apps import App, ResumabilityConfig
from google.adk.runners import InMemoryRunner
from google.adk.workflow import node
from google.genai import types
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

    def test_model_consultation_has_explicit_budgets(self):
        agent = example("references/tools-reference.md", "## Model Consultation")["agent"]
        advisor = agent.tools[0]
        self.assertEqual(advisor.max_uses, 1)
        self.assertEqual(advisor.session_max_uses, 3)


class IntegrationExamples(unittest.IsolatedAsyncioTestCase):
    async def test_skill_load_unload_and_catalog(self):
        with patch.dict(os.environ, {"ADK_ENABLE_SKILL_LIFECYCLE": "1"}):
            ns = example("references/tools-reference.md", "### Discovery and Lifecycle")
            toolset = ns["skill_tools"]
            self.addAsyncCleanup(toolset.close)
            sessions = InMemorySessionService()
            session = await sessions.create_session(app_name="test", user_id="user")
            from google.adk.agents import LlmAgent
            context = Context(InvocationContext(
                session_service=sessions, session=session, invocation_id="skill-test",
                agent=LlmAgent(name="skill_agent"),
            ))
            self.assertEqual(toolset.list_active_skills(context), [])
            self.assertTrue(await toolset.load_skill(context, "greeting-skill"))
            self.assertEqual(toolset.list_active_skills(context), ["greeting-skill"])
            self.assertTrue(toolset.unload_skill(context, "greeting-skill"))
            self.assertEqual(toolset.list_active_skills(context), [])

    async def test_a2a_server_and_native_task_proxy_construct(self):
        server = example("references/a2a-protocol.md", "## Expose an Agent")
        app = server["a2a_app"]
        async with app.router.lifespan_context(app):
            self.assertTrue(app.routes)
        proxy = example("references/a2a-protocol.md", "## Native Task Delegation")
        self.assertEqual(proxy["remote_math"].mode, "task")

    async def test_model_failover_preserves_request(self):
        from google.adk.models import BaseLlm, LlmResponse
        from google.adk.models.llm_request import LlmRequest
        from google.genai.errors import ServerError

        class FailingLlm(BaseLlm):
            async def generate_content_async(self, llm_request, stream=False):
                llm_request.contents.clear()
                raise ServerError(503, {"error": {"message": "offline failure"}})
                yield

        class BackupLlm(BaseLlm):
            async def generate_content_async(self, llm_request, stream=False):
                if not llm_request.contents:
                    raise AssertionError("Fallback lost the original request")
                yield LlmResponse(content=types.Content(
                    role="model", parts=[types.Part.from_text(text="backup response")],
                ))

        ns = example("references/design-patterns.md", "### Model Failover")
        fallback = ns["FallbackModel"](models=[FailingLlm(model="primary"), BackupLlm(model="backup")])
        request = LlmRequest(contents=[types.Content(
            role="user", parts=[types.Part.from_text(text="hello")],
        )])
        responses = [r async for r in fallback.generate_content_async(request)]
        self.assertEqual(responses[-1].content.parts[0].text, "backup response")


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


class WorkflowExamples(unittest.IsolatedAsyncioTestCase):
    async def runner_for(self, workflow):
        runner = InMemoryRunner(app=App(
            name="test", root_agent=workflow,
            resumability_config=ResumabilityConfig(is_resumable=True),
        ))
        self.addAsyncCleanup(runner.close)
        session = await runner.session_service.create_session(app_name="test", user_id="user")
        return runner, session

    async def run_message(self, runner, session, text, **kwargs):
        return [event async for event in runner.run_async(
            user_id="user", session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=text)]),
            **kwargs,
        )]

    async def test_routing_and_fallback(self):
        for text, expected in (("bug", "bug"), ("support", "support"), ("other", "unknown")):
            with self.subTest(text=text):
                ns = example("references/workflows.md", "### Conditional Routing")
                runner, session = await self.runner_for(ns["root_agent"])
                events = await self.run_message(runner, session, text)
                self.assertIn(expected, [event.output for event in events])

    async def test_parallel_join(self):
        ns = example("references/workflows.md", "### Fan-out and Fan-in")
        runner, session = await self.runner_for(ns["root_agent"])
        events = await self.run_message(runner, session, "hello world")
        self.assertIn("HELLO WORLD (2 words)", [event.output for event in events])

    async def test_dynamic_dispatch(self):
        ns = example("references/workflows.md", "### Bounded Loops and Stable Execution IDs")
        runner, session = await self.runner_for(ns["root_agent"])
        events = await self.run_message(runner, session, "hello")
        self.assertIn("hello!!!", [event.output for event in events])

    async def test_confirmation_accept_and_reject(self):
        for accepted in (True, False):
            with self.subTest(accepted=accepted):
                ns = example("references/workflows.md", "### Node Confirmation")
                runner, session = await self.runner_for(ns["root_agent"])
                paused = await self.run_message(runner, session, "report")
                calls = [call for event in paused for call in event.get_function_calls()
                         if call.name == "adk_request_input"]
                self.assertEqual(len(calls), 1)
                self.assertNotIn("approved_count", session.state)
                helper = example("references/workflows.md", "### Resuming a RequestInput")
                resumed = await helper["resume_input"](
                    runner, session.id, paused[0].invocation_id,
                    calls[0].args["interruptId"], {"confirmed": accepted},
                )
                stored = await runner.session_service.get_session(
                    app_name="test", user_id="user", session_id=session.id,
                )
                self.assertEqual(stored.state.get("approved_count", 0), int(accepted))
                outputs = [event.output for event in resumed if event.output is not None]
                self.assertIn("Approved: report" if accepted else
                              {"error": "This tool call is rejected."}, outputs)

    async def test_failed_node_reexecutes_on_resume(self):
        attempts = []

        def flaky(node_input: str) -> str:
            attempts.append(node_input)
            if len(attempts) == 1:
                raise RuntimeError("transient offline failure")
            return "recovered"

        runner, session = await self.runner_for(Workflow(name="recovery", edges=[("START", flaky)]))
        with self.assertRaisesRegex(RuntimeError, "transient offline failure"):
            await self.run_message(runner, session, "start")
        stored = await runner.session_service.get_session(
            app_name="test", user_id="user", session_id=session.id,
        )
        invocation_id = stored.events[-1].invocation_id
        recovered = [event async for event in runner.run_async(
            user_id="user", session_id=session.id, invocation_id=invocation_id,
        )]
        self.assertEqual(len(attempts), 2)
        self.assertIn("recovered", [event.output for event in recovered])

    async def test_abort_stops_running_node(self):
        started = asyncio.Event()
        stopped = asyncio.Event()

        async def wait(node_input: str) -> str:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        runner, session = await self.runner_for(Workflow(name="abort", edges=[("START", wait)]))
        abort_signal = asyncio.Event()
        task = asyncio.create_task(self.run_message(runner, session, "start", abort_signal=abort_signal))
        await asyncio.wait_for(started.wait(), timeout=5)
        abort_signal.set()
        await asyncio.wait_for(task, timeout=5)
        self.assertTrue(stopped.is_set())


if __name__ == "__main__":
    unittest.main()
