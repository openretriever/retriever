"""
Perception Pipeline - Live Camera to Object Detection

Demonstrates perception pipeline with live or mock camera input:
- Real camera via cv2.VideoCapture (with mock fallback)
- Color-based object detection
- Backend execution (multiprocessing or dora)

The default public task uses the in-process backend so a local webcam path works
reliably across desktop platforms. Dora remains available as an explicit mock-camera
variant when you want distributed execution.

Run:
  pixi run demo-webcam-detection
  pixi run demo-webcam-detection-dora
  pixi run demo-webcam-detection-dora-rerun
"""

from __future__ import annotations

import argparse

from retriever.tutorials.perception import build_tutorial_perception_pipeline


def build_perception_pipeline(*, show_window: bool, camera_index: int, use_real_camera: bool):
    print("Building perception pipeline:")
    print("  Camera @ Rate(20Hz) -> ColorDetector @ Trigger -> Display @ Rate\n")
    pipe = build_tutorial_perception_pipeline(
        use_real_camera=use_real_camera,
        show_window=show_window,
        min_confidence=0.6,
        camera_width=640,
        camera_height=480,
        camera_index=camera_index,
    )
    graph = pipe.get_graph()
    print(f"✓ Graph created: {graph.get_node_count()} nodes, {graph.get_edge_count()} edges\n")
    return pipe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Perception demo (camera -> detection -> display)")
    parser.add_argument("--backend", default="in-process", choices=["dora", "multiprocessing", "in-process"])
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--camera-index", type=int, default=0, help="Camera index to open (default: 0).")
    parser.add_argument(
        "--camera-mode",
        default="auto",
        choices=["auto", "real", "mock"],
        help="Use 'real' to request a live camera, 'mock' for synthetic frames, or 'auto' for backend-safe defaults.",
    )
    parser.add_argument(
        "--visualize",
        default="auto",
        choices=["auto", "stdout", "window", "rerun", "both"],
        help="Visualization mode. 'auto' uses stdout everywhere; opt into cv2 or Rerun explicitly.",
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
        mode = "stdout"

    show_window = mode in {"window", "both"}
    use_rerun = mode in {"rerun", "both"}

    # GUI windows from backend worker processes are fragile across local/remote desktop setups.
    if args.backend == "dora" and show_window:
        print(
            "[Perception Demo] OpenCV windows from Dora worker processes are fragile across macOS, Linux remote sessions,\n"
            "[Perception Demo] and Windows desktop setups. Disabling the window; prefer --visualize stdout, --visualize rerun,\n"
            "[Perception Demo] or the in-process webcam stepper for local GUI debugging."
        )
        show_window = False
    return show_window, use_rerun


def _resolve_camera_mode(args: argparse.Namespace) -> bool:
    if args.camera_mode == "real":
        return True
    if args.camera_mode == "mock":
        return False

    if args.backend == "in-process":
        print(
            "[Perception Demo] Using live camera with mock fallback in-process by default.\n"
            "[Perception Demo] Pass --camera-mode mock if you want a deterministic synthetic stream instead."
        )
        return True

    print(
        "[Perception Demo] Using mock camera in backend workers by default.\n"
        "[Perception Demo] Use --backend in-process or demo-webcam-stepper when you explicitly want live capture."
    )
    return False


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Perception Demo - Live or Mock Camera to Detection\n")

    show_window, use_rerun = _resolve_visualization(args)
    use_real_camera = _resolve_camera_mode(args)

    pipe = build_perception_pipeline(
        show_window=show_window,
        camera_index=args.camera_index,
        use_real_camera=use_real_camera,
    )
    backend_config = {}
    if args.backend == "dora" and args.fresh_dora:
        backend_config = {"dora_fresh": True}
        print("Using a fresh Dora runtime for this demo.\n")
    if use_rerun:
        print("Streaming typed outputs to Rerun.\n")

    print(f"Running for {args.duration:.1f} seconds...")
    if use_real_camera:
        print("Tip: Show colored objects (red/blue) to your camera. If no camera is available, this demo falls back to mock frames.")
    else:
        print("Tip: This backend demo is using mock frames by default. Use --backend in-process or demo-webcam-stepper for a real camera path.")
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
    if use_real_camera:
        print(f"  • Tries cv2.VideoCapture({args.camera_index}) for real camera")
        print("  • Falls back to mock test pattern if no camera")
    else:
        print("  • Uses mock test pattern by default in backend workers")
    print("\nDetection:")
    print("  • Red objects: RGB(255, <100, <100)")
    print("  • Blue objects: RGB(<100, <100, 255)")
    print("\nTip: Use red or blue paper/objects in front of camera!")
    print("=" * 60)


if __name__ == "__main__":
    main()
