"""
Perception data types and visualization helpers for the Retriever tutorial demos.

Provides reusable building blocks:
- Data types: BBox, Image, Detection, CameraData, DetectionResults
- Rerun blueprint helper: send_perception_blueprint
- OpenCV helpers: optional_cv2, render_detection_overlay

The actual Flow subclasses (CameraSource, ColorDetector, DisplayFlow) and pipeline
factories live in examples/shared/perception_flows.py so they stay close to the
examples that use them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Literal, Optional

try:
    import numpy as np  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]

try:
    import rerun as _rr_module  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    _rr_module = None

from retriever.flow import io

PerceptionDisplayMode = Literal["none", "stdout", "cv2"]
PERCEPTION_DISPLAY_MODES: tuple[PerceptionDisplayMode, ...] = ("none", "stdout", "cv2")

_CV2_MODULE: Any = None
_CV2_ATTEMPTED = False
_PERCEPTION_BLUEPRINT_SENT = False


def optional_cv2() -> Any:
    """Lazily import cv2 — returns None if not installed."""
    global _CV2_MODULE, _CV2_ATTEMPTED
    if not _CV2_ATTEMPTED:
        _CV2_ATTEMPTED = True
        try:
            import cv2 as _cv2  # type: ignore[import-not-found]
        except Exception:
            _CV2_MODULE = None
        else:
            _CV2_MODULE = _cv2
    return _CV2_MODULE


def require_demo_deps(*, require_cv2: bool = False) -> None:
    """Raise a clear error when demo dependencies (numpy / cv2) are missing."""
    if np is None:
        raise RuntimeError(
            "retriever.lib.perception requires demo dependencies (numpy). "
            "Install retriever with the demo extras: pip install 'retriever[demo]'"
        )
    if require_cv2 and optional_cv2() is None:
        raise RuntimeError(
            "retriever.lib.perception requires OpenCV for live camera capture and cv2 windows. "
            "Install retriever with the demo extras: pip install 'retriever[demo]'"
        )


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


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


def render_detection_overlay(frame_rgb: Any, detections: List[Detection]) -> Any:
    """Draw bounding boxes onto an RGB frame and return the annotated RGB frame."""
    cv2 = optional_cv2()
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


@io
class CameraData:
    image: Image
    mode: str = "unknown"

    def log_to_rerun(self, path: str) -> None:
        rr = _rr_module
        if rr is None:
            return
        rr.log(f"{path}/image", rr.Image(self.image.frame))
        rr.log(f"{path}/frame_id", rr.TextLog(str(self.image.frame_id)))
        rr.log(f"{path}/mode", rr.TextLog(self.mode))


@io
class DetectionResults:
    image: Image
    detections: List[Detection]
    mode: str = "unknown"

    def log_to_rerun(self, path: str) -> None:
        rr = _rr_module
        if rr is None:
            return

        rr.log(f"{path}/image", rr.Image(self.image.frame))
        rr.log(f"{path}/overlay", rr.Image(render_detection_overlay(self.image.frame, self.detections)))
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


# ---------------------------------------------------------------------------
# Rerun blueprint
# ---------------------------------------------------------------------------


def send_perception_blueprint(rr_module: Any) -> None:
    """
    Send a pre-built Rerun blueprint for the tutorial perception pipeline.

    Idempotent — only sends once per process. Safe to call from reset() of a Flow.
    Node IDs in the entity paths come from the class names: CameraSource, ColorDetector.
    """
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
        # Spatial2DView is correct for rr.Image data (TensorView is for rr.Tensor).
        # Fall back to TensorView for older Rerun SDK versions that lack Spatial2DView.
        # Spatial2DView requires origin to be the direct parent (or the entity itself)
        # in the spatial tree — wildcard origins like "/" or "/flows" do not work.
        _ImageView = getattr(rrb, "Spatial2DView", None) or getattr(rrb, "TensorView")
        blueprint = rrb.Blueprint(
            rrb.Horizontal(
                rrb.Tabs(
                    _ImageView(
                        origin="/flows/ColorDetector/output",
                        name="Detections",
                    ),
                    _ImageView(
                        origin="/flows/CameraSource/output",
                        name="Raw Camera",
                    ),
                    active_tab="Detections",
                ),
                rrb.Vertical(
                    rrb.TimeSeriesView(
                        origin="/flows/ColorDetector/output/count",
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


__all__ = [
    "BBox",
    "CameraData",
    "Detection",
    "DetectionResults",
    "Image",
    "PERCEPTION_DISPLAY_MODES",
    "PerceptionDisplayMode",
    "optional_cv2",
    "render_detection_overlay",
    "require_demo_deps",
    "send_perception_blueprint",
]
