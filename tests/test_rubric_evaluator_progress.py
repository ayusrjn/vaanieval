from __future__ import annotations

import sys
from types import SimpleNamespace

from vaanieval.config import EvalConfig
from vaanieval.models import EvalScenario, ScenarioExecution, ScenarioScore, TurnEvent
from vaanieval.progress import finalize_progress, update_progress
from vaanieval.scoring import evaluator
from vaanieval.scoring.rubric import (
    _all_expected_present,
    _any_forbidden_present,
    _fallback_quality,
    _is_unresolved,
    _task_success,
    score_scenario,
)


def test_rubric_adapter_error_short_circuit() -> None:
    scenario = EvalScenario(id="s1", category="smoke", user_message="hello")
    execution = ScenarioExecution(scenario_id="s1", category="smoke", adapter_error="boom")

    score = score_scenario(execution, scenario)
    assert score.passed is False
    assert score.unresolved_turn is True
    assert any("adapter_error" in note for note in score.notes)


def test_rubric_expected_forbidden_and_unresolved_paths() -> None:
    scenario = EvalScenario(
        id="s2",
        category="regression",
        user_message="u",
        expected_facts=["policy"],
        forbidden_claims=["wire transfer"],
        completion_rule="must_contain_all_expected_facts",
    )
    execution = ScenarioExecution(
        scenario_id="s2",
        category="regression",
        turns=[
            TurnEvent(role="agent", message="I do not know.", latency_ms=120),
            TurnEvent(role="agent", message="policy says no wire transfer", latency_ms=150),
        ],
    )

    score = score_scenario(execution, scenario)
    assert score.task_success is False
    assert score.hallucination is True
    assert score.unresolved_turn is True
    assert score.latency_ms_values == [120.0, 150.0]


def test_rubric_helper_functions() -> None:
    assert _task_success("fallback_allowed", answered=True, expected_ok=False, forbidden_hit=False, unresolved=True)
    assert not _task_success("must_answer", answered=False, expected_ok=True, forbidden_hit=False, unresolved=False)
    assert _all_expected_present("a b c", ["a", "b"])
    assert _any_forbidden_present("contains x", ["x"])
    assert _fallback_quality(["Can you clarify?"])
    assert _is_unresolved(["I can't help with that"]) is True


def test_append_discrepancy_note() -> None:
    score = ScenarioScore(
        scenario_id="s",
        category="c",
        passed=True,
        task_success=True,
        unresolved_turn=False,
        hallucination=False,
        fallback_good=True,
    )
    evaluator._append_discrepancy_note(score, "ext", {"pass": False})
    assert "ext_disagrees_with_deterministic" in score.notes


def test_evaluate_scenarios_full_flow_with_external_errors(monkeypatch) -> None:
    scenario = EvalScenario(id="s1", category="smoke", user_message="hello")
    config = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="a")

    class FakeAdapter:
        def run_scenario(self, _scenario):
            return ScenarioExecution(
                scenario_id="s1",
                category="smoke",
                turns=[TurnEvent(role="agent", message="All good", latency_ms=110)],
            )

    class GoodScorer:
        name = "good"

        def score_scenario(self, *_args):
            return {"available": True, "pass": False, "task_success_score": 0.4}

    class FailingScorer:
        name = "bad"

        def score_scenario(self, *_args):
            raise RuntimeError("external failed")

    events: list[str] = []
    monkeypatch.setattr(evaluator, "log_event", lambda msg: events.append(msg))
    monkeypatch.setattr(evaluator, "update_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(evaluator, "finalize_progress", lambda: None)
    monkeypatch.setattr(evaluator, "get_external_scorers", lambda _cfg: [GoodScorer(), FailingScorer()])

    result = evaluator.evaluate_scenarios([scenario], config, run_type="smoke", adapter=FakeAdapter())
    assert result.summary.scenario_count == 1
    assert result.summary.external_scorers == ["good", "bad"]
    assert result.scenario_scores[0].external_scores["good"]["pass"] is False
    assert result.scenario_scores[0].external_scores["bad"]["available"] is False
    assert "bad_error" in result.scenario_scores[0].notes
    assert any("Summary ready" in msg for msg in events)


def test_progress_paths_tty_and_non_tty(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    update_progress(1, 3, prefix="Eval")
    non_tty = capsys.readouterr().out
    assert "Eval:" in non_tty

    class TTYWriter:
        def __init__(self):
            self.buffer = ""

        def isatty(self):
            return True

        def write(self, value):
            self.buffer += value

        def flush(self):
            return None

    writer = TTYWriter()
    monkeypatch.setattr("sys.stdout", writer)
    update_progress(1, 2)
    update_progress(2, 2)
    finalize_progress()
    assert "Progress:" in writer.buffer
