import tempfile
import unittest
from pathlib import Path

from vaanieval.models import EvalRunResult, RunSummary, ScenarioExecution, ScenarioScore
from vaanieval.reporting.json_report import write_json_report
from vaanieval.reporting.markdown_report import write_markdown_report


class TestReporting(unittest.TestCase):
    def test_reports_written(self):
        result = EvalRunResult(
            summary=RunSummary(
                run_type="smoke",
                scenario_count=1,
                passed_count=1,
                task_success_rate=1.0,
                unresolved_turn_rate=0.0,
                hallucination_rate=0.0,
                fallback_quality=1.0,
                latency_p50_ms=100.0,
                latency_p95_ms=120.0,
                latency_p99_ms=130.0,
                gate_passed=True,
                threshold_task_success_rate=0.85,
                threshold_unresolved_turn_rate=0.10,
                threshold_hallucination_rate=0.05,
                threshold_latency_p95_ms=1200.0,
            ),
            scenario_scores=[
                ScenarioScore(
                    scenario_id="s1",
                    category="retrieval",
                    passed=True,
                    task_success=True,
                    unresolved_turn=False,
                    hallucination=False,
                    fallback_good=True,
                    latency_ms_values=[100.0],
                    notes=[],
                )
            ],
            execution=[ScenarioExecution(scenario_id="s1", category="retrieval")],
        )

        with tempfile.TemporaryDirectory() as tmp:
            json_path = write_json_report(result, tmp)
            md_path = write_markdown_report(result, tmp)
            self.assertTrue(Path(json_path).exists())
            self.assertTrue(Path(md_path).exists())

    def test_markdown_includes_external_section(self):
        result = EvalRunResult(
            summary=RunSummary(
                run_type="regression",
                scenario_count=1,
                passed_count=0,
                task_success_rate=0.0,
                unresolved_turn_rate=1.0,
                hallucination_rate=0.0,
                fallback_quality=1.0,
                latency_p50_ms=100.0,
                latency_p95_ms=120.0,
                latency_p99_ms=130.0,
                gate_passed=False,
                threshold_task_success_rate=0.85,
                threshold_unresolved_turn_rate=0.10,
                threshold_hallucination_rate=0.05,
                threshold_latency_p95_ms=1200.0,
                external_scoring_enabled=True,
                external_scorers=["openai_evals"],
                external_summary={"openai_evals": {"avg_pass": 0.5}},
                external_error_count=1,
            ),
            scenario_scores=[
                ScenarioScore(
                    scenario_id="s1",
                    category="retrieval",
                    passed=False,
                    task_success=False,
                    unresolved_turn=True,
                    hallucination=False,
                    fallback_good=True,
                    latency_ms_values=[100.0],
                    notes=["missing expected facts"],
                    external_scores={"openai_evals": {"available": False, "error": "timeout"}},
                )
            ],
            execution=[ScenarioExecution(scenario_id="s1", category="retrieval")],
        )

        with tempfile.TemporaryDirectory() as tmp:
            md_path = write_markdown_report(result, tmp)
            text = Path(md_path).read_text(encoding="utf-8")
            self.assertIn("## External Scoring", text)
            self.assertIn("openai_evals", text)
            self.assertIn("notes:", text)


if __name__ == "__main__":
    unittest.main()
