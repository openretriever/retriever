"""
Record + replay a perception camera stream (in-process stepper) for debugging.

This is a stepper-first workflow:
  - record once from hardware (real camera) to MCAP
  - replay later (still in-process) so breakpoints inside `Flow.run()` work
  - optionally stream to Rerun for live visualization

Run:
  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10
  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --stream  # with live Rerun

  pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
"""

from __future__ import annotations

import argparse
import importlib
import time
from pathlib import Path

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest

_perception = importlib.import_module("examples.tutorial.b_ir_and_execution.06_dora_perception")
CameraSource = _perception.CameraSource
CameraData = _perception.CameraData
Image = _perception.Image
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
    """Resolve and validate recording path."""
    if not path.exists():
        raise FileNotFoundError(
            f"Recording not found: {path}. Run 'record' first to create an MCAP session."
        )
    return path


def _as_camera_data(obj: object) -> CameraData | None:
    """Best-effort conversion from MCAP JSON payloads back into `CameraData`."""
    if isinstance(obj, CameraData):
        return obj

    # Covers the case where MCAP decoding returns real dataclass objects.
    if hasattr(obj, "image"):
        img = getattr(obj, "image", None)
        if img is None:
            return None
        if hasattr(img, "frame") and hasattr(img, "frame_id"):
            return CameraData(image=Image(frame=img.frame, frame_id=int(img.frame_id)))
        if isinstance(img, dict):
            frame = img.get("frame")
            if frame is None:
                return None
            return CameraData(image=Image(frame=frame, frame_id=int(img.get("frame_id") or 0)))
        return None

    if not isinstance(obj, dict):
        return None

    img = obj.get("image")
    if not isinstance(img, dict):
        return None

    frame = img.get("frame")
    if frame is None:
        return None

    frame_id = img.get("frame_id") or 0
    try:
        frame_id = int(frame_id)
    except Exception:
        frame_id = 0

    return CameraData(image=Image(frame=frame, frame_id=frame_id))


def _load_camera_buffer_from_mcap(path: Path) -> list[tuple[float, CameraData]]:
    """
    Extract a CameraData time series from an MCAP file.

    Note: node IDs inside MCAP topics are not stable across processes, so we detect the camera stream
    by inspecting payload shape instead of hard-coding a node id.
    """
    from retriever.lib.mcap import MCAPReader

    with MCAPReader(path) as reader:
        steps = list(reader)

    if not steps:
        raise RuntimeError(f"MCAP recording is empty: {path}")

    camera_key: str | None = None
    for step in steps:
        outputs = step.get("outputs", {}) or {}
        if not isinstance(outputs, dict):
            continue
        for key, val in outputs.items():
            if _as_camera_data(val) is not None:
                camera_key = str(key)
                break
        if camera_key is not None:
            break

    if camera_key is None:
        raise RuntimeError(f"Could not locate a CameraData-like stream in MCAP: {path}")

    buffer: list[tuple[float, CameraData]] = []
    for step in steps:
        now = step.get("now", 0.0) or 0.0
        try:
            ts = float(now)
        except Exception:
            ts = 0.0

        outputs = step.get("outputs", {}) or {}
        if not isinstance(outputs, dict):
            continue
        cam = _as_camera_data(outputs.get(camera_key))
        if cam is None:
            continue
        buffer.append((ts, cam))

    if not buffer:
        raise RuntimeError(f"Camera stream extracted but contained no frames: {path}")

    print(f"[Replay] extracted camera stream key={camera_key} frames={len(buffer)} from {path}")
    return buffer


def cmd_replay(args: argparse.Namespace) -> None:
    recording = _resolve_recording_path(args.recording)
    pipe, camera = build_replay_pipeline(show_window=args.show_window)

    camera_buffer = _load_camera_buffer_from_mcap(recording)
    pipe.replay(camera, buffer=camera_buffer)

    rerun_manager = None
    if args.stream:
        from retriever.lib.rerun import RerunConfig, RerunManager

        config = RerunConfig(mode="spawn")
        rerun_manager = RerunManager(config, app_id="perception_replay")
        rerun_manager.init()

    try:
        for i in range(args.steps):
            result = pipe.step(dt=args.dt)
            if rerun_manager is not None:
                rerun_manager.log_step_result(result, i)
            if args.sleep > 0:
                time.sleep(args.sleep)
    finally:
        pipe.close_stepper()
        if rerun_manager is not None:
            rerun_manager.cleanup()
    print(f"[Replay] ran {args.steps} steps from {recording}")


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
