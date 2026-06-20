from __future__ import annotations

import json
import runpy
from dataclasses import asdict
from pathlib import Path

from vaanieval import api, cli
from vaanieval.config import EvalConfig
from vaanieval.models import EvalRunResult, RunSummary, ScenarioExecution, ScenarioScore


def _sample_result() -> EvalRunResult:
    return EvalRunResult(
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
                category="smoke",
                passed=True,
                task_success=True,
                unresolved_turn=False,
                hallucination=False,
                fallback_good=True,
            )
        ],
        execution=[ScenarioExecution(scenario_id="s1", category="smoke")],
    )


def test_api_public_runs_delegate_to_internal(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_run(**kwargs):
        calls.append((kwargs["run_type"], kwargs["dataset"]))
        return _sample_result()

    monkeypatch.setattr(api, "_run", fake_run)

    api.run_smoke()
    api.run_regression()
    api.run_custom("custom.yaml")

    run_types = [item[0] for item in calls]
    assert run_types == ["smoke", "regression", "custom"]
    assert calls[2][1] == "custom.yaml"


def test_api_internal_run_applies_overrides(monkeypatch, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    cfg = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="a", output_dir=str(tmp_path / "base"))
    result = _sample_result()

    monkeypatch.setattr(api, "load_config", lambda config_path=None: cfg)
    monkeypatch.setattr(api, "load_scenarios", lambda _dataset: [ScenarioExecution(scenario_id="s", category="c")])
    monkeypatch.setattr(api, "evaluate_scenarios", lambda **_kwargs: result)
    monkeypatch.setattr(api, "write_json_report", lambda *_args: Path("summary.json"))
    monkeypatch.setattr(api, "write_markdown_report", lambda *_args: Path("report.md"))

    final = api._run(
        dataset="dataset.yaml",
        config_path="config.yaml",
        output_dir=str(out_dir),
        run_type="smoke",
        external_scorers=["noop"],
        openai_api_key="openai-k",
        openai_model="gpt-x",
    )

    assert final.summary.scenario_count == 1
    assert cfg.output_dir == str(out_dir)
    assert cfg.enabled_external_scorers == ["noop"]
    assert cfg.openai_api_key == "openai-k"
    assert cfg.openai_model == "gpt-x"
    assert out_dir.exists()


def test_default_dataset_path_contains_tier_and_filename() -> None:
    path = api._default_dataset_path("smoke", "smoke_core.yaml")
    assert "datasets" in path
    assert "smoke" in path
    assert path.endswith("smoke_core.yaml")


def test_cli_smoke_and_custom(monkeypatch, capsys) -> None:
    result = _sample_result()
    monkeypatch.setattr(cli, "run_smoke", lambda **_kwargs: result)
    monkeypatch.setattr(cli, "run_regression", lambda **_kwargs: result)
    monkeypatch.setattr(cli, "run_custom", lambda **_kwargs: result)

    monkeypatch.setattr(
        "sys.argv",
        [
            "vaanieval",
            "smoke",
            "--external-scorers",
            "noop,openai_evals",
            "--openai-model",
            "gpt-4o-mini",
            "--tsr-threshold",
            "0.92",
        ],
    )
    cli.main()
    printed = capsys.readouterr().out
    assert json.loads(printed)["run_type"] == "smoke"

    monkeypatch.setattr("sys.argv", ["vaanieval", "custom", "--dataset", "x.yaml"])
    cli.main()
    printed = capsys.readouterr().out
    assert json.loads(printed)["scenario_count"] == asdict(result.summary)["scenario_count"]


def test_cli_helpers_and_main_entrypoint(monkeypatch) -> None:
    cli._set_env("VAANIEVAL_TEST_KEY", "1")
    assert cli._parse_scorer_csv(None) is None
    assert cli._parse_scorer_csv("noop, openai_evals") == ["noop", "openai_evals"]

    called = {"count": 0}
    monkeypatch.setattr("vaanieval.cli.main", lambda: called.__setitem__("count", called["count"] + 1))
    runpy.run_module("vaanieval.__main__", run_name="__main__")
    assert called["count"] == 1
