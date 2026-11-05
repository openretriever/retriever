"""Lossless recording values and SDK-dependent RRD readback."""
from dataclasses import dataclass, fields, is_dataclass
from typing import Any

import numpy as np
import pytest

from retriever.config import RecordConfig
from retriever.recording import build_recording_sink, open_recording_reader
from retriever.rt.stepper import StepResult


@dataclass
class ArrayValue:
    array: np.ndarray


@dataclass
class NestedValue:
    child: ArrayValue
    raw: bytes


CASES = [
    (NestedValue(ArrayValue(np.array([1.0, 2.0])), b"\x00\xff"), NestedValue),
    ((np.array([1, 2], dtype=np.int16), b"tuple"), tuple[np.ndarray, bytes]),
    ({"array": np.array([3], dtype=np.uint32), "raw": b"dict"}, dict[str, Any]),
    (np.arange(18, dtype=np.uint8).reshape(2, 3, 3), np.ndarray),
    (b"\x00\x01\xff", bytes),
    (np.empty((0, 3), dtype=np.float32), np.ndarray),
]


def assert_same(actual, expected):
    if isinstance(expected, np.ndarray):
        assert actual.dtype == expected.dtype
        assert actual.shape == expected.shape
        np.testing.assert_array_equal(actual, expected)
    elif is_dataclass(expected):
        assert type(actual) is type(expected)
        for field in fields(expected):
            assert_same(getattr(actual, field.name), getattr(expected, field.name))
    elif isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_same(actual[key], expected[key])
    elif isinstance(expected, tuple):
        assert isinstance(actual, tuple)
        for left, right in zip(actual, expected, strict=True):
            assert_same(left, right)
    else:
        assert actual == expected


@pytest.mark.parametrize("value,output_type", CASES,
                         ids=["nested", "tuple", "dict", "image", "bytes", "empty"])
@pytest.mark.parametrize("suffix", [".mcap", ".rrd"])
def test_recording_supported_values_roundtrip(tmp_path, suffix, value, output_type):
    rr = pytest.importorskip("rerun")
    path = tmp_path / ("values" + suffix)
    sink = build_recording_sink(RecordConfig(path=path), app_id="value-roundtrip")
    sink.open()
    try:
        for index, stamp in enumerate([0.1, 0.37]):
            sink.write_step(StepResult(now=stamp, executed=["Source"], inputs={},
                                       outputs={"Source": value}), index)
    finally:
        sink.close()
    assert path.stat().st_size > 0
    assert not path.with_suffix(".mcap" if suffix == ".rrd" else ".rrd").exists()
    if suffix == ".rrd" and not hasattr(rr, "dataframe"):
        with pytest.raises(RuntimeError) as error:
            open_recording_reader(path)
        message = str(error.value)
        assert rr.__version__ in message
        assert str(path) in message
        assert "RecordConfig" in message and "mirrors=" in message
        assert "rerun-sdk<0.29" in message
        return
    rows = open_recording_reader(path).read_node_stream("Source", output_type=output_type)
    assert [stamp for stamp, _ in rows] == pytest.approx([0.1, 0.37])
    for _, actual in rows:
        assert_same(actual, value)


def test_rrd_contains_visual_and_replay_entity_paths(tmp_path, monkeypatch):
    rr = pytest.importorskip("rerun")
    logged = []
    real_log = rr.log

    def capture(path, *args, **kwargs):
        logged.append(path)
        return real_log(path, *args, **kwargs)

    monkeypatch.setattr(rr, "log", capture)
    path = tmp_path / "entities.rrd"
    sink = build_recording_sink(RecordConfig(path=path), app_id="entities")
    sink.open()
    try:
        sink.write_step(StepResult(now=0.1, executed=["Source"], inputs={},
                                   outputs={"Source": 7}), 0)
    finally:
        sink.close()
    assert "flows/Source/output" in logged
    assert "retriever_recording/flows/Source/output/payload" in logged
    assert "retriever_recording/flows/Source/spec" in logged
    assert path.stat().st_size > 0


def test_mcap_restores_legacy_array_and_current_lossless_markers():
    from retriever.lib.mcap import _deserialize_dataclass, _restore_numpy, MCAPWriter

    original = {"image": np.empty((0, 3), dtype=np.float32), "raw": b"\x00\xff"}
    encoded = MCAPWriter("unused.mcap")._to_json(original)
    restored = _deserialize_dataclass(encoded)
    assert_same(restored, original)
    old = {"__numpy__": True, "data": [], "dtype": "float32", "shape": [0, 3]}
    assert_same(_restore_numpy(old), original["image"])
