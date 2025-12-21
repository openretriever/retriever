"""
Record + replay a perception camera stream (in-process stepper) for debugging.

This is a stepper-first workflow:
  - record once from hardware (real camera) to MCAP
  - replay later (still in-process) so breakpoints inside `Flow.run()` work
  - optionally stream to Rerun for live visualization

Run:
  pixi run python -m examples.tutorial.014_record_replay_perception record --out logs/perception.mcap --steps 10
  pixi run python -m examples.tutorial.014_record_replay_perception record --stream  # with live Rerun

  pixi run python -m examples.tutorial.014_record_replay_perception replay --recording logs/perception.mcap --steps 10
"""

from __future__ import annotations

import argparse
import importlib
import time
from pathlib import Path

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest

_perception = importlib.import_module("examples.tutorial.009_dora_perception")
CameraSource = _perception.CameraSource
CameraData = _perception.CameraData
ColorDetector = _perception.ColorDetector
DisplayFlow = _perception.DisplayFlow


class Drain(Flow[CameraData, None]):
    """Minimal sink to keep the source connected inside the pipeline."""

    def run(self, _input: CameraData) -> None:
        return None


def build_record_pipeline() -> tuple[Pipeline, object]:
    pipe = Pipeline("perception_record")
    camera = CameraSource(use_real_camera=True) @ Rate(hz=20)
    drain = Drain() @ Trigger("image")
    pipe.connect(camera, drain, sync=Latest())
    return pipe, camera


def build_replay_pipeline(*, show_window: bool) -> tuple[Pipeline, object]:
    pipe = Pipeline("perception_replay")

    # Build with a placeholder camera source, then swap it to a replay source.
    camera = CameraSource(use_real_camera=False) @ Rate(hz=20)
    detector = ColorDetector(min_confidence=0.6) @ Trigger("image")
    display = DisplayFlow(show_window=show_window) @ Rate(hz=20)

    pipe.connect(camera, detector, sync=Latest())
    pipe.connect(detector, display, sync=Latest())
    return pipe, camera


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

    return p.parse_args()


def cmd_record(args: argparse.Namespace) -> None:
    pipe, camera = build_record_pipeline()
    try:
        buffer = pipe.record(
            camera,
            args.out,
            steps=args.steps,
            dt=args.dt,
            sleep_s=args.sleep,
            name="camera",
            visualize=args.stream,
        )
    finally:
        pipe.close_stepper()
    print(f"[Recording] wrote {len(buffer)} steps to {args.out}")


def _resolve_recording_path(path: Path) -> Path:
    """
    Resolve default recording path with a small legacy fallback.

    This keeps the demo usable if you recorded using the older filename:
      logs/perception_bag.pkl.gz
    """
    default = Path("logs/perception_recording.pkl.gz")
    if path == default and not path.exists():
        legacy = Path("logs/perception_bag.pkl.gz")
        if legacy.exists():
            print(f"[Replay] {path} not found; using legacy {legacy}")
            return legacy
    return path


def cmd_replay(args: argparse.Namespace) -> None:
    recording = _resolve_recording_path(args.recording)

    pipe, camera = build_replay_pipeline(show_window=bool(args.show_window))

    # Swap the camera node to a replay source (no custom ReplayFlow needed).
    replay = pipe.replay(camera, path=recording)

    try:
        for _ in range(args.steps):
            pipe.step(dt=args.dt)
            if getattr(replay.flow, "done", False):
                break
            if args.sleep > 0:
                time.sleep(args.sleep)
    finally:
        pipe.close_stepper()


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
