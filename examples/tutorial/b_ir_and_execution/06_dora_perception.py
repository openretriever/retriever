"""
Perception Runtime Demo - Live or Mock Camera to Object Detection

Demonstrates perception pipeline with live or mock camera input:
- Real camera via cv2.VideoCapture
- Color-based object detection
- Backend execution (in-process, multiprocessing, or dora)

Historical note: the filename still says `dora_perception`, but the public
surface is backend-neutral. The default task uses the in-process backend for a
direct local webcam path. Dora and multiprocessing remain explicit worker
backend variants when you want backend parity checks or live Rerun views.

Run:
  pixi run demo-webcam-detection
  pixi run demo-webcam-detection-mp-rerun
  pixi run demo-webcam-detection-dora
  pixi run demo-webcam-detection-dora-rerun
"""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import argparse

from examples.shared.perception_flows import build_tutorial_perception_pipeline
from retriever.lib.perception import optional_cv2


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
    parser = argparse.ArgumentParser(description="Perception runtime demo (camera -> detection -> display)")
    parser.add_argument("--backend", default="in-process", choices=["dora", "multiprocessing", "in-process"])
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--camera-index", type=int, default=0, help="Camera index to open (default: 0).")
    parser.add_argument(
        "--camera-mode",
        default="real",
        choices=["auto", "real", "mock"],
        help="Use 'real' (default) to require a live camera. Use 'auto' to try a live camera and fall back to synthetic frames, or 'mock' for synthetic frames.",
    )
    parser.add_argument(
        "--visualize",
        default="auto",
        choices=["auto", "stdout", "window", "rerun", "both"],
        help="Visualization mode. 'auto' prefers Rerun when installed and falls back to stdout; opt into cv2 explicitly when needed.",
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
        # Prefer Rerun when it is available so local desktop users see live visualization
        # out of the box, but fall back to stdout on machines without the SDK installed.
        try:
            import importlib
            importlib.import_module("rerun")
            mode = "rerun"
        except ImportError:
            mode = "stdout"

    show_window = mode in {"window", "both"}
    use_rerun = mode in {"rerun", "both"}

    if args.backend in {"dora", "multiprocessing"} and show_window:
        print(
            "[Perception Demo] OpenCV windows from worker backends are fragile across macOS, Linux remote sessions,\n"
            "[Perception Demo] and many Windows desktop setups. Prefer --visualize stdout, --visualize rerun,\n"
            "[Perception Demo] or the in-process webcam stepper for local GUI debugging."
        )
        show_window = False
    return show_window, use_rerun


def _camera_available(camera_index: int) -> bool:
    cv2 = optional_cv2()
    if cv2 is None:
        return False
    cap = cv2.VideoCapture(camera_index)
    try:
        if not cap.isOpened():
            return False
        ret, frame = cap.read()
        return bool(ret and frame is not None)
    finally:
        cap.release()


def _resolve_camera_mode(args: argparse.Namespace) -> bool:
    if args.camera_mode == "mock":
        return False
    if args.camera_mode == "real":
        return True
    if _camera_available(args.camera_index):
        return True
    print(
        f"[Perception Demo] No readable camera found at index {args.camera_index}; falling back to mock frames."
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
        print(
            "Tip: Show colored objects (red/blue) to your camera. "
            "If no camera is available, rerun with --camera-mode mock."
        )
    else:
        print(
            "Tip: This run is using mock frames. "
            "Use --camera-mode real to require a live webcam path."
        )
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
        print("  • Raises clearly if no camera is available")
    else:
        print("  • Uses mock test pattern when mock mode is selected or auto fallback triggers")
    print("\nDetection:")
    print("  • Red objects: RGB(255, <100, <100)")
    print("  • Blue objects: RGB(<100, <100, 255)")
    print("\nTip: Use red or blue paper/objects in front of camera!")
    print("=" * 60)


if __name__ == "__main__":
    main()
