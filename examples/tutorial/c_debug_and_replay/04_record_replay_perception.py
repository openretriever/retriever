"""
Record + replay a perception camera stream (in-process stepper) for debugging.

This is a stepper-first workflow:
  - record once from hardware (real camera) to MCAP
  - replay later (still in-process) so breakpoints inside `Flow.step()` work
  - optionally stream to Rerun for live visualization

Run:
  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10
  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --steps 10
  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --stream  # with live Rerun

  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from examples.shared.perception_runtime import (
    build_record_pipeline,
    build_replay_pipeline,
    emit_replay_finished,
    emit_replay_started,
    load_camera_buffer_from_recording,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Record + replay perception stream (in-process stepper).")
    sub = p.add_subparsers(dest="cmd", required=True)

    record = sub.add_parser("record", help="Record a short stream from the real camera")
    record.add_argument("--out", type=Path, default=Path("logs/perception.mcap"), help="Output recording path (.mcap)")
    record.add_argument("--stream", action="store_true", help="Stream to Rerun live while recording")
    record.add_argument("--steps", type=int, default=10, help="Number of step iterations")
    record.add_argument("--dt", type=float, default=0.05, help="Logical dt used for timestamps (seconds)")
    record.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between steps (optional)")

    replay = sub.add_parser("replay", help="Replay a recorded stream (no hardware needed)")
    replay.add_argument(
        "--recording", type=Path, default=Path("logs/perception.mcap"), help="Input recording path (.mcap)"
    )
    replay.add_argument("--steps", type=int, default=10, help="Max number of step iterations")
    replay.add_argument("--dt", type=float, default=0.05, help="Logical dt used for timestamps (seconds)")
    replay.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between steps (optional)")
    replay.add_argument("--show-window", action="store_true", help="Enable OpenCV window")
    replay.add_argument("--stream", action="store_true", help="Stream to Rerun live while replaying")

    return p.parse_args()


def cmd_record(args: argparse.Namespace) -> None:
    pipe, camera = build_record_pipeline()
    try:
        # Record the entire session (all streams) to MCAP
        pipe.record(
            args.out,
            steps=args.steps,
            dt=args.dt,
            sleep_s=args.sleep,
            name="camera",
            visualize=args.stream,
        )
    finally:
        pipe.close_stepper()
    print(f"[Recording] saved {args.steps} steps to {args.out}")


def _resolve_recording_path(path: Path) -> Path:
    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"Recording not found: {resolved}")
    return resolved


def cmd_replay(args: argparse.Namespace) -> None:
    recording = _resolve_recording_path(args.recording)
    buffer = load_camera_buffer_from_recording(recording)
    max_steps = len(buffer) if args.steps <= 0 else min(args.steps, len(buffer))
    replay_buffer = buffer[:max_steps]

    pipe, camera = build_replay_pipeline(display="cv2" if args.show_window else "stdout")
    if args.stream:
        print("[Replay] --stream is not supported for explicit stepper replay; proceeding without live Rerun.")

    emit_replay_started(recording_path=str(recording), frame_count_estimate=max_steps)
    try:
        pipe.replay(camera, buffer=replay_buffer)
        for _ in range(max_steps):
            pipe.step(dt=args.dt)
            if args.sleep > 0:
                time.sleep(args.sleep)
    finally:
        pipe.close_stepper()
    emit_replay_finished(recording_path=str(recording), steps_completed=max_steps)


def main() -> None:
    args = parse_args()
    if args.cmd == "record":
        cmd_record(args)
        return
    if args.cmd == "replay":
        cmd_replay(args)
        return
    raise SystemExit(f"Unknown subcommand: {args.cmd}")


if __name__ == "__main__":
    main()
