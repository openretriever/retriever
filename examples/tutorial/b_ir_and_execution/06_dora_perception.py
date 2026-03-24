"""
Perception Pipeline - Real Camera to Object Detection

Demonstrates perception pipeline with real camera input:
- Real camera via cv2.VideoCapture (with mock fallback)
- Color-based object detection
- Backend execution (dora)

Run:
  pixi run demo-webcam-detection
  # or:
  pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception --backend dora --duration 10
"""

from __future__ import annotations

import argparse

from retriever.tutorials.perception import (
    BBox,
    CameraData,
    CameraSource,
    ColorDetector,
    Detection,
    DetectionResults,
    DisplayFlow,
    Image,
    build_tutorial_perception_pipeline,
)


def build_perception_pipeline():
    print("Building perception pipeline:")
    print("  Camera @ Rate(20Hz) -> ColorDetector @ Trigger -> Display @ Rate\n")
    pipe = build_tutorial_perception_pipeline(
        use_real_camera=True,
        show_window=True,
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Perception Demo - Real Camera to Detection\n")

    pipe = build_perception_pipeline()

    print(f"Running for {args.duration:.1f} seconds...")
    print("Tip: Show colored objects (red/blue) to your camera!")
    print("-" * 60)
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)
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
