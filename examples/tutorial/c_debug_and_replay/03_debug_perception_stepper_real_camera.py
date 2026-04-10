"""
Perception debugging with `Pipeline.step()` (in-process) using a real camera.

Goal:
  - Demonstrate that the stepper can debug the *actual* perception workflow
    (camera → detector → display/print), while still allowing VS Code breakpoints
    inside `Flow.step()` because everything runs in the current process.

Notes:
  - This does NOT use the dora backend; it uses the in-process stepper.
  - By default this does not open a GUI window (prints to stdout).
    Pass `--show-window` to enable the OpenCV window.
  - `dt` is optional and only affects timestamps (not scheduling). By default it
    uses `--sleep` if provided, otherwise wall-clock time.

Run:
  pixi run demo-webcam-stepper
"""

from __future__ import annotations

import argparse
import time

from examples.shared.perception_runtime import CameraSource, ColorDetector, DisplayFlow
from retriever.flow import Latest, Pipeline, Rate, Trigger


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Debug perception with Pipeline.step() using a real camera.")
    p.add_argument("--show-window", action="store_true", help="Enable OpenCV window")
    p.add_argument("--camera-index", type=int, default=0, help="Camera index to open (default: 0).")
    p.add_argument("--steps", type=int, default=10, help="Number of step iterations")
    p.add_argument("--sleep", type=float, default=0.05, help="Sleep seconds between steps")
    p.add_argument("--dt", type=float, default=None, help="Logical dt for timestamps (optional)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    show_window = bool(args.show_window)
    steps = int(args.steps)
    sleep_s = float(args.sleep)
    dt = args.dt if args.dt is not None else (sleep_s if sleep_s > 0 else None)

    pipe = Pipeline("perception_stepper_real_camera")

    camera = CameraSource(use_real_camera=True, camera_index=args.camera_index) @ Rate(hz=20)
    detector = ColorDetector(min_confidence=0.6) @ Trigger("image")
    display = DisplayFlow(display="cv2" if show_window else "stdout") @ Rate(hz=20)

    pipe.connect(camera, detector, sync=Latest())
    pipe.connect(detector, display, sync=Latest())

    try:
        for _ in range(steps):
            pipe.step(dt=dt)
            if sleep_s > 0:
                time.sleep(sleep_s)
    finally:
        pipe.close_stepper()


if __name__ == "__main__":
    main()
