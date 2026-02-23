"""
Record + replay a perception camera stream (in-process stepper) for debugging.

Run:
  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10
  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from retriever.tutorials.perception import (
    build_record_pipeline,
    build_replay_pipeline,
    emit_replay_finished,
    emit_replay_started,
    load_camera_buffer_from_mcap,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record + replay perception stream (in-process stepper).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    record = sub.add_parser("record", help="Record a short stream from the real camera")
    record.add_argument("--out", type=Path, default=Path("logs/perception.mcap"), help="Output recording path (.mcap)")
    record.add_argument("--stream", action="store_true", help="Stream to Rerun live while recording")
    record.add_argument("--steps", type=int, default=10, help="Number of step iterations")
    record.add_argument("--dt", type=float, default=0.05, help="Logical dt used for timestamps (seconds)")
    record.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between steps (optional)")

    replay = sub.add_parser("replay", help="Replay a recorded stream (no hardware needed)")
    replay.add_argument("--recording", type=Path, default=Path("logs/perception.mcap"), help="Input recording path (.mcap)")
    replay.add_argument("--steps", type=int, default=10, help="Max number of step iterations")
    replay.add_argument("--dt", type=float, default=0.05, help="Logical dt used for timestamps (seconds)")
    replay.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between steps (optional)")
    replay.add_argument("--show-window", action="store_true", help="Enable OpenCV window")
    replay.add_argument("--stream", action="store_true", help="Stream to Rerun live while replaying")

    return parser.parse_args()


def cmd_record(args: argparse.Namespace) -> None:
    pipe, camera = build_record_pipeline()
    try:
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
    if not path.exists():
        raise FileNotFoundError(f"Recording not found: {path}. Run 'record' first to create an MCAP session.")
    return path


def cmd_replay(args: argparse.Namespace) -> None:
    recording = _resolve_recording_path(args.recording)
    pipe, camera = build_replay_pipeline(show_window=args.show_window)

    camera_buffer = load_camera_buffer_from_mcap(recording)
    emit_replay_started(recording_path=str(recording), frame_count_estimate=len(camera_buffer))
    pipe.replay(camera, buffer=camera_buffer)

    rerun_manager = None
    if args.stream:
        from retriever.lib.rerun import RerunConfig, RerunManager

        config = RerunConfig(mode="spawn")
        rerun_manager = RerunManager(config, app_id="perception_replay")
        rerun_manager.init()

    completed = 0
    try:
        for i in range(args.steps):
            result = pipe.step(dt=args.dt)
            completed = i + 1
            if rerun_manager is not None:
                rerun_manager.log_step_result(result, i)
            if args.sleep > 0:
                time.sleep(args.sleep)
    finally:
        pipe.close_stepper()
        if rerun_manager is not None:
            rerun_manager.cleanup()
        emit_replay_finished(recording_path=str(recording), steps_completed=completed)
    print(f"[Replay] ran {completed} steps from {recording}")


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
