from pathlib import Path

import pytest

from vaanieval.config import EvalConfig
from vaanieval.models import ScenarioScore
from vaanieval.scenarios.loader import _to_str_list, load_scenarios
from vaanieval.scenarios.schema import validate_scenario_payload
from vaanieval.scoring.metrics import summarize


def test_validate_scenario_payload_reports_type_errors() -> None:
    errors = validate_scenario_payload(
        {
            "id": 1,
            "category": 2,
            "user_message": 3,
            "expected_facts": "x",
            "forbidden_claims": "y",
            "safety_flags": "z",
            "max_turns": "bad",
        }
    )
    assert "id must be a string" in errors
    assert "category must be a string" in errors
    assert "user_message must be a string" in errors
    assert "expected_facts must be a list" in errors
    assert "forbidden_claims must be a list" in errors
    assert "safety_flags must be a list" in errors
    assert "max_turns must be an integer" in errors


def test_validate_scenario_payload_missing_fields() -> None:
    errors = validate_scenario_payload({"id": "x"})
    assert errors
    assert "missing fields:" in errors[0]


def test_load_scenarios_supports_list_and_scenarios_key(tmp_path: Path) -> None:
    list_file = tmp_path / "list.yaml"
    list_file.write_text(
        "- id: s1\n  category: retrieval\n  user_message: hello\n",
        encoding="utf-8",
    )
    scenarios = load_scenarios(str(list_file))
    assert len(scenarios) == 1
    assert scenarios[0].id == "s1"

    keyed_file = tmp_path / "keyed.yaml"
    keyed_file.write_text(
        "scenarios:\n  - id: s2\n    category: regression\n    user_message: hi\n",
        encoding="utf-8",
    )
    scenarios = load_scenarios(str(keyed_file))
    assert len(scenarios) == 1
    assert scenarios[0].id == "s2"


def test_load_scenarios_validation_and_shape_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "scenarios:\n  - id: 10\n    category: retrieval\n  - not-an-object\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        load_scenarios(str(bad))

    text = str(exc.value)
    assert "Invalid scenarios:" in text
    assert "scenario[0]" in text
    assert "scenario[1] must be an object" in text

    wrong_root = tmp_path / "wrong_root.yaml"
    wrong_root.write_text("foo: bar\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_scenarios(str(wrong_root))

    with pytest.raises(FileNotFoundError):
        load_scenarios(str(tmp_path / "missing.yaml"))


def test_to_str_list_converts_and_handles_non_list() -> None:
    assert _to_str_list([1, "a", True]) == ["1", "a", "True"]
    assert _to_str_list("not-list") == []


def test_summarize_handles_empty_scores_and_external_fields() -> None:
    cfg = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="a")
    summary = summarize("smoke", [], cfg, external_scorers=["openai_evals"])
    assert summary.scenario_count == 0
    assert summary.task_success_rate == 0.0
    assert summary.latency_p95_ms == 0.0
    assert summary.external_scoring_enabled is True
    assert summary.external_scorers == ["openai_evals"]


def test_summarize_aggregates_external_scores() -> None:
    cfg = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="a", latency_p95_threshold_ms=9999)
    scores = [
        ScenarioScore(
            scenario_id="s1",
            category="retrieval",
            passed=True,
            task_success=True,
            unresolved_turn=False,
            hallucination=False,
            fallback_good=True,
            latency_ms_values=[100, 200],
            external_scores={
                "openai_evals": {
                    "available": True,
                    "aligned": True,
                    "score": 0.8,
                }
            },
        ),
        ScenarioScore(
            scenario_id="s2",
            category="retrieval",
            passed=False,
            task_success=False,
            unresolved_turn=True,
            hallucination=True,
            fallback_good=False,
            latency_ms_values=[250],
            external_scores={
                "openai_evals": {
                    "available": False,
                    "error": "timeout",
                    "aligned": False,
                    "score": 0.2,
                }
            },
        ),
    ]

    summary = summarize("regression", scores, cfg, external_scorers=["openai_evals"])
    assert summary.scenario_count == 2
    assert summary.external_scoring_enabled is True
    assert summary.external_error_count == 1
    assert "openai_evals" in summary.external_summary
    assert summary.external_summary["openai_evals"]["avg_score"] == 0.5
    assert summary.external_summary["openai_evals"]["avg_aligned"] == 0.5
    assert summary.gate_passed is False
