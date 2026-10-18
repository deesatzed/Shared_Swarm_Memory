import tempfile
import unittest
from pathlib import Path

from aether_core import ConnectomeScaffoldGraph, HarnessConfig, ToolRegistry
from aether_swarm import AetherSwarmOrchestrator


class FixedLLM:
    def __init__(self, response: str):
        self.response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return self.response


def harness(role_name: str) -> HarnessConfig:
    return HarnessConfig(role_name=role_name, system_prompt="Return an action.", guardrails=["test only"])


class SwarmCorrectnessTests(unittest.TestCase):
    def build_swarm(self, response: str, fast_threshold: float):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        return AetherSwarmOrchestrator(
            llm=FixedLLM(response),
            connectome=ConnectomeScaffoldGraph(":memory:"),
            registry=ToolRegistry(),
            librarian_harness=harness("librarian"),
            worker_harness=harness("worker"),
            verifier_harness=harness("verifier"),
            fast_bypass_utility_threshold=fast_threshold,
            swarm_log_path=Path(tempdir.name) / "swarm.jsonl",
        )

    def test_fast_path_uses_full_response_but_cannot_claim_verifier_approval(self):
        swarm = self.build_swarm("x" * 180 + " ACTION=escalate_human", fast_threshold=0.30)

        result = swarm.dispatch("ordinary query", expected_hard_trigger="ACTION=escalate_human")

        self.assertTrue(result.fast_path_bypass)
        self.assertEqual(result.final_action, "ACTION=escalate_human")
        self.assertEqual(result.verifier_status, "not_run")
        self.assertFalse(result.verifier_approved)

    def test_failed_verification_is_never_reported_as_approved(self):
        swarm = self.build_swarm("ACTION=silent_log", fast_threshold=0.0)

        result = swarm.dispatch("breach", expected_hard_trigger="ACTION=escalate_human")

        self.assertFalse(result.fast_path_bypass)
        self.assertEqual(result.verifier_status, "failed")
        self.assertFalse(result.verifier_approved)

    def test_handoffs_keep_full_response_text(self):
        swarm = self.build_swarm("x" * 180 + " ACTION=escalate_human", fast_threshold=0.0)

        result = swarm.dispatch("breach", expected_hard_trigger="ACTION=escalate_human")

        self.assertFalse(result.fast_path_bypass)
        self.assertIn("ACTION=escalate_human", result.handoffs[0].payload)


if __name__ == "__main__":
    unittest.main()
