"""Recording uses Rerun for visualization and MCAP for typed replay."""
from dataclasses import dataclass

import numpy as np
import pytest

from retriever.config import RecordConfig
from retriever.flow import io
from retriever.recording import build_recording_sink, open_recording_reader
from retriever.rt.stepper import StepResult


@io
@dataclass
class Sample:
    value: int | None = None
    image: np.ndarray | None = None


def test_rrd_reader_explains_mcap_replay_path(tmp_path):
    with pytest.raises(ValueError, match="MCAP"):
        open_recording_reader(tmp_path / "session.rrd")


def test_record_visualization_and_read_typed_mcap_without_rerun(tmp_path, monkeypatch):
    pytest.importorskip("rerun")
    pytest.importorskip("mcap")
    path = tmp_path / "session.mcap"
    visual = tmp_path / "session.rrd"
    sink = build_recording_sink(RecordConfig(path=path, mirrors=(visual,)), app_id="recording-test")
    pixels = np.arange(6, dtype=np.uint8).reshape(2, 3)
    sink.open()
    try:
        for index, (stamp, value) in enumerate([(2.125, Sample(3, pixels)), (2.75, None)]):
            sink.write_step(StepResult(now=stamp, executed=["Source"], inputs={}, outputs={"Source": value}), index)
    finally:
        sink.close()
    assert visual.stat().st_size > 0
    monkeypatch.setitem(__import__("sys").modules, "rerun", None)
    reader = open_recording_reader(path)
    rows = reader.read_node_stream("Source", output_type=Sample)
    assert [t for t, _ in rows] == [2.125, 2.75]
    assert rows[0][1].value == 3
    np.testing.assert_array_equal(rows[0][1].image, pixels)
    assert rows[1][1] is None
    assert reader.get_stream_spec("Source").io_kind == "output"
