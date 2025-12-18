"""
Perception Pipeline - Real Camera to Object Detection

Demonstrates perception pipeline with real camera input:
- Real camera via cv2.VideoCapture (with mock fallback)
- Color-based object detection
- Backend execution (dora)

Run:
  pixi run demo-dora
  # or:
  pixi run python -m examples.00_refact.009_dora_perception --backend dora --duration 10
"""

from __future__ import annotations

import argparse
import numpy as np
import cv2
from dataclasses import dataclass
from typing import List

from retriever.flow import Flow, flow_io, Rate, Trigger, Pipeline


@dataclass
class BBox:
    x: float
    y: float
    width: float
    height: float

@dataclass
class Image:
    frame: np.ndarray
    frame_id: int

@dataclass
class Detection:
    label: str
    confidence: float
    bbox: BBox

@flow_io
@dataclass
class CameraData:
    image: Image

@flow_io
@dataclass
class DetectionResults:
    image: Image
    detections: List[Detection]


class CameraSource(Flow[None, CameraData]):
    """Camera capture - tries real camera, falls back to mock"""
    def __init__(self, use_real_camera=True, width=640, height=480):
        super().__init__()
        self.use_real_camera = use_real_camera
        self.width = width
        self.height = height
        self.cap = None
        self.frame_count = 0

    def init(self):
        """Initialize camera on process start"""
        if self.use_real_camera:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    print(f"[CameraSource] Using real camera (index 0)")
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                else:
                    print(f"[CameraSource] Camera failed, using mock")
                    self.cap.release()
                    self.cap = None
                    self.use_real_camera = False
            else:
                print(f"[CameraSource] No camera found, using mock")
                self.use_real_camera = False

    def finalize(self):
        """Release camera on process stop"""
        if self.cap is not None:
            self.cap.release()
            print(f"[CameraSource] Camera released")

    def run(self, _) -> CameraData:
        self.frame_count += 1

        # Try real camera
        if self.use_real_camera and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return CameraData(image=Image(frame=rgb_frame, frame_id=self.frame_count))

        # Fallback: synthetic moving blobs (useful on CI / no camera / permissions)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        t = self.frame_count

        # Red box (moves horizontally)
        x = int((t * 7) % max(1, (self.width - 80)))
        cv2.rectangle(frame, (x, 60), (x + 80, 140), (255, 0, 0), -1)

        # Blue box (moves vertically)
        y = int((t * 5) % max(1, (self.height - 80)))
        cv2.rectangle(frame, (60, y), (140, y + 80), (0, 0, 255), -1)

        return CameraData(image=Image(frame=frame, frame_id=self.frame_count))


class ColorDetector(Flow[CameraData, DetectionResults]):
    """Detect colored objects in image"""
    def __init__(self, min_confidence=0.6):
        super().__init__()
        self.min_confidence = min_confidence

    def run(self, input: CameraData) -> DetectionResults:
        detections = []
        frame = input.image.frame

        # Detect red objects
        red_mask = (frame[:,:,0] > 180) & (frame[:,:,1] < 120) & (frame[:,:,2] < 120)
        detections.extend(self._detect_from_mask(red_mask, "red_object"))

        # Detect blue objects
        blue_mask = (frame[:,:,2] > 180) & (frame[:,:,0] < 120) & (frame[:,:,1] < 120)
        detections.extend(self._detect_from_mask(blue_mask, "blue_object"))

        # Filter by confidence
        filtered = [d for d in detections if d.confidence >= self.min_confidence]

        return DetectionResults(
            image=input.image,
            detections=filtered
        )

    def _detect_from_mask(self, mask: np.ndarray, label: str) -> List[Detection]:
        """Create detection from binary mask"""
        y_coords, x_coords = np.where(mask)

        if len(x_coords) < 50:
            return []

        x1, x2 = int(x_coords.min()), int(x_coords.max())
        y1, y2 = int(y_coords.min()), int(y_coords.max())
        area = len(x_coords)
        confidence = min(0.95, area / 5000.0)

        bbox = BBox(
            x=float(x1),
            y=float(y1),
            width=float(x2 - x1),
            height=float(y2 - y1)
        )

        return [Detection(label=label, confidence=confidence, bbox=bbox)]


class DisplayFlow(Flow[DetectionResults, None]):
    """Display detection results with cv2 window"""
    def __init__(self, show_window=True):
        super().__init__()
        self.show_window = show_window

    def init(self):
        """Create window on process start"""
        if self.show_window:
            try:
                cv2.namedWindow('Perception Demo', cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Perception Demo', 1280, 720)
            except Exception as e:
                print(f"[DisplayFlow] Failed to create OpenCV window, disabling UI: {e}")
                self.show_window = False

    def finalize(self):
        """Cleanup window on process stop"""
        if self.show_window:
            cv2.destroyAllWindows()

    def run(self, input: DetectionResults) -> None:
        if not input.image:
            return

        frame_id = input.image.frame_id
        dets = input.detections or []
        frame = input.image.frame

        # Print detections
        if dets:
            labels = [d.label for d in dets]
            confs = [f"{d.confidence:.2f}" for d in dets]
            print(f"  Frame {frame_id}: {len(dets)} objects - {list(zip(labels, confs))}")
        else:
            print(f"  Frame {frame_id}: No objects")

        # Show window with bounding boxes
        if self.show_window:
            display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()

            # Draw bounding boxes
            for det in dets:
                bbox = det.bbox
                x, y, w, h = int(bbox.x), int(bbox.y), int(bbox.width), int(bbox.height)

                # Color based on detection type
                if 'red' in det.label:
                    color = (0, 0, 255)
                elif 'blue' in det.label:
                    color = (255, 0, 0)
                else:
                    color = (255, 255, 255)

                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(display_frame, f"{det.label}: {det.confidence:.2f}",
                           (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Add frame info
            cv2.putText(display_frame, f"Frame {frame_id}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow('Perception Demo', display_frame)
            cv2.waitKey(1)

        return None


def build_perception_pipeline() -> Pipeline:
    """Build perception pipeline: Camera → Detector → Display"""
    print("Building perception pipeline:")
    print("  Camera @ Rate(20Hz) → ColorDetector @ Trigger → Display @ Rate\n")

    pipe = Pipeline("perception_demo")

    # Preferred authoring: `with pipe: a >> b` (no separate FlowContext).
    with pipe:
        camera = CameraSource(use_real_camera=True) @ Rate(hz=20)
        detector = ColorDetector(min_confidence=0.6) @ Trigger("image")
        display = DisplayFlow(show_window=True) @ Rate(hz=20)

        # Default adapter is Latest(), so `>>` is the shortest form.
        camera >> detector >> display

    graph = pipe.get_graph()
    print(f"✓ Graph created: {graph.get_node_count()} nodes, {graph.get_edge_count()} edges\n")
    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Perception demo (camera -> detection -> display)")
    p.add_argument("--backend", default="dora", choices=["dora", "multiprocessing"])
    p.add_argument("--duration", type=float, default=10.0)
    return p.parse_args()


def main() -> None:
    """Run perception demo"""
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
