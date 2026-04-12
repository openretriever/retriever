"""
Record + replay a perception camera stream (in-process stepper) for debugging.

This is a stepper-first workflow:
  - record once from a live camera (or mock fallback) to `.rrd` plus a mirrored `.mcap`
  - replay later (still in-process) so breakpoints inside `Flow.step()` work
  - optionally visualize replay in stdout, OpenCV, Rerun, or both

`stdout` is the documented cross-platform default. Use `cv2` or `rerun` only on a local desktop session.

Run:
  pixi run demo-webcam-record
  pixi run demo-webcam-replay-rrd
  pixi run demo-webcam-replay-mcap
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from retriever.config import RecordConfig
from examples.shared.perception_runtime import (
    build_record_pipeline,
    build_replay_pipeline,
    emit_replay_finished,
    emit_replay_started,
    load_camera_buffer_from_recording,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record + replay perception stream (in-process stepper).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    record = sub.add_parser("record", help="Record a short stream from the real camera")
    record.add_argument(
        "--out",
        type=Path,
        default=Path("logs/perception.rrd"),
        help="Primary output artifact (.rrd recommended for inspection).",
    )
    record.add_argument(
        "--replay-out",
        type=Path,
        default=Path("logs/perception.mcap"),
        help="Optional replay artifact path (.mcap recommended for portable replay).",
    )
    record.add_argument("--camera-index", type=int, default=0, help="Camera index to open (default: 0).")
    record.add_argument("--stream", action="store_true", help="Stream to Rerun live while recording")
    record.add_argument("--steps", type=int, default=10, help="Number of step iterations")
    record.add_argument("--dt", type=float, default=0.05, help="Logical dt used for timestamps (seconds)")
    record.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between steps (optional)")

    replay = sub.add_parser("replay", help="Replay a recorded stream (no hardware needed)")
    replay.add_argument(
        "--recording",
        type=Path,
        default=Path("logs/perception.rrd"),
        help="Input recording path (.rrd or .mcap).",
    )
    replay.add_argument("--steps", type=int, default=10, help="Max number of step iterations")
    replay.add_argument("--dt", type=float, default=0.05, help="Logical dt used for timestamps (seconds)")
    replay.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between steps (optional)")
    replay.add_argument(
        "--visualize",
        choices=("stdout", "cv2", "rerun", "both"),
        default="stdout",
        help="Replay visualization mode: stdout logs, cv2 window, live Rerun, or both cv2+Rerun.",
    )

    return parser.parse_args()


def cmd_record(args: argparse.Namespace) -> None:
    if args.out.expanduser().resolve() == args.replay_out.expanduser().resolve():
        raise SystemExit("--out and --replay-out must be different artifact paths.")
    pipe, _camera = build_record_pipeline(camera_index=args.camera_index)
    cfg = RecordConfig(path=args.out, mirrors=(args.replay_out,))
    try:
        pipe.record(
            cfg,
            steps=args.steps,
            dt=args.dt,
            sleep_s=args.sleep,
            name="camera",
            visualize=args.stream,
        )
    finally:
        pipe.close_stepper()
    outputs = ", ".join(str(path) for path in cfg.artifact_paths())
    print(f"[Recording] saved {args.steps} steps to {outputs}")
    print("[Recording] if no camera is available, the tutorial pipeline uses mock frames so the artifact flow still works.")


def _resolve_recording_path(path: Path) -> Path:
    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(
            f"Recording not found: {resolved}. Run 'record' first to create a perception recording (.rrd or .mcap)."
        )
    return resolved


def cmd_replay(args: argparse.Namespace) -> None:
    recording = _resolve_recording_path(args.recording)
    camera_buffer = load_camera_buffer_from_recording(recording)
    max_steps = len(camera_buffer) if args.steps <= 0 else min(args.steps, len(camera_buffer))
    replay_buffer = camera_buffer[:max_steps]

    display = "cv2" if args.visualize in {"cv2", "both"} else "stdout" if args.visualize == "stdout" else "none"
    pipe, camera = build_replay_pipeline(display=display)
    emit_replay_started(recording_path=str(recording), frame_count_estimate=max_steps)
    pipe.replay(camera, buffer=replay_buffer)

    rerun_manager = None
    if args.visualize in {"rerun", "both"}:
        from retriever.lib.rerun import RerunConfig, RerunManager

        rerun_manager = RerunManager(RerunConfig(mode="spawn"), app_id="perception_replay")
        rerun_manager.init()

    completed = 0
    try:
        for i in range(max_steps):
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
