"""
Perception Pipeline - Real Camera to Object Detection

Demonstrates perception pipeline with real camera input:
- Real camera via cv2.VideoCapture (with mock fallback)
- Color-based object detection
- Backend execution (dora)

Run:
  pixi run demo-webcam-detection
  # or:
  pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception --backend dora --duration 10 --visualize rerun
"""

from __future__ import annotations

import argparse

from examples.shared.perception_runtime import (
    build_tutorial_perception_pipeline,
)


def build_perception_pipeline(*, show_window: bool):
    print("Building perception pipeline:")
    print("  Camera @ Rate(20Hz) -> ColorDetector @ Trigger -> Display @ Rate\n")
    pipe = build_tutorial_perception_pipeline(
        use_real_camera=True,
        show_window=show_window,
        min_confidence=0.6,
        camera_width=640,
        camera_height=480,
    )
    graph = pipe.get_graph()
    print(f"✓ Graph created: {graph.get_node_count()} nodes, {graph.get_edge_count()} edges\n")
    return pipe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Perception demo (camera -> detection -> display)")
    parser.add_argument("--backend", default="dora", choices=["dora", "multiprocessing"])
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument(
        "--visualize",
        default="auto",
        choices=["auto", "stdout", "window", "rerun", "both"],
        help="Visualization mode. 'auto' uses Rerun for Dora and OpenCV window otherwise.",
    )
    parser.add_argument(
        "--fresh-dora",
        dest="fresh_dora",
        action="store_true",
        default=False,
        help="Destroy/restart the dora runtime before launch.",
    )
    parser.add_argument(
        "--no-fresh-dora",
        dest="fresh_dora",
        action="store_false",
        help="Reuse an existing dora runtime (default).",
    )
    return parser.parse_args()


def _resolve_visualization(args: argparse.Namespace) -> tuple[bool, bool]:
    mode = args.visualize
    if mode == "auto":
        mode = "rerun" if args.backend == "dora" else "window"

    show_window = mode in {"window", "both"}
    use_rerun = mode in {"rerun", "both"}

    # OpenCV GUI windows from a Dora worker process are unreliable on macOS.
    if args.backend == "dora" and show_window:
        print(
            "[Perception Demo] OpenCV windows are unreliable from Dora worker processes.\n"
            "[Perception Demo] Disabling the window and using Rerun or the in-process stepper is recommended."
        )
        show_window = False
    return show_window, use_rerun


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Perception Demo - Real Camera to Detection\n")

    show_window, use_rerun = _resolve_visualization(args)

    pipe = build_perception_pipeline(show_window=show_window)
    backend_config = {}
    if args.backend == "dora" and args.fresh_dora:
        backend_config = {"dora_fresh": True}
        print("Using a fresh Dora runtime for this demo.\n")
    if use_rerun:
        print("Streaming typed outputs to Rerun.\n")

    print(f"Running for {args.duration:.1f} seconds...")
    print("Tip: Show colored objects (red/blue) to your camera!")
    print("-" * 60)
    pipe.run(
        backend=args.backend,
        duration=args.duration,
        blocking=True,
        backend_config=backend_config,
        visualize="rerun" if use_rerun else None,
    )
    print("-" * 60)

    print("\n" + "=" * 60)
    print("Pipeline Summary\n")
    print("Camera Input:")
    print("  • Tries cv2.VideoCapture(0) for real camera")
    print("  • Falls back to mock test pattern if no camera")
    print("\nDetection:")
    print("  • Red objects: RGB(255, <100, <100)")
    print("  • Blue objects: RGB(<100, <100, 255)")
    print("\nTip: Use red or blue paper/objects in front of camera!")
    print("=" * 60)


if __name__ == "__main__":
    main()
