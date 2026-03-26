from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

try:
    import cv2  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    cv2 = None  # type: ignore[assignment]

try:
    import numpy as np  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]

try:
    import rerun as rr  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    rr = None

from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io
from retriever.pipeline_registry import register_pipeline

_PERCEPTION_BLUEPRINT_SENT = False


def _require_demo_deps() -> None:
    if cv2 is None or np is None:
        raise RuntimeError(
            "tutorial.perception requires demo dependencies (numpy, opencv-python). "
            "Install retriever with the demo extras to use this pipeline."
        )


def _send_perception_blueprint(rr_module: Any) -> None:
    global _PERCEPTION_BLUEPRINT_SENT

    if _PERCEPTION_BLUEPRINT_SENT:
        return
    if not hasattr(rr_module, "send_blueprint") or not hasattr(rr_module, "blueprint"):
        return

    try:
        rrb = rr_module.blueprint
        rr_module.log(
            "docs/perception",
            rr_module.TextDocument(
                (
                    "# Perception Demo\n\n"
                    "- Main view: annotated detector overlay image.\n"
                    "- `.../output/overlay`: RGB frame with boxes already rendered.\n"
                    "- `.../output/image`: raw camera stream.\n"
                    "- `.../output/bbox`: raw box geometry.\n"
                    "- `ColorDetector/.../output/count`: number of detections.\n"
                    "- `.../mode`: `real` camera vs `mock` fallback.\n"
                ),
                media_type=rr_module.MediaType.MARKDOWN,
            ),
            static=True,
        )
        blueprint = rrb.Blueprint(
            rrb.Horizontal(
                rrb.Tabs(
                    rrb.TensorView(
                        origin="/flows",
                        contents="+ /flows/**/output/overlay",
                        name="Detections",
                    ),
                    rrb.TensorView(
                        origin="/flows",
                        contents="+ /flows/**/output/image",
                        name="Raw Camera",
                    ),
                    active_tab="Detections",
                ),
                rrb.Vertical(
                    rrb.TimeSeriesView(
                        origin="/flows",
                        contents="+ /flows/**/output/count",
                        name="Detection Count",
                    ),
                    rrb.TextDocumentView(
                        origin="docs/perception",
                        name="Legend",
                    ),
                    row_shares=[0.55, 0.45],
                ),
                column_shares=[0.72, 0.28],
            ),
            collapse_panels=True,
        )
        rr_module.send_blueprint(blueprint)
        _PERCEPTION_BLUEPRINT_SENT = True
    except Exception as exc:
        print(f"[Perception Demo] Failed to send Rerun blueprint: {exc}")


def _render_detection_overlay(frame_rgb: Any, detections: List["Detection"]) -> Any:
    if cv2 is None or frame_rgb is None:
        return frame_rgb

    overlay_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR).copy()
    for det in detections:
        bbox = det.bbox
        x, y = int(bbox.x), int(bbox.y)
        w, h = int(bbox.width), int(bbox.height)
        color = (0, 0, 255) if "red" in det.label else (255, 0, 0)
        cv2.rectangle(overlay_bgr, (x, y), (x + w, y + h), color, 2)
        cv2.putText(
            overlay_bgr,
            f"{det.label} {det.confidence:.2f}",
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )
    return cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)


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


@dataclass
class BBox:
    x: float
    y: float
    width: float
    height: float


@dataclass
class Image:
    frame: Any
    frame_id: int


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: BBox


@io
@dataclass
class CameraData:
    image: Image
    mode: str = "unknown"

    def log_to_rerun(self, path: str) -> None:
        if rr is None:
            return
        rr.log(f"{path}/image", rr.Image(self.image.frame))
        rr.log(f"{path}/frame_id", rr.TextLog(str(self.image.frame_id)))
        rr.log(f"{path}/mode", rr.TextLog(self.mode))


@io
@dataclass
class DetectionResults:
    image: Image
    detections: List[Detection]
    mode: str = "unknown"

    def log_to_rerun(self, path: str) -> None:
        if rr is None:
            return

        rr.log(f"{path}/image", rr.Image(self.image.frame))
        rr.log(f"{path}/overlay", rr.Image(_render_detection_overlay(self.image.frame, self.detections)))
        rr.log(f"{path}/count", rr.Scalars([len(self.detections)]))
        rr.log(f"{path}/mode", rr.TextLog(self.mode))
        if not self.detections:
            rr.log(f"{path}/bbox", rr.Boxes2D([], labels=[]))
            return

        boxes = []
        labels = []
        class_ids = []
        for det in self.detections:
            bbox = det.bbox
            boxes.append([bbox.x, bbox.y, bbox.width, bbox.height])
            labels.append(f"{det.label} {det.confidence:.2f}")
            class_ids.append(1 if "red" in det.label else 2)

        rr.log(
            f"{path}/bbox",
            rr.Boxes2D(
                array=np.array(boxes),
                array_format=rr.Box2DFormat.XYWH,
                labels=labels,
                class_ids=class_ids,
            ),
        )


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

    def reset(self) -> None:
        _require_demo_deps()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.rr is not None:
            _send_perception_blueprint(self.rr)
        self.frame_count = 0
        self._initialized = True
        self.mode = "mock"
        if self.use_real_camera and cv2 is not None:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.mode = "real"
                    print(f"[CameraSource] Using real camera (index {self.camera_index})")
                else:
                    print("[CameraSource] Camera read failed, using mock")
                    self.cap.release()
                    self.cap = None
            else:
                print("[CameraSource] No camera found, using mock")

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
        _require_demo_deps()
        self.frame_count += 1

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
        cv2.rectangle(frame, (x, 60), (x + 80, 140), (255, 0, 0), -1)
        cv2.rectangle(frame, (60, y), (140, y + 80), (0, 0, 255), -1)
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

    def step(self, input: CameraData) -> DetectionResults:
        _require_demo_deps()
        detections: List[Detection] = []
        frame = input.image.frame

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
                "frame_id": int(input.image.frame_id),
                "count": len(filtered),
                "labels": labels,
                "max_confidence": float(max_confidence) if filtered else 0.0,
                "empty": len(filtered) == 0,
            },
        )
        return DetectionResults(image=input.image, detections=filtered, mode=str(input.mode or "unknown"))

    def _detect_from_mask(self, mask: Any, label: str) -> List[Detection]:
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
    def __init__(self, *, show_window: bool = False) -> None:
        super().__init__()
        self.show_window = bool(show_window)

    def reset(self) -> None:
        if self.show_window and cv2 is not None:
            try:
                cv2.namedWindow("Perception Demo", cv2.WINDOW_NORMAL)
                cv2.resizeWindow("Perception Demo", 1280, 720)
            except Exception as exc:
                print(f"[DisplayFlow] Failed to create OpenCV window, disabling UI: {exc}")
                self.show_window = False

    def finalize(self) -> None:
        if self.show_window and cv2 is not None:
            cv2.destroyAllWindows()

    def step(self, input: DetectionResults) -> None:
        if not input.image:
            return None

        frame_id = input.image.frame_id
        detections = input.detections or []
        frame = input.image.frame
        if detections:
            labels = [row.label for row in detections]
            confs = [f"{row.confidence:.2f}" for row in detections]
            print(f"  Frame {frame_id}: {len(detections)} objects - {list(zip(labels, confs))}")
        else:
            print(f"  Frame {frame_id}: No objects")

        if self.show_window and cv2 is not None:
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


def build_tutorial_perception_pipeline(
    *,
    use_real_camera: bool = True,
    show_window: bool = False,
    stream_rerun: bool = False,
    min_confidence: float = 0.6,
    camera_width: int = 640,
    camera_height: int = 480,
) -> Pipeline:
    del stream_rerun  # Reserved for future runtime-level visualization toggles.
    pipe = Pipeline("tutorial.perception")
    with pipe:
        camera = CameraSource(
            use_real_camera=use_real_camera,
            width=camera_width,
            height=camera_height,
        ) @ Rate(hz=30)
        detector = ColorDetector(min_confidence=min_confidence) @ Trigger("image")
        display = DisplayFlow(show_window=show_window) @ Rate(hz=3)
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
    stream_rerun: bool = False,
    min_confidence: float = 0.6,
    camera_width: int = 640,
    camera_height: int = 480,
) -> Pipeline:
    return build_tutorial_perception_pipeline(
        use_real_camera=use_real_camera,
        show_window=show_window,
        stream_rerun=stream_rerun,
        min_confidence=min_confidence,
        camera_width=camera_width,
        camera_height=camera_height,
    )


def build_record_pipeline() -> tuple[Pipeline, object]:
    pipe = Pipeline("tutorial.perception.record")
    camera = CameraSource(use_real_camera=True, width=640, height=480) @ Rate(hz=20)
    drain = Drain() @ Trigger("image")
    pipe.connect(camera, drain, sync=Latest())
    return pipe, camera


def build_replay_pipeline(*, show_window: bool) -> tuple[Pipeline, object]:
    pipe = Pipeline("tutorial.perception.replay")
    camera = CameraSource(use_real_camera=False, width=640, height=480) @ Rate(hz=20)
    detector = ColorDetector(min_confidence=0.6) @ Trigger("image")
    display = DisplayFlow(show_window=show_window) @ Rate(hz=20)
    pipe.connect(camera, detector, sync=Latest())
    pipe.connect(detector, display, sync=Latest())
    return pipe, camera


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


def load_camera_buffer_from_mcap(path: Path) -> list[tuple[float, CameraData]]:
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
    return buffer


__all__ = [
    "BBox",
    "CameraData",
    "CameraSource",
    "ColorDetector",
    "Detection",
    "DetectionResults",
    "DisplayFlow",
    "Image",
    "build_record_pipeline",
    "build_replay_pipeline",
    "build_tutorial_perception_pipeline",
    "emit_replay_finished",
    "emit_replay_started",
    "load_camera_buffer_from_mcap",
]
