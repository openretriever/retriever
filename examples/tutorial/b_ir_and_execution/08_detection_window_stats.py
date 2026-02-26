"""
02 Vision Processing — Windowed Detection Stats

Demonstrates a vision pipeline that computes windowed statistics over detections:

  Camera @ Rate → Detector @ Trigger → Window(mean) → Print @ Trigger

This tutorial uses a deterministic synthetic camera source so it works the same
everywhere (CI, no camera permissions, no colored objects, etc.). For a real
camera demo, see `examples.tutorial.b_ir_and_execution.06_dora_perception`.

Run:
  pixi run python -m examples.tutorial.b_ir_and_execution.08_detection_window_stats --backend multiprocessing --duration 3
  pixi run python -m examples.tutorial.b_ir_and_execution.08_detection_window_stats --backend dora --duration 10
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np

from retriever.flow import Flow, Pipeline, Rate, Trigger, Window, flow_io

@flow_io
@dataclass
class CameraData:
    frame: np.ndarray
    frame_id: int


@flow_io
@dataclass
class DetectionCount:
    count: float


@flow_io
@dataclass
class WindowMeanCount:
    mean_count: float


class SyntheticCameraSource(Flow[None, CameraData]):
    """
    Deterministic camera source that generates simple red/blue blobs.

    It intentionally varies the number of blobs over time so the window mean
    changes (useful for demonstrating `Window(..., agg="mean")`).
    """

    def init(self) -> None:
        self._frame_id = 0

    def run(self, _):  # type: ignore[override]
        self._frame_id += 1
        height, width = 240, 320
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Always show a red square (RGB).
        x = int((self._frame_id * 7) % max(1, (width - 60)))
        frame[40:100, x : x + 60, 0] = 255

        # Show a blue square on even frames only (so detections alternate 1 ↔ 2).
        if self._frame_id % 2 == 0:
            y = int((self._frame_id * 5) % max(1, (height - 60)))
            frame[y : y + 60, 180:240, 2] = 255

        return CameraData(frame=frame, frame_id=self._frame_id)


class ColorBlobDetector(Flow[CameraData, DetectionCount]):
    """
    Minimal "detector" for the synthetic source: count the presence of red/blue blobs.

    This is intentionally simple: it just detects whether each mask has enough pixels
    to count as an "object".
    """

    MIN_PIXELS = 50

    def run(self, input: CameraData) -> DetectionCount:
        frame = input.frame

        red_mask = (frame[:, :, 0] > 180) & (frame[:, :, 1] < 120) & (frame[:, :, 2] < 120)
        blue_mask = (frame[:, :, 2] > 180) & (frame[:, :, 0] < 120) & (frame[:, :, 1] < 120)

        count = 0
        if int(red_mask.sum()) >= self.MIN_PIXELS:
            count += 1
        if int(blue_mask.sum()) >= self.MIN_PIXELS:
            count += 1

        return DetectionCount(count=float(count))


class PrintWindowMean(Flow[WindowMeanCount, None]):
    def init(self) -> None:
        self._step = 0

    def run(self, input: WindowMeanCount) -> None:
        self._step += 1
        print(f"[mean] step={self._step} mean_detections={input.mean_count:.2f}")
        return None


def build_pipeline(
    *,
    hz: float,
    window_s: float,
    window_buffer_size: int,
) -> Pipeline:
    pipe = Pipeline("vision_detection_window")

    with pipe:
        camera = SyntheticCameraSource() @ Rate(hz=hz)
        detector = ColorBlobDetector() @ Trigger("frame")
        printer = PrintWindowMean() @ Trigger("mean_count")

        # Perception path (Latest() is the default adapter for `>>`)
        camera >> detector

        # Stats path (window mean of detection counts)
        detector.then(
            printer,
            map={"count": "mean_count"},
            sync=Window(buffer_size=window_buffer_size, duration=window_s, agg="mean"),
        )

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Windowed detection stats (vision tutorial).")
    p.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    p.add_argument("--duration", type=float, default=3.0)
    p.add_argument("--hz", type=float, default=20.0)
    p.add_argument("--window", type=float, default=0.5, help="Window duration (seconds) for mean detection count.")
    p.add_argument("--window-buffer-size", type=int, default=200, help="Max events retained for the window.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(
        hz=args.hz,
        window_s=args.window,
        window_buffer_size=args.window_buffer_size,
    )
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)


if __name__ == "__main__":
    main()
