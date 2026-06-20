import json
from pathlib import Path

import pytest

from vaanieval.config import EvalConfig, _parse_scorer_list, _read_config_file, load_config


def test_parse_scorer_list_from_string_and_list() -> None:
    assert _parse_scorer_list("openai_evals, custom, ,") == ["openai_evals", "custom"]
    assert _parse_scorer_list(["openai_evals", "", " custom "]) == ["openai_evals", "custom"]
    assert _parse_scorer_list(None) == []


def test_read_config_file_json_yaml_and_errors(tmp_path: Path) -> None:
    json_path = tmp_path / "cfg.json"
    json_path.write_text(json.dumps({"elevenlabs_api_key": "k"}), encoding="utf-8")
    assert _read_config_file(str(json_path))["elevenlabs_api_key"] == "k"

    yaml_path = tmp_path / "cfg.yaml"
    yaml_path.write_text("elevenlabs_agent_id: a\n", encoding="utf-8")
    assert _read_config_file(str(yaml_path))["elevenlabs_agent_id"] == "a"

    empty_yaml = tmp_path / "empty.yml"
    empty_yaml.write_text("", encoding="utf-8")
    assert _read_config_file(str(empty_yaml)) == {}

    bad_root = tmp_path / "bad.json"
    bad_root.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError):
        _read_config_file(str(bad_root))

    unsupported = tmp_path / "cfg.txt"
    unsupported.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        _read_config_file(str(unsupported))

    with pytest.raises(FileNotFoundError):
        _read_config_file(str(tmp_path / "missing.yaml"))


def test_from_file_merges_with_env_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "env-k")
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "env-a")
    monkeypatch.setenv("VAANIEVAL_EXTERNAL_SCORERS", "openai_evals")
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")

    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(
        json.dumps(
            {
                "elevenlabs_agent_id": "file-a",
                "tsr_threshold": 0.91,
                "enabled_external_scorers": ["openai_evals", "custom"],
            }
        ),
        encoding="utf-8",
    )

    cfg = EvalConfig.from_file(str(cfg_path))
    assert cfg.elevenlabs_api_key == "env-k"
    assert cfg.elevenlabs_agent_id == "file-a"
    assert cfg.tsr_threshold == 0.91
    assert cfg.enabled_external_scorers == ["openai_evals", "custom"]


def test_ensure_valid_checks_required_keys() -> None:
    with pytest.raises(ValueError):
        EvalConfig(elevenlabs_api_key="", elevenlabs_agent_id="a").ensure_valid()

    with pytest.raises(ValueError):
        EvalConfig(elevenlabs_api_key="k", elevenlabs_agent_id="").ensure_valid()

    with pytest.raises(ValueError):
        EvalConfig(
            elevenlabs_api_key="k",
            elevenlabs_agent_id="a",
            enabled_external_scorers=["openai_evals"],
            openai_api_key="",
        ).ensure_valid()

    EvalConfig(
        elevenlabs_api_key="k",
        elevenlabs_agent_id="a",
        enabled_external_scorers=["openai_evals"],
        openai_api_key="ok",
    ).ensure_valid()


def test_load_config_creates_output_dir_and_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VAANIEVAL_EXTERNAL_SCORERS", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    cfg_path = tmp_path / "config.yaml"
    out_dir = tmp_path / "reports"
    cfg_path.write_text(
        "\n".join(
            [
                "elevenlabs_api_key: test-k",
                "elevenlabs_agent_id: test-a",
                f"output_dir: {out_dir.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_config(str(cfg_path))
    assert loaded.elevenlabs_api_key == "test-k"
    assert out_dir.exists()
