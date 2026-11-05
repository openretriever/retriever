"""Read and replay the original MCAP session layout without source checkouts."""

import json
from dataclasses import dataclass

import numpy as np
import pytest
from mcap.writer import Writer
from mcap.reader import make_reader

from retriever.flow import Flow, Latest, Pipeline, Rate, io
from retriever.recording import open_recording_reader, build_recording_sink
from retriever.config import RecordConfig
from retriever.lib.mcap import MCAPWriter
from retriever.rt.stepper import StepResult


@io
@dataclass
class LegacySample:
    value: int
    image: np.ndarray


class LegacySource(Flow[None, LegacySample]):
    def step(self, _):
        return LegacySample(value=-1, image=np.zeros((1,), dtype=np.uint8))


class Increment(Flow[LegacySample, LegacySample]):
    def step(self, value):
        return LegacySample(value=value.value + 100, image=value.image)


def _write_legacy_session(path, node_id, samples):
    """Frozen writer layout from main b0d7663 and 0.0.1 source e9ad0c6.

    Keep registration order and JSON spacing so complete files can be compared.
    This fixture covers Sample outputs without extra image visualization topics.
    """
    with path.open("wb") as stream:
        writer = Writer(stream)
        writer.start()
        channels = {}

        def channel(topic, name, schema):
            if topic not in channels:
                schema_id = writer.register_schema(name, "jsonschema", schema)
                channels[topic] = writer.register_channel(topic, "json", schema_id)
            return channels[topic]

        for index, (stamp, sample) in enumerate(samples):
            timestamp_ns = int(stamp * 1e9)
            step_schema = json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "step": {"type": "integer"},
                        "now": {"type": "number"},
                        "executed": {"type": "array", "items": {"type": "string"}},
                    },
                }
            ).encode("utf-8")
            step_channel = channel("/retriever/step", "retriever.Step", step_schema)
            metadata = {"step": index, "now": stamp, "executed": [node_id]}
            writer.add_message(
                step_channel,
                timestamp_ns,
                json.dumps(metadata).encode("utf-8"),
                timestamp_ns,
            )
            output_channel = channel(
                f"/retriever/flows/{node_id}/output",
                f"retriever.{node_id}",
                json.dumps({"type": "object"}).encode("utf-8"),
            )
            payload = {
                "value": sample.value,
                "image": {
                    "__numpy__": True,
                    "shape": list(sample.image.shape),
                    "dtype": str(sample.image.dtype),
                    "data": sample.image.tolist(),
                },
            }
            writer.add_message(
                output_channel,
                timestamp_ns,
                json.dumps(payload).encode("utf-8"),
                timestamp_ns,
            )
        writer.finish()


def _read_with_frozen_legacy_reader(path):
    """Frozen read/decode behavior shared by b0d7663 and 0.0.1 e9ad0c6."""

    def restore(value):
        if isinstance(value, dict):
            if value.get("__numpy__"):
                return np.array(value["data"], dtype=value["dtype"])
            return {key: restore(item) for key, item in value.items()}
        if isinstance(value, list):
            return [restore(item) for item in value]
        return value

    rows = []
    with path.open("rb") as stream:
        reader = make_reader(stream)
        for schema, _, message in reader.iter_messages(
            topics=["/retriever/flows/Source/output"]
        ):
            assert schema.name.startswith("retriever.")
            try:
                value = restore(json.loads(message.data.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(
                    f"Legacy pickled MCAP payload for schema `{schema.name}` is no longer supported. "
                    "Re-record this artifact with the current Retriever build."
                ) from exc
            rows.append((message.log_time / 1e9, value))
    return rows


@pytest.mark.parametrize("shape", [(2, 3, 3), (0, 3)])
def test_original_writer_file_reads_and_replays_with_current_reader(tmp_path, shape):
    pipe = Pipeline("legacy_session")
    source = LegacySource() @ Rate(hz=10)
    increment = Increment() @ Rate(hz=10)
    pipe.connect(source, increment, sync=Latest())
    path = tmp_path / "legacy.mcap"
    image = np.arange(int(np.prod(shape)), dtype=np.uint8).reshape(shape)
    samples = [
        (0.1, LegacySample(value=7, image=image)),
        (0.37, LegacySample(value=8, image=image)),
    ]
    _write_legacy_session(path, pipe.get_node_id(source), samples)

    rows = open_recording_reader(path).read_node_stream(
        pipe.get_node_id(source), output_type=LegacySample
    )
    assert [stamp for stamp, _ in rows] == pytest.approx([0.1, 0.37])
    assert [sample.value for _, sample in rows] == [7, 8]
    for _, sample in rows:
        assert sample.image.dtype == image.dtype
        assert sample.image.shape == image.shape
        np.testing.assert_array_equal(sample.image, image)

    pipe.replay(source, path=path)
    try:
        for index, now in enumerate([0.1, 0.37]):
            result = pipe.step(now=now)
            output = result.outputs[pipe.get_node_id(increment)]
            assert output.value == 107 + index
            np.testing.assert_array_equal(output.image, image)
    finally:
        pipe.close_stepper()


def test_default_file_is_byte_identical_to_frozen_writer(tmp_path):
    original = tmp_path / "original.mcap"
    current = tmp_path / "current.mcap"
    samples = [
        (0.1, LegacySample(7, np.array([[1, 2]], dtype=np.uint8))),
        (0.37, LegacySample(8, np.array([[3, 4]], dtype=np.uint8))),
    ]
    _write_legacy_session(original, "Source", samples)
    with MCAPWriter(current) as writer:
        for index, (stamp, sample) in enumerate(samples):
            writer.write_step(
                StepResult(
                    now=stamp,
                    executed=["Source"],
                    inputs={},
                    outputs={"Source": sample},
                ),
                index,
            )
    assert current.read_bytes() == original.read_bytes()
    rows = _read_with_frozen_legacy_reader(current)
    assert [value["value"] for _, value in rows] == [7, 8]


DEFAULT_VALUES = [
    (None, b"null"),
    (True, b"true"),
    (7, b"7"),
    (1.25, b"1.25"),
    ("caf\u00e9", b'"caf\\u00e9"'),
    ([1, None], b"[1, null]"),
    ((1, 2), b"[1, 2]"),
    ({"tuple": (1, 2)}, b'{"tuple": [1, 2]}'),
    ({"__bytes__": "YWJj", "label": "data"}, b'{"__bytes__": "YWJj", "label": "data"}'),
    (
        np.array([1, 2], dtype=np.int16),
        b'{"__numpy__": true, "shape": [2], "dtype": "int16", "data": [1, 2]}',
    ),
    (
        np.empty((0, 3), dtype=np.float32),
        b'{"__numpy__": true, "shape": [0, 3], "dtype": "float32", "data": []}',
    ),
    (
        LegacySample(7, np.array([1, 2], dtype=np.uint8)),
        b'{"value": 7, "image": {"__numpy__": true, "shape": [2], "dtype": "uint8", "data": [1, 2]}}',
    ),
]


@pytest.mark.parametrize("value,expected_payload", DEFAULT_VALUES)
def test_default_output_payload_and_schema_keep_legacy_bytes(
    tmp_path, value, expected_payload
):
    path = tmp_path / "default.mcap"
    with MCAPWriter(path) as writer:
        writer.write_step(
            StepResult(
                now=0.1, executed=["Source"], inputs={}, outputs={"Source": value}
            ),
            0,
        )
    with path.open("rb") as stream:
        [(schema, channel, message)] = make_reader(stream).iter_messages(
            topics=["/retriever/flows/Source/output"]
        )
    assert schema.name == "retriever.Source"
    assert schema.encoding == "jsonschema"
    assert schema.data == b'{"type": "object"}'
    assert channel.message_encoding == "json"
    assert message.data == expected_payload
    assert message.log_time == message.publish_time == 100_000_000


def test_explicit_lossless_file_is_rejected_by_frozen_legacy_reader(tmp_path):
    path = tmp_path / "lossless.mcap"
    with MCAPWriter(path, lossless=True) as writer:
        writer.write_step(
            StepResult(
                now=0.1,
                executed=["Source"],
                inputs={},
                outputs={"Source": {"raw": b"abc", "pair": (1, 2)}},
            ),
            0,
        )
    with pytest.raises(RuntimeError, match="Legacy pickled MCAP payload"):
        _read_with_frozen_legacy_reader(path)
    rows = open_recording_reader(path).read_node_stream("Source")
    assert rows[0][1] == {"raw": b"abc", "pair": (1, 2)}


def test_record_config_routes_explicit_lossless_option(tmp_path):
    path = tmp_path / "configured.mcap"
    sink = build_recording_sink(
        RecordConfig(path=path, mcap_lossless=True), app_id="explicit-codec"
    )
    sink.open()
    try:
        sink.write_step(
            StepResult(
                now=0.1, executed=["Source"], inputs={}, outputs={"Source": b"bytes"}
            ),
            0,
        )
    finally:
        sink.close()
    assert open_recording_reader(path).read_node_stream("Source")[0][1] == b"bytes"
    with pytest.raises(RuntimeError, match="Legacy pickled MCAP payload"):
        _read_with_frozen_legacy_reader(path)
    assert not path.with_suffix(".rrd").exists()


def test_default_writer_keeps_legacy_bytes_rejection(tmp_path):
    with MCAPWriter(tmp_path / "default.mcap") as writer:
        with pytest.raises(
            TypeError, match="Unsupported value for stable MCAP recording"
        ):
            writer.write_step(
                StepResult(
                    now=0.1,
                    executed=["Source"],
                    inputs={},
                    outputs={"Source": b"bytes"},
                ),
                0,
            )
