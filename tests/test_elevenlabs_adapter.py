from __future__ import annotations

from types import SimpleNamespace

from vaanieval.adapters.elevenlabs_adapter import (
    ElevenLabsSimulationAdapter,
    _extract_latency,
    _model_to_dict,
)
from vaanieval.config import EvalConfig
from vaanieval.models import EvalScenario


def test_extract_latency_and_model_to_dict() -> None:
    assert _extract_latency(None) == (None, {})

    metrics_obj = SimpleNamespace(
        metrics={
            "stage1": SimpleNamespace(elapsed_time=0.1),
            "stage2": SimpleNamespace(elapsed_time=0.2),
        }
    )
    total_ms, raw = _extract_latency(metrics_obj)
    assert total_ms == 300.0
    assert raw["stage1"] == 100.0

    assert _model_to_dict(None) == {}
    assert _model_to_dict({"a": 1}) == {"a": 1}
    assert _model_to_dict(SimpleNamespace(model_dump=lambda: {"x": 1})) == {"x": 1}
    assert _model_to_dict(SimpleNamespace(dict=lambda: {"y": 2})) == {"y": 2}
    assert _model_to_dict("abc") == {"value": "abc"}


def test_parse_turns_maps_turn_fields() -> None:
    adapter = ElevenLabsSimulationAdapter.__new__(ElevenLabsSimulationAdapter)
    turns = [
        SimpleNamespace(
            role="agent",
            message="hello",
            interrupted=True,
            time_in_call_secs=3,
            conversation_turn_metrics=SimpleNamespace(
                metrics={"decode": SimpleNamespace(elapsed_time=0.05)}
            ),
        )
    ]

    parsed = adapter._parse_turns(turns)
    assert len(parsed) == 1
    assert parsed[0].role == "agent"
    assert parsed[0].message == "hello"
    assert parsed[0].interrupted is True
    assert parsed[0].time_in_call_secs == 3
    assert parsed[0].latency_ms == 50.0


def test_run_scenario_success_and_retry_failure(monkeypatch) -> None:
    cfg = EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="agent-1", max_retries=1)
    scenario = EvalScenario(id="s1", category="smoke", user_message="hi", max_turns=3)

    monkeypatch.setattr("vaanieval.adapters.elevenlabs_adapter.AgentConfig", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(
        "vaanieval.adapters.elevenlabs_adapter.ConversationSimulationSpecification",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    class GoodClient:
        def __init__(self):
            self.conversational_ai = SimpleNamespace(
                agents=SimpleNamespace(simulate_conversation=self._simulate)
            )

        def _simulate(self, **_kwargs):
            return SimpleNamespace(
                simulated_conversation=[SimpleNamespace(role="agent", message="ok")],
                analysis=SimpleNamespace(model_dump=lambda: {"status": "ok"}),
            )

    monkeypatch.setattr("vaanieval.adapters.elevenlabs_adapter.ElevenLabs", lambda api_key: GoodClient())
    good_adapter = ElevenLabsSimulationAdapter(cfg)
    result = good_adapter.run_scenario(scenario)
    assert result.adapter_error is None
    assert result.analysis["status"] == "ok"
    assert "simulation_call_duration_ms" in result.analysis

    class BadClient:
        def __init__(self):
            self.calls = 0
            self.conversational_ai = SimpleNamespace(
                agents=SimpleNamespace(simulate_conversation=self._simulate)
            )

        def _simulate(self, **_kwargs):
            self.calls += 1
            raise RuntimeError("transient")

    bad_client = BadClient()
    monkeypatch.setattr("vaanieval.adapters.elevenlabs_adapter.ElevenLabs", lambda api_key: bad_client)
    bad_adapter = ElevenLabsSimulationAdapter(cfg)
    bad_result = bad_adapter.run_scenario(scenario)
    assert bad_result.adapter_error is not None
    assert "transient" in bad_result.adapter_error
    assert bad_client.calls == cfg.max_retries + 1
