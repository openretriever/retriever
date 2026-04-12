"""Data spec multistream join tutorial.

Covers:
1) explicit bridge from runtime EventBuffer to retriever.types.data
2) deterministic event-time joins (`exact`, `latest_before`, `window`)
3) processing-time profile helpers (`latest`, `hold`, `window_agg`)

Run:
  pixi run python -m examples.tutorial.e_resource_and_sync.07_data_multistream_join
"""

from __future__ import annotations

from pathlib import Path

from retriever.types.data import (
    Event,
    EventBuffer,
    JoinPolicy,
    StreamId,
    WindowPolicy,
    align_exact,
    align_latest_before,
    align_window,
    from_runtime_event_buffer,
    hold,
    latest,
    to_runtime_event_buffer,
    window_agg,
)
from retriever.flow.types import EventBuffer as RuntimeEventBuffer

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


def _evt(stream: str, t_ns: int, seq: int, value: float) -> Event[float]:
    return Event(
        stream_id=StreamId(stream),
        event_time_ns=t_ns,
        ingest_time_ns=t_ns,
        seq=seq,
        value=value,
        type_name="float",
    )


def _pairs(buffer: EventBuffer[tuple[float, float]]) -> list[list[str]]:
    rows = []
    for event in buffer.sorted():
        left, right = event.value
        rows.append([str(event.event_time_ns), f"{left:.1f}", f"{right:.1f}"])
    return rows


def main() -> None:
    out_path = Path("logs/tutorial_data_spec/tut038_multistream_join.json")

    runtime_camera = RuntimeEventBuffer([(1.0, 10.0), (2.0, 20.0), (3.0, 30.0)])
    runtime_joint = RuntimeEventBuffer([(2.0, 100.0), (3.02, 110.0)])

    camera = from_runtime_event_buffer(runtime_camera, stream_id="camera")
    joint = from_runtime_event_buffer(runtime_joint, stream_id="joint")

    exact = align_exact(camera, joint, output_stream_id="join.exact")
    latest_before = align_latest_before(
        camera,
        joint,
        max_delta_ns=50_000_000,
        output_stream_id="join.latest_before",
    )
    windowed = align_window(camera, joint, window_ns=25_000_000, output_stream_id="join.window")

    sensor = EventBuffer((_evt("sensor", 100, 0, 1.0), _evt("sensor", 200, 1, 2.0), _evt("sensor", 280, 2, 4.0)))
    latest_value = latest(sensor)
    hold_value = hold(sensor, now_ns=250, last_value=-1.0)
    mean_value = window_agg(sensor, now_ns=300, policy=WindowPolicy(duration_ns=200, agg="mean"))

    print("=== Exact Join ===")
    print(format_table(["event_time_ns", "camera", "joint"], _pairs(exact)))
    print("\n=== Latest-Before Join ===")
    print(format_table(["event_time_ns", "camera", "joint"], _pairs(latest_before)))
    print("\n=== Window Join ===")
    print(format_table(["event_time_ns", "camera", "joint"], _pairs(windowed)))
    print("\n=== Processing-Time Sampling ===")
    print(format_table(["latest", "hold@250ns", "window_mean@300ns"], [[f"{latest_value:.1f}", f"{hold_value:.1f}", f"{mean_value:.3f}"]]))

    write_json(
        out_path,
        {
            "generated_at": utc_now_iso(),
            "runtime_roundtrip": to_runtime_event_buffer(camera) == list(runtime_camera),
            "exact_join_rows": len(exact),
            "latest_before_rows": len(latest_before),
            "window_rows": len(windowed),
            "latest": latest_value,
            "hold": hold_value,
            "window_mean": mean_value,
        },
    )
    print(f"\n[artifact] wrote {out_path}")


if __name__ == "__main__":
    main()
