"""
Perception debugging with `Pipeline.step()` (in-process).

This is the simplest way to use the VS Code debugger to step into Flow logic:
set breakpoints inside `ColorDetector.step()` or `_detect_from_mask()` and run this file.

Unlike `Pipeline.run(backend=...)`, this does *not* spawn child processes.

Why synthetic frames?
  - Deterministic + no hardware dependency (works on CI and laptops without a camera).
  - If you want the same workflow with a real camera, use:
    `examples/tutorial/c_debug_and_replay/03_debug_perception_stepper_real_camera.py`

Run:
  pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
"""

from __future__ import annotations

import importlib
import numpy as np

from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest

# Reuse the real detector implementation from the working dora demo.
# Note: the `examples/tutorial/*` path is not a valid Python identifier, so we
# import it via importlib (string-based import), not `from ... import ...`.
_perception = importlib.import_module("examples.tutorial.b_ir_and_execution.06_dora_perception")
CameraData = _perception.CameraData
DetectionResults = _perception.DetectionResults
Image = _perception.Image
ColorDetector = _perception.ColorDetector


class SyntheticCamera(Flow[None, CameraData]):
    """Generates a synthetic RGB frame with alternating red/blue blocks."""

    def reset(self) -> None:
        self.frame_id = 0
        self.h = 240
        self.w = 320

    def step(self, _):  # type: ignore[override]
        self.frame_id += 1
        frame = np.zeros((self.h, self.w, 3), dtype=np.uint8)

        # Note: frames in the perception demo are RGB.
        if self.frame_id % 2 == 0:
            frame[50:120, 60:140, 0] = 255  # red
        else:
            frame[70:150, 100:180, 2] = 255  # blue

        return CameraData(image=Image(frame=frame, frame_id=self.frame_id))

class PrintDetections(Flow[DetectionResults, None]):
    def step(self, input: DetectionResults) -> None:
        labels = [d.label for d in (input.detections or [])]
        print(f"[PrintDetections] frame={input.image.frame_id} labels={labels}")
        return None


def main() -> None:
    pipe = Pipeline("perception_stepper_debug")

    camera = SyntheticCamera() @ Rate(hz=20)
    detector = ColorDetector(min_confidence=0.0) @ Trigger("image")
    sink = PrintDetections() @ Rate(hz=20)

    pipe.connect(camera, detector, sync=Latest())
    pipe.connect(detector, sink, sync=Latest())

    try:
        for i in range(3):
            print(f"\n=== step {i} ===")
            pipe.step(dt=0.05)
    finally:
        pipe.close_stepper()


if __name__ == "__main__":
    main()
