from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import pytest

from retriever.config import RecordConfig
from retriever.pipeline_registry import build_ir, list_pipelines
from retriever.recording import build_recording_sink
from retriever.rt.stepper import StepResult
from retriever.tutorials.perception import (
    CameraSource,
    ColorDetector,
    CameraData,
    Image,
    emit_replay_finished,
    emit_replay_started,
    load_camera_buffer_from_recording,
)


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        rows.append(json.loads(text))
    return rows


def test_tutorial_perception_pipeline_registers_and_builds_ir() -> None:
    pipelines = list_pipelines()
    assert "tutorial.perception" in pipelines

    ir = build_ir(
        "tutorial.perception",
        use_real_camera=False,
        show_window=False,
        min_confidence=0.55,
        camera_width=320,
        camera_height=240,
        camera_index=2,
    )
    assert ir.metadata.name == "tutorial.perception"
    assert len(list(ir.nodes or [])) == 3
    edge_ports = {(str(edge.source.port), str(edge.destination.port)) for edge in list(ir.edges or [])}
    assert ("image", "image") in edge_ports
    assert ("detections", "detections") in edge_ports

    nodes = {node.id: node for node in ir.nodes}
    assert nodes["CameraSource"].init_config == {
        "use_real_camera": False,
        "width": 320,
        "height": 240,
        "camera_index": 2,
    }
    assert nodes["ColorDetector"].init_config == {"min_confidence": 0.55}
    assert nodes["DisplayFlow"].init_config == {"display": "stdout"}


def test_tutorial_perception_emits_semantic_camera_and_detection_events(
    tmp_path: Path, monkeypatch
) -> None:
    stream_path = tmp_path / "semantic_stream.jsonl"
    monkeypatch.setenv("RETRIEVER_RUNTIME_STREAM_JSONL", str(stream_path))
    monkeypatch.setenv("RETRIEVER_RUN_ID", "run_perception_rt")
    monkeypatch.setenv("RETRIEVER_PIPELINE_ID", "tutorial.perception")

    camera = CameraSource(use_real_camera=False, width=160, height=120)
    camera.reset()
    sample = camera.step(None)

    detector = ColorDetector(min_confidence=0.4)
    detector.step(sample)

    rows = _read_jsonl(stream_path)
    events = [str(row.get("event")) for row in rows]
    assert "Perception.CameraMode" in events
    assert "Perception.FrameCaptured" in events
    assert "Perception.Detections" in events

    camera_mode = next(row for row in rows if str(row.get("event")) == "Perception.CameraMode")
    assert str((camera_mode.get("payload") or {}).get("mode")) in {"mock", "real"}

    detections = next(row for row in rows if str(row.get("event")) == "Perception.Detections")
    payload = detections.get("payload") or {}
    assert int(payload.get("frame_id", 0) or 0) >= 1
    assert isinstance(payload.get("labels"), list)
    assert "empty" in payload


def test_tutorial_perception_replay_helpers_emit_semantic_events(
    tmp_path: Path, monkeypatch
) -> None:
    stream_path = tmp_path / "semantic_replay.jsonl"
    monkeypatch.setenv("RETRIEVER_RUNTIME_STREAM_JSONL", str(stream_path))
    monkeypatch.setenv("RETRIEVER_RUN_ID", "run_perception_replay")
    monkeypatch.setenv("RETRIEVER_PIPELINE_ID", "tutorial.perception")

    emit_replay_started(recording_path="logs/perception.mcap", frame_count_estimate=10)
    emit_replay_finished(recording_path="logs/perception.mcap", steps_completed=7)

    rows = _read_jsonl(stream_path)
    events = [str(row.get("event")) for row in rows]
    assert events == ["Perception.ReplayStarted", "Perception.ReplayFinished"]
    assert str((rows[0].get("payload") or {}).get("recording_path")) == "logs/perception.mcap"
    assert int((rows[1].get("payload") or {}).get("steps_completed", 0) or 0) == 7


def test_tutorial_perception_loads_camera_buffer_from_rrd(tmp_path: Path) -> None:
    import numpy as np

    pytest.importorskip("rerun")

    path = tmp_path / "perception.rrd"
    frame = np.zeros((3, 4, 3), dtype=np.uint8)
    frame[:, :, 0] = 10
    frame[:, :, 1] = 20
    frame[:, :, 2] = 30

    sink = build_recording_sink(RecordConfig(path=path), app_id="perception_test")
    sink.open()
    try:
        sink.write_step(
            StepResult(
                now=1.25,
                executed=["CameraSource_test"],
                inputs={},
                outputs={
                    "CameraSource_test": CameraData(
                        image=Image(frame=frame, frame_id=11),
                        mode="mock",
                    )
                },
            ),
            0,
        )
    finally:
        sink.close()

    buffer = load_camera_buffer_from_recording(path)
    assert len(buffer) == 1
    _ts, camera = buffer[0]
    assert camera.image.frame_id == 11
    assert camera.mode == "mock"
    assert camera.image.frame.shape == (3, 4, 3)
    assert int(camera.image.frame[0, 0, 1]) == 20


def test_tutorial_record_replay_cli_roundtrip_emits_rrd_and_mcap(tmp_path: Path) -> None:
    pytest.importorskip("rerun")

    mod = importlib.import_module("examples.tutorial.c_debug_and_replay.04_record_replay_perception")

    rrd_path = tmp_path / "perception.rrd"
    mcap_path = tmp_path / "perception.mcap"

    record_args = argparse.Namespace(
        out=rrd_path,
        replay_out=mcap_path,
        camera_index=0,
        stream=False,
        steps=3,
        dt=0.01,
        sleep=0.0,
    )
    mod.cmd_record(record_args)

    assert rrd_path.exists()
    assert rrd_path.stat().st_size > 0
    assert mcap_path.exists()
    assert mcap_path.stat().st_size > 0

    replay_args = argparse.Namespace(
        recording=rrd_path,
        steps=3,
        dt=0.01,
        sleep=0.0,
        visualize="stdout",
    )
    mod.cmd_replay(replay_args)

    replay_args.recording = mcap_path
    mod.cmd_replay(replay_args)
