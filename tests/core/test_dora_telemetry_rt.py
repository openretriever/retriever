import json
from pathlib import Path

from retriever.rt.backend.dora.telemetry import CONTRACT_VERSION, DoraTelemetryWriter


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def test_telemetry_writer_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("RETRIEVER_DORA_TELEMETRY_JSONL", raising=False)
    monkeypatch.delenv("RETRIEVER_DORA_TAP_JSONL", raising=False)
    path = tmp_path / "telemetry.jsonl"

    writer = DoraTelemetryWriter()
    assert writer.enabled is False
    wrote = writer.emit(event="Dora.Input", node_id="node_a", payload={"input": "tick"})
    assert wrote is False
    assert path.exists() is False


def test_telemetry_writer_uses_canonical_env_var(monkeypatch, tmp_path):
    path = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv("RETRIEVER_DORA_TELEMETRY_JSONL", str(path))
    monkeypatch.setenv("RETRIEVER_RUN_ID", "run_test")
    monkeypatch.setenv("RETRIEVER_PIPELINE_ID", "demo.pipeline")

    writer = DoraTelemetryWriter()
    assert writer.enabled is True
    assert writer.emit(event="Dora.Input", node_id="node_a", payload={"input": "tick"}) is True
    assert path.exists()

    rows = _read_jsonl(path)
    assert len(rows) == 1
    row = rows[0]
    assert row["contract_version"] == CONTRACT_VERSION
    assert row["event"] == "Dora.Input"
    assert row["run_id"] == "run_test"
    assert row["pipeline_id"] == "demo.pipeline"
    assert row["node_id"] == "node_a"
    assert row["payload"]["input"] == "tick"


def test_telemetry_writer_supports_legacy_alias(monkeypatch, tmp_path):
    monkeypatch.delenv("RETRIEVER_DORA_TELEMETRY_JSONL", raising=False)
    path = tmp_path / "telemetry_alias.jsonl"
    monkeypatch.setenv("RETRIEVER_DORA_TAP_JSONL", str(path))

    writer = DoraTelemetryWriter()
    assert writer.enabled is True
    assert writer.emit(event="Dora.Output", node_id="node_b", payload={"port": "value"}) is True
    rows = _read_jsonl(path)
    assert len(rows) == 1
    assert rows[0]["event"] == "Dora.Output"
