from __future__ import annotations

import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from vaanieval.config import EvalConfig
from vaanieval.models import EvalScenario, ScenarioExecution, ScenarioScore, TurnEvent
from vaanieval.scoring.scorers import _load_custom_scorer, get_external_scorers
from vaanieval.scoring.scorers.base import ExternalScorer
from vaanieval.scoring.scorers.noop_scorer import NoopScorer
from vaanieval.scoring.scorers.openai_evals_scorer import (
    OpenAIEvalsScorer,
    _as_str_list,
    _as_unit_float,
    _extract_first_json_object,
)


def _sample_inputs() -> tuple[EvalScenario, ScenarioExecution, ScenarioScore]:
    scenario = EvalScenario(id="s1", category="smoke", user_message="hello")
    execution = ScenarioExecution(
        scenario_id="s1",
        category="smoke",
        turns=[TurnEvent(role="user", message="hi"), TurnEvent(role="agent", message="hello")],
    )
    score = ScenarioScore(
        scenario_id="s1",
        category="smoke",
        passed=True,
        task_success=True,
        unresolved_turn=False,
        hallucination=False,
        fallback_good=True,
    )
    return scenario, execution, score


def test_noop_scorer_and_base_abstract_method() -> None:
    scenario, execution, score = _sample_inputs()
    payload = NoopScorer().score_scenario(scenario, execution, score)
    assert payload["available"] is True
    assert payload["pass"] is True

    with pytest.raises(NotImplementedError):
        ExternalScorer.score_scenario(None, scenario, execution, score)


def test_get_external_scorers_and_unknown() -> None:
    cfg = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="a", enabled_external_scorers=["noop"])
    scorers = get_external_scorers(cfg)
    assert len(scorers) == 1
    assert scorers[0].name == "noop"

    bad_cfg = EvalConfig(
        elevenlabs_api_key="k",
        elevenlabs_agent_id="a",
        enabled_external_scorers=["unknown_provider"],
    )
    with pytest.raises(ValueError):
        get_external_scorers(bad_cfg)


def test_load_custom_scorer_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = tmp_path / "custom_scorer_mod.py"
    module_path.write_text(
        textwrap.dedent(
            """
            from vaanieval.scoring.scorers.base import ExternalScorer

            class MyScorer(ExternalScorer):
                name = "my"
                def __init__(self, config):
                    self.config = config
                def score_scenario(self, scenario, execution, deterministic_score):
                    return {"available": True, "pass": deterministic_score.passed}

            class NotAScorer:
                def __init__(self, config):
                    self.config = config
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    cfg = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="a")

    scorer = _load_custom_scorer("custom_scorer_mod:MyScorer", cfg)
    assert scorer.name == "my"

    with pytest.raises(TypeError):
        _load_custom_scorer("custom_scorer_mod:NotAScorer", cfg)

    with pytest.raises(ValueError):
        _load_custom_scorer("custom_scorer_mod", cfg)


def test_openai_helper_functions() -> None:
    assert _as_unit_float(-10) == 0.0
    assert _as_unit_float(1.5) == 1.0
    assert _as_unit_float("0.23456") == 0.2346
    assert _as_unit_float("bad") == 0.0

    assert _as_str_list([1, "a", True]) == ["1", "a", "True"]
    assert _as_str_list("x") == []

    parsed = _extract_first_json_object("prefix {\"pass\": true} suffix")
    assert parsed["pass"] is True
    with pytest.raises(ValueError):
        _extract_first_json_object("no json here")


def test_openai_scorer_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    scenario, execution, deterministic = _sample_inputs()
    cfg = EvalConfig(
        elevenlabs_api_key="k",
        elevenlabs_agent_id="a",
        openai_api_key="openai-key",
        openai_model="gpt-4o-mini",
    )

    class FakeResponses:
        def create(self, **_kwargs):
            return SimpleNamespace(
                output_text='{"pass": true, "task_success_score": 0.9, "factuality_score": 0.8, "confidence": 0.7, "rationale": "ok", "issues": ["none"]}'
            )

    class FakeClient:
        def __init__(self):
            self.responses = FakeResponses()

    monkeypatch.setattr(OpenAIEvalsScorer, "_create_client", lambda self, _cfg: FakeClient())
    scorer = OpenAIEvalsScorer(cfg)
    payload = scorer.score_scenario(scenario, execution, deterministic)
    assert payload["available"] is True
    assert payload["pass"] is True
    assert payload["task_success_score"] == 0.9

    failed_execution = ScenarioExecution(scenario_id="s1", category="smoke", adapter_error="boom")
    failed_payload = scorer.score_scenario(scenario, failed_execution, deterministic)
    assert failed_payload["available"] is False

    class BrokenResponses:
        def create(self, **_kwargs):
            raise RuntimeError("request failed")

    class BrokenClient:
        def __init__(self):
            self.responses = BrokenResponses()

    monkeypatch.setattr(OpenAIEvalsScorer, "_create_client", lambda self, _cfg: BrokenClient())
    broken = OpenAIEvalsScorer(cfg)
    error_payload = broken.score_scenario(scenario, execution, deterministic)
    assert error_payload["available"] is False


def test_openai_create_client_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="a", openai_api_key="x")
    monkeypatch.setattr("importlib.import_module", lambda *_args, **_kwargs: (_ for _ in ()).throw(ImportError("missing")))
    with pytest.raises(RuntimeError):
        OpenAIEvalsScorer(cfg)
