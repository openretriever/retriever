"""
MCAP session inspection for replay diagnostics and notebook preparation.

Covers:
1) Read a recorded MCAP session and summarize timeline/stream coverage
2) Emit notebook-friendly tabular rows (`.jsonl`) for later Jupyter conversion
3) Provide a compact diagnostics artifact for release/debug evidence

Run:
  pixi run python -m examples.tutorial.c_debug_and_replay.08_mcap_session_inspection --recording logs/perception.mcap
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from retriever.lib.mcap import MCAPReader

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json, write_jsonl


def _shape_of_frame(frame: Any) -> list[int] | None:
    if hasattr(frame, "shape"):
        try:
            return [int(x) for x in frame.shape]
        except Exception:
            return None
    if isinstance(frame, list) and frame:
        # Fallback for list-backed images.
        h = len(frame)
        w = len(frame[0]) if isinstance(frame[0], list) else 0
        c = len(frame[0][0]) if w > 0 and isinstance(frame[0][0], list) else 0
        if c > 0:
            return [h, w, c]
        if w > 0:
            return [h, w]
    return None


def _frame_from_output(output: Any) -> Any | None:
    # Dataclass-like object
    if hasattr(output, "image"):
        image = getattr(output, "image", None)
        if image is None:
            return None
        if hasattr(image, "frame"):
            return getattr(image, "frame", None)
        if isinstance(image, dict):
            return image.get("frame")

    # Dict-like object
    if isinstance(output, dict):
        image = output.get("image")
        if isinstance(image, dict):
            return image.get("frame")
    return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inspect MCAP session and export notebook-friendly summaries.")
    p.add_argument(
        "--recording",
        type=Path,
        default=Path("logs/perception.mcap"),
        help="Input MCAP recording path.",
    )
    p.add_argument(
        "--summary-out",
        type=Path,
        default=Path("logs/tutorial_mcap/tut036_mcap_session_summary.json"),
        help="Summary JSON output path.",
    )
    p.add_argument(
        "--table-out",
        type=Path,
        default=Path("logs/tutorial_mcap/tut036_mcap_step_table.jsonl"),
        help="Step-table JSONL output path.",
    )
    p.add_argument(
        "--preview",
        type=int,
        default=10,
        help="How many step rows to print in console preview.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.recording.exists():
        raise FileNotFoundError(
            f"Recording not found: {args.recording}. "
            "Create one first with 'pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10'."
        )

    with MCAPReader(args.recording) as reader:
        steps = list(reader)

    if not steps:
        raise RuntimeError(f"Recording is empty: {args.recording}")

    now_values = [float(step.get("now", 0.0) or 0.0) for step in steps]
    duration_s = max(0.0, now_values[-1] - now_values[0])

    output_counts: dict[str, int] = {}
    executed_counts: dict[str, int] = {}
    frame_shapes: dict[str, list[int]] = {}

    step_rows: list[dict[str, Any]] = []
    for idx, step in enumerate(steps):
        outputs = step.get("outputs", {}) or {}
        executed = step.get("executed", []) or []
        if not isinstance(outputs, dict):
            outputs = {}
        if not isinstance(executed, list):
            executed = []

        non_null_keys: list[str] = []
        camera_nodes: list[str] = []
        for key, value in outputs.items():
            if value is None:
                continue
            node = str(key)
            non_null_keys.append(node)
            output_counts[node] = output_counts.get(node, 0) + 1

            frame = _frame_from_output(value)
            if frame is not None:
                camera_nodes.append(node)
                if node not in frame_shapes:
                    shape = _shape_of_frame(frame)
                    if shape is not None:
                        frame_shapes[node] = shape

        for node in executed:
            node_key = str(node)
            executed_counts[node_key] = executed_counts.get(node_key, 0) + 1

        step_rows.append(
            {
                "step": int(step.get("step", idx)),
                "now": float(step.get("now", 0.0) or 0.0),
                "executed_count": len(executed),
                "output_count": len(non_null_keys),
                "executed_nodes": [str(x) for x in executed],
                "output_nodes": non_null_keys,
                "camera_nodes": camera_nodes,
            }
        )

    top_outputs = sorted(output_counts.items(), key=lambda item: item[1], reverse=True)
    top_executed = sorted(executed_counts.items(), key=lambda item: item[1], reverse=True)

    print("\n=== Session Summary ===")
    print(
        format_table(
            ["metric", "value"],
            [
                ["recording", str(args.recording)],
                ["steps", str(len(steps))],
                ["t_start_s", f"{now_values[0]:.3f}"],
                ["t_end_s", f"{now_values[-1]:.3f}"],
                ["duration_s", f"{duration_s:.3f}"],
                ["unique_output_nodes", str(len(output_counts))],
                ["unique_executed_nodes", str(len(executed_counts))],
            ],
        )
    )

    if top_outputs:
        print("\n=== Output Stream Coverage ===")
        rows = [[name, str(count)] for name, count in top_outputs]
        print(format_table(["node", "non_null_outputs"], rows))

    preview_rows = [
        [
            str(row["step"]),
            f"{row['now']:.3f}",
            str(row["executed_count"]),
            str(row["output_count"]),
            ",".join(row["camera_nodes"]) if row["camera_nodes"] else "-",
        ]
        for row in step_rows[: max(0, args.preview)]
    ]
    if preview_rows:
        print("\n=== Step Preview ===")
        print(format_table(["step", "now_s", "executed", "outputs", "camera_nodes"], preview_rows))

    summary = {
        "schema_version": "retriever.mcap_session_summary.v1",
        "created_at": utc_now_iso(),
        "recording": str(args.recording),
        "steps": len(steps),
        "time": {
            "start_s": now_values[0],
            "end_s": now_values[-1],
            "duration_s": duration_s,
        },
        "output_counts": output_counts,
        "executed_counts": executed_counts,
        "frame_shapes": frame_shapes,
        "top_outputs": [{"node": name, "count": count} for name, count in top_outputs],
        "top_executed": [{"node": name, "count": count} for name, count in top_executed],
    }
    write_json(args.summary_out, summary)
    write_jsonl(args.table_out, step_rows)
    print(f"\n[Artifacts] summary={args.summary_out} step_table={args.table_out}")


if __name__ == "__main__":
    main()

