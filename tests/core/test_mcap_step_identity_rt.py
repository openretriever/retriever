"""A session's step metadata, rather than timestamp proximity, owns its outputs."""

import json

import pytest

from retriever.lib.mcap import MCAPReader, MCAPWriter
from retriever.rt.stepper import StepResult

Writer = pytest.importorskip("mcap.writer").Writer


def read_steps(path):
    with MCAPReader(path) as reader:
        return reader.read_all()


@pytest.mark.parametrize(
    "times",
    [
        [0.1, 0.2, 0.3],
        [0.004, 0.008, 0.012],
        [0.001, 0.002, 0.003],
        [0.0005, 0.001, 0.0015],
        [0.0001, 0.0002, 0.0003],
        [0.1, 0.1, 0.2],
        [0.3, 0.1, 0.2],
    ],
    ids=["100ms", "4ms", "1ms", "500us", "100us", "same_time", "clock_reversal"],
)
def test_session_keeps_each_steps_outputs(tmp_path, times):
    path = tmp_path / "session.mcap"
    expected = []
    with MCAPWriter(path) as writer:
        for index, now in enumerate(times):
            outputs = {"camera": {"value": index}, "controller": {"value": 10 * index}}
            result = StepResult(
                now=now, executed=list(outputs), inputs={}, outputs=outputs
            )
            writer.write_step(result, index)
            expected.append(
                {
                    "step": index,
                    "now": now,
                    "executed": result.executed,
                    "inputs": {},
                    "outputs": outputs,
                }
            )

    assert read_steps(path) == expected
    # The per-node API already retained the values; this is a session join regression.
    with MCAPReader(path) as reader:
        stream = reader.read_node_stream("camera")
    assert stream == sorted(
        [(int(now * 1e9) / 1e9, {"value": index}) for index, now in enumerate(times)],
        key=lambda item: item[0],
    )


@pytest.mark.parametrize("middle", [{"camera": None}, {"camera": {"value": None}}, {}])
def test_session_preserves_missing_outputs_and_empty_steps(tmp_path, middle):
    path = tmp_path / "missing.mcap"
    outputs = [{"camera": {"value": 0}}, middle, {"camera": {"value": 2}}]
    with MCAPWriter(path) as writer:
        for index, output in enumerate(outputs):
            writer.write_step(
                StepResult(now=0.1, executed=list(output), inputs={}, outputs=output),
                index,
            )
    steps = read_steps(path)
    assert [row["step"] for row in steps] == [0, 1, 2]
    assert [row["outputs"] for row in steps] == outputs


def write_messages(path, messages):
    """Build raw MCAP messages, including files the session writer would not emit."""
    with path.open("wb") as file:
        writer = Writer(file, chunk_size=1)
        writer.start()
        schema = writer.register_schema("retriever.test", "jsonschema", b"{}")
        channels = {}
        for topic, now_ns, payload in messages:
            if topic not in channels:
                channels[topic] = writer.register_channel(topic, "json", schema)
            writer.add_message(
                channel_id=channels[topic],
                log_time=now_ns,
                data=json.dumps(payload).encode(),
                publish_time=now_ns,
            )
        writer.finish()


def metadata(index=0, now=0.1):
    return (
        "/retriever/step",
        int(now * 1e9),
        {"step": index, "now": now, "executed": ["camera"]},
    )


def payload(value=0, now_ns=100_000_000, kind="output"):
    return (f"/retriever/flows/camera/{kind}", now_ns, {"value": value})


def test_session_reads_equal_time_steps_across_chunks_and_keeps_inputs(tmp_path):
    path = tmp_path / "chunked.mcap"
    write_messages(
        path,
        [
            metadata(),
            payload(kind="input"),
            payload(),
            ("/unrelated/output", 100_000_000, {"value": 999}),
            metadata(index=1),
            payload(1, kind="input"),
            payload(1),
        ],
    )
    steps = read_steps(path)
    assert [row["step"] for row in steps] == [0, 1]
    for kind in ("inputs", "outputs"):
        assert [row[kind] for row in steps] == [
            {"camera": {"value": 0}},
            {"camera": {"value": 1}},
        ]


@pytest.mark.parametrize(
    ("messages", "error"),
    [
        ([payload(), metadata()], "no matching preceding step metadata"),
        (
            [metadata(), payload(now_ns=100_000_001)],
            "no matching preceding step metadata",
        ),
        ([metadata(), payload(), metadata()], "Duplicate Retriever step index"),
        ([metadata(), payload(), payload(1)], "Duplicate Retriever payload"),
    ],
    ids=["orphan", "wrong_timestamp", "duplicate_step", "duplicate_payload"],
)
def test_session_rejects_ambiguous_payloads(tmp_path, messages, error):
    path = tmp_path / "invalid.mcap"
    write_messages(path, messages)
    with pytest.raises(ValueError, match=error):
        read_steps(path)
