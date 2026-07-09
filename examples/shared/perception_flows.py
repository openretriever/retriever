"""
Tutorial perception flows and pipeline factories.

Defines the concrete Flow subclasses and Pipeline builders used by the
tutorial examples. Data types and visualization helpers live in
`examples.shared.perception_lib` so they can be imported without pulling in
the full example stack.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, List, Optional

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io
from examples.shared.perception_lib import (
    BBox,
    CameraData,
    Detection,
    DetectionResults,
    Image,
    PerceptionDisplayMode,
    PERCEPTION_DISPLAY_MODES,
    optional_cv2,
    render_detection_overlay,
    require_demo_deps,
    send_perception_blueprint,
)
from retriever.recording import detect_recording_format, open_recording_reader
from retriever.registry.pipeline import register_pipeline

try:
    import rerun as rr  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    rr = None


# ---------------------------------------------------------------------------
# Event streaming helpers
# ---------------------------------------------------------------------------


def _stream_path() -> Optional[Path]:
    raw = str(
        os.getenv("RETRIEVER_RUNTIME_STREAM_JSONL")
        or os.getenv("RETRIEVER_SEMANTIC_STREAM_JSONL")
        or ""
    ).strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _emit_perception_event(*, node: str, event: str, payload: dict[str, Any]) -> None:
    path = _stream_path()
    if path is None:
        return
    row = {
        "timestamp": time.time(),
        "run_id": str(os.getenv("RETRIEVER_RUN_ID") or ""),
        "pipeline_id": str(os.getenv("RETRIEVER_PIPELINE_ID") or ""),
        "node": node,
        "event": event,
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def emit_replay_started(*, recording_path: str, frame_count_estimate: int) -> None:
    _emit_perception_event(
        node="replay",
        event="Perception.ReplayStarted",
        payload={
            "recording_path": recording_path,
            "frame_count_estimate": int(frame_count_estimate),
        },
    )


def emit_replay_finished(*, recording_path: str, steps_completed: int) -> None:
    _emit_perception_event(
        node="replay",
        event="Perception.ReplayFinished",
        payload={
            "recording_path": recording_path,
            "steps_completed": int(steps_completed),
        },
    )


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------


class CameraSource(Flow[None, CameraData]):
    """Camera capture that prefers a real camera and falls back to a synthetic stream."""

    def __init__(
        self,
        *,
        use_real_camera: bool = True,
        width: int = 640,
        height: int = 480,
        camera_index: int = 0,
    ) -> None:
        super().__init__()
        self.use_real_camera = bool(use_real_camera)
        self.width = int(width)
        self.height = int(height)
        self.camera_index = int(camera_index)
        self.cap = None
        self.frame_count = 0
        self.mode = "unknown"
        self._initialized = False

    def init_config(self) -> dict:
        return {
            "use_real_camera": self.use_real_camera,
            "width": self.width,
            "height": self.height,
            "camera_index": self.camera_index,
        }

    def reset(self) -> None:
        require_demo_deps()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if rr is not None and hasattr(rr, "get_global_data_recording"):
            try:
                if rr.get_global_data_recording() is not None:
                    send_perception_blueprint(rr)
            except Exception:
                pass
        self.frame_count = 0
        self._initialized = True
        self.mode = "mock"
        if self.use_real_camera:
            cv2 = optional_cv2()
            if cv2 is None:
                raise RuntimeError(
                    "CameraSource requires OpenCV for real camera capture. "
                    "Install demo dependencies: pip install opencv-python"
                )
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise RuntimeError(
                    f"Camera index {self.camera_index} could not be opened. "
                    "Check that a webcam is connected, or use use_real_camera=False for mock frames."
                )
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                self.cap.release()
                self.cap = None
                raise RuntimeError(
                    f"Camera index {self.camera_index} opened but failed to read a frame."
                )
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.mode = "real"
            print(f"[CameraSource] Using real camera (index {self.camera_index})")

        _emit_perception_event(
            node="camera",
            event="Perception.CameraMode",
            payload={
                "mode": self.mode,
                "camera_index": self.camera_index,
                "width": self.width,
                "height": self.height,
            },
        )

    def finalize(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("[CameraSource] Camera released")

    def step(self, _) -> CameraData:
        if not self._initialized:
            self.reset()
        require_demo_deps()
        self.frame_count += 1

        import numpy as np

        cv2 = optional_cv2()
        if self.mode == "real" and self.cap is not None and self.cap.isOpened() and cv2 is not None:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                out = CameraData(image=Image(frame=rgb_frame, frame_id=self.frame_count), mode="real")
                _emit_perception_event(
                    node="camera",
                    event="Perception.FrameCaptured",
                    payload={"frame_id": out.image.frame_id, "mode": out.mode},
                )
                return out
            self.mode = "mock"

        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        t = self.frame_count
        x = int((t * 7) % max(1, (self.width - 80)))
        y = int((t * 5) % max(1, (self.height - 80)))
        frame[60:140, x : x + 80] = (255, 0, 0)
        frame[y : y + 80, 60:140] = (0, 0, 255)
        out = CameraData(image=Image(frame=frame, frame_id=self.frame_count), mode=self.mode or "mock")
        _emit_perception_event(
            node="camera",
            event="Perception.FrameCaptured",
            payload={"frame_id": out.image.frame_id, "mode": out.mode},
        )
        return out


class ColorDetector(Flow[CameraData, DetectionResults]):
    def __init__(self, *, min_confidence: float = 0.6) -> None:
        super().__init__()
        self.min_confidence = float(min_confidence)

    def init_config(self) -> dict:
        return {"min_confidence": self.min_confidence}

    def step(self, input: CameraData) -> DetectionResults:
        require_demo_deps()
        camera = _as_camera_data(input)
        if camera is None:
            return DetectionResults()
        detections: List[Detection] = []
        frame = camera.image.frame

        import numpy as np

        red_mask = (
            (frame[:, :, 0] > 180) & (frame[:, :, 1] < 120) & (frame[:, :, 2] < 120)
        )
        detections.extend(self._detect_from_mask(red_mask, "red_object"))

        blue_mask = (
            (frame[:, :, 2] > 180) & (frame[:, :, 0] < 120) & (frame[:, :, 1] < 120)
        )
        detections.extend(self._detect_from_mask(blue_mask, "blue_object"))

        filtered = [row for row in detections if row.confidence >= self.min_confidence]
        labels = [str(row.label) for row in filtered]
        max_confidence = max([float(row.confidence) for row in filtered], default=0.0)
        _emit_perception_event(
            node="detector",
            event="Perception.Detections",
            payload={
                "frame_id": int(camera.image.frame_id),
                "count": len(filtered),
                "labels": labels,
                "max_confidence": float(max_confidence) if filtered else 0.0,
                "empty": len(filtered) == 0,
            },
        )
        return DetectionResults(image=camera.image, detections=filtered, mode=str(camera.mode or "unknown"))

    def _detect_from_mask(self, mask: Any, label: str) -> List[Detection]:
        import numpy as np

        y_coords, x_coords = np.where(mask)
        if len(x_coords) < 50:
            return []

        x1, x2 = int(x_coords.min()), int(x_coords.max())
        y1, y2 = int(y_coords.min()), int(y_coords.max())
        area = len(x_coords)
        confidence = min(0.95, area / 5000.0)

        return [
            Detection(
                label=label,
                confidence=confidence,
                bbox=BBox(
                    x=float(x1),
                    y=float(y1),
                    width=float(x2 - x1),
                    height=float(y2 - y1),
                ),
            )
        ]


class DisplayFlow(Flow[DetectionResults, None]):
    def __init__(self, *, display: PerceptionDisplayMode = "stdout") -> None:
        super().__init__()
        if display not in PERCEPTION_DISPLAY_MODES:
            raise ValueError(f"Unsupported display mode: {display}")
        self.display = display

    def init_config(self) -> dict:
        return {"display": self.display}

    def reset(self) -> None:
        if self.display != "cv2":
            return
        cv2 = optional_cv2()
        if cv2 is None:
            raise RuntimeError("OpenCV UI is not available; install demo dependencies to use --visualize cv2.")
        try:
            cv2.namedWindow("Perception Demo", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Perception Demo", 1280, 720)
        except Exception as exc:
            raise RuntimeError(f"Failed to create OpenCV window for perception replay: {exc}") from exc

    def finalize(self) -> None:
        cv2 = optional_cv2()
        if self.display == "cv2" and cv2 is not None:
            cv2.destroyAllWindows()

    def step(self, input: DetectionResults) -> None:
        if not input.image:
            return None

        frame_id = input.image.frame_id
        detections = input.detections or []
        frame = input.image.frame
        if self.display == "stdout" and detections:
            labels = [row.label for row in detections]
            confs = [f"{row.confidence:.2f}" for row in detections]
            print(f"  Frame {frame_id}: {len(detections)} objects - {list(zip(labels, confs))}")
        elif self.display == "stdout":
            print(f"  Frame {frame_id}: No objects")

        cv2 = optional_cv2()
        if self.display == "cv2" and cv2 is not None:
            display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()
            for det in detections:
                bbox = det.bbox
                x, y, w, h = int(bbox.x), int(bbox.y), int(bbox.width), int(bbox.height)
                color = (0, 0, 255) if "red" in det.label else (255, 0, 0) if "blue" in det.label else (255, 255, 255)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(
                    display_frame,
                    f"{det.label}: {det.confidence:.2f}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )
            cv2.putText(
                display_frame,
                f"Frame {frame_id}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.imshow("Perception Demo", display_frame)
            cv2.waitKey(1)

        return None


class Drain(Flow[CameraData, None]):
    def step(self, _input: CameraData) -> None:
        return None


# ---------------------------------------------------------------------------
# Pipeline factories
# ---------------------------------------------------------------------------


def build_tutorial_perception_pipeline(
    *,
    use_real_camera: bool = True,
    show_window: bool = False,
    min_confidence: float = 0.6,
    camera_width: int = 640,
    camera_height: int = 480,
    camera_index: int = 0,
) -> Pipeline:
    pipe = Pipeline("tutorial.perception")
    with pipe:
        camera = CameraSource(
            use_real_camera=use_real_camera,
            width=camera_width,
            height=camera_height,
            camera_index=camera_index,
        ) @ Rate(hz=30)
        detector = ColorDetector(min_confidence=min_confidence) @ Trigger("image")
        display = DisplayFlow(display="cv2" if show_window else "stdout") @ Rate(hz=3)
        camera >> detector >> display
    return pipe


@register_pipeline(
    "tutorial.perception",
    category="tutorial",
    description="Tutorial perception pipeline with real camera fallback, detection, and display.",
    tags=["tutorial", "perception", "camera", "dora"],
)
def _register_tutorial_perception_pipeline(
    *,
    use_real_camera: bool = True,
    show_window: bool = False,
    min_confidence: float = 0.6,
    camera_width: int = 640,
    camera_height: int = 480,
    camera_index: int = 0,
) -> Pipeline:
    return build_tutorial_perception_pipeline(
        use_real_camera=use_real_camera,
        show_window=show_window,
        min_confidence=min_confidence,
        camera_width=camera_width,
        camera_height=camera_height,
        camera_index=camera_index,
    )


def build_record_pipeline(*, camera_index: int = 0, use_real_camera: bool = True) -> tuple[Pipeline, object]:
    pipe = Pipeline("tutorial.perception.record")
    camera = CameraSource(use_real_camera=use_real_camera, width=640, height=480, camera_index=camera_index) @ Rate(hz=20)
    drain = Drain() @ Trigger("image")
    pipe.connect(camera, drain, sync=Latest())
    return pipe, camera


def build_replay_pipeline(
    *,
    display: PerceptionDisplayMode = "stdout",
) -> tuple[Pipeline, object]:
    pipe = Pipeline("tutorial.perception.replay")
    camera = CameraSource(use_real_camera=False, width=640, height=480) @ Rate(hz=20)
    detector = ColorDetector(min_confidence=0.6) @ Trigger("image")
    display_flow = DisplayFlow(display=display) @ Rate(hz=20)
    pipe.connect(camera, detector, sync=Latest())
    pipe.connect(detector, display_flow, sync=Latest())
    return pipe, camera


# ---------------------------------------------------------------------------
# Recording / replay utilities
# ---------------------------------------------------------------------------


def _as_camera_data(obj: object) -> CameraData | None:
    if isinstance(obj, CameraData):
        return obj
    if hasattr(obj, "image"):
        img = getattr(obj, "image", None)
        mode = str(getattr(obj, "mode", "unknown") or "unknown")
        if img is None:
            return None
        if hasattr(img, "frame") and hasattr(img, "frame_id"):
            return CameraData(image=Image(frame=img.frame, frame_id=int(img.frame_id)), mode=mode)
        if isinstance(img, dict):
            frame = img.get("frame")
            if frame is None:
                return None
            return CameraData(
                image=Image(frame=frame, frame_id=int(img.get("frame_id") or 0)),
                mode=str(mode or img.get("mode") or "unknown"),
            )
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
    return CameraData(
        image=Image(frame=frame, frame_id=frame_id),
        mode=str(obj.get("mode") or "unknown"),
    )


def _load_camera_buffer_generic(path: Path) -> list[tuple[float, CameraData]]:
    reader = open_recording_reader(path)
    candidates: list[tuple[tuple[int, int, str], list[tuple[float, CameraData]]]] = []

    for node_id in reader.list_node_ids():
        try:
            raw_buffer = reader.read_node_stream(node_id)
        except Exception:
            continue

        camera_buffer: list[tuple[float, CameraData]] = []
        for ts, value in raw_buffer:
            camera = _as_camera_data(value)
            if camera is None:
                camera_buffer = []
                break
            camera_buffer.append((float(ts), camera))

        if not camera_buffer:
            continue

        score = (
            10 if "CameraSource" in node_id else 0,
            len(camera_buffer),
            node_id,
        )
        candidates.append((score, camera_buffer))

    if not candidates:
        raise RuntimeError(
            f"Could not locate a CameraData-like stream in recording: {path}. "
            "Re-record with the current build to generate replayable session payloads."
        )
    return max(candidates, key=lambda item: item[0])[1]


def load_camera_buffer_from_mcap(path: Path) -> list[tuple[float, CameraData]]:
    return _load_camera_buffer_generic(path)


def load_camera_buffer_from_rrd(path: Path) -> list[tuple[float, CameraData]]:
    return _load_camera_buffer_generic(path)


def load_camera_buffer_from_recording(path: Path) -> list[tuple[float, CameraData]]:
    fmt = detect_recording_format(path)
    if fmt in {"mcap", "rrd"}:
        return _load_camera_buffer_generic(path)
    raise ValueError(f"Unsupported recording path for perception replay: {path}")


__all__ = [
    # Re-exported types (convenience for examples that only import from here)
    "BBox",
    "CameraData",
    "Detection",
    "DetectionResults",
    "Image",
    "PERCEPTION_DISPLAY_MODES",
    "PerceptionDisplayMode",
    # Flows
    "CameraSource",
    "ColorDetector",
    "DisplayFlow",
    "Drain",
    # Pipelines
    "build_record_pipeline",
    "build_replay_pipeline",
    "build_tutorial_perception_pipeline",
    # Replay utils
    "emit_replay_finished",
    "emit_replay_started",
    "load_camera_buffer_from_recording",
    "load_camera_buffer_from_mcap",
    "load_camera_buffer_from_rrd",
]
