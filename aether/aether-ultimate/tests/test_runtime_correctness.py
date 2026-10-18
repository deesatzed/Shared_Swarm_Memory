import tempfile
import unittest
from pathlib import Path

from aether_core import (
    AetherAgentRuntime,
    CandidateScore,
    ConnectomeScaffoldGraph,
    CriterionWeights,
    HarnessConfig,
    MultiCriteriaDecisionModel,
    ToolRegistry,
    TraceAnalyzer,
)


class FixedLLM:
    def __init__(self, response: str):
        self.response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return self.response


def harness() -> HarnessConfig:
    return HarnessConfig(
        role_name="test",
        system_prompt="Return an action.",
        guardrails=["test only"],
    )


class RuntimeCorrectnessTests(unittest.TestCase):
    def test_response_keeps_full_text_while_preview_stays_display_only(self):
        response = "x" * 180 + " ACTION=escalate_human"
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "trace.jsonl"
            runtime = AetherAgentRuntime(
                harness=harness(),
                router=__import__("aether_core").FastDecisionLayer(ToolRegistry(), ConnectomeScaffoldGraph(":memory:")),
                registry=ToolRegistry(),
                llm=FixedLLM(response),
                trace_log_path=log_path,
            )
            trace = runtime.execute("test", expected_hard_trigger="ACTION=escalate_human")
            persisted = log_path.read_text()

        self.assertTrue(trace.guardrail_passed)
        self.assertEqual(trace.response_preview, response[:160])
        self.assertEqual(trace.response_text, response)
        self.assertNotIn("ACTION=escalate_human", persisted)

    def test_missing_expected_trigger_is_not_reported_as_a_successful_verification(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = AetherAgentRuntime(
                harness=harness(),
                router=__import__("aether_core").FastDecisionLayer(ToolRegistry(), ConnectomeScaffoldGraph(":memory:")),
                registry=ToolRegistry(),
                llm=FixedLLM("ACTION=silent_log"),
                trace_log_path=Path(td) / "trace.jsonl",
            )
            trace = runtime.execute("test")

        self.assertEqual(trace.verification_status, "not_run")
        self.assertFalse(trace.guardrail_passed)

    def test_all_quarantined_candidates_return_no_adoption(self):
        candidates = [
            CandidateScore(candidate_id="unsafe", description="unsafe", scores={"safety_robustness": 1, "evidence_strength": 1}),
            CandidateScore(candidate_id="also_unsafe", description="also unsafe", scores={"safety_robustness": 2, "evidence_strength": 2}),
        ]

        record = MultiCriteriaDecisionModel.evaluate("test", CriterionWeights(), candidates)

        self.assertIsNone(record.selected_candidate_id)
        self.assertIn("No candidate", record.adoption_rationale)
        self.assertTrue(all(candidate.quarantined for candidate in record.candidates))

    def test_mixed_candidates_only_adopt_a_non_quarantined_candidate(self):
        candidates = [
            CandidateScore(candidate_id="unsafe", description="unsafe", scores={"safety_robustness": 1, "evidence_strength": 1}),
            CandidateScore(candidate_id="safe", description="safe", scores={"safety_robustness": 9, "evidence_strength": 9}),
        ]

        record = MultiCriteriaDecisionModel.evaluate("test", CriterionWeights(), candidates)

        self.assertEqual(record.selected_candidate_id, "safe")
        self.assertFalse(next(candidate for candidate in record.candidates if candidate.candidate_id == "safe").quarantined)

    def test_empty_trace_analysis_is_explicitly_incomplete(self):
        report = TraceAnalyzer.analyze([])

        self.assertEqual(report.total_traces, 0)
        self.assertEqual(report.guardrail_pass_rate, 0.0)
        self.assertEqual(report.missed_hard_trigger_count, 0)
        self.assertTrue(any(mode.startswith("NO_TRACES") for mode in report.detected_failure_modes))


if __name__ == "__main__":
    unittest.main()
