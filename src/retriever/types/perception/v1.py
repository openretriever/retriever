"""Canonical perception/media payload standard v1.

This package is intentionally small. It defines reusable media/perception
primitives, not every model-specific packet shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Iterable

import numpy as np
from numpy.typing import NDArray

from retriever.registry.types import register_type
from retriever.types.spatial import Header

_PERCEPTION_CATEGORY: Final[str] = "perception"
_PERCEPTION_NAMESPACE: Final[str] = "perception"
_PERCEPTION_VERSION: Final[str] = "v1"


def _register_perception_type(
    name: str,
    *,
    description: str,
    tags: Iterable[str],
):
    return register_type(
        name,
        description=description,
        category=_PERCEPTION_CATEGORY,
        namespace=_PERCEPTION_NAMESPACE,
        version=_PERCEPTION_VERSION,
        kind="payload",
        tags=tags,
        schema_name=f"perception/{name}",
        schema_version=_PERCEPTION_VERSION,
    )


@_register_perception_type(
    "Image2D",
    description="Decoded 2D image frame payload",
    tags=["perception", "v1", "image", "frame"],
)
@dataclass(frozen=True)
class Image2D:
    data: NDArray
    encoding: str = "rgb8"
    header: Header | None = None

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    @property
    def channels(self) -> int:
        if self.data.ndim == 2:
            return 1
        return int(self.data.shape[2])


@_register_perception_type(
    "CompressedImage2D",
    description="Compressed single-frame image payload",
    tags=["perception", "v1", "image", "compressed"],
)
@dataclass(frozen=True)
class CompressedImage2D:
    data: bytes
    format: str = "jpeg"
    header: Header | None = None
    width: int | None = None
    height: int | None = None


@_register_perception_type(
    "EncodedVideo",
    description="Encoded multi-frame video artifact payload",
    tags=["perception", "v1", "video", "encoded"],
)
@dataclass(frozen=True)
class EncodedVideo:
    data: bytes | None = None
    uri: str | None = None
    container: str = "mp4"
    codec: str | None = None
    header: Header | None = None
    width: int | None = None
    height: int | None = None
    frame_rate_hz: float | None = None


@_register_perception_type(
    "CameraIntrinsics",
    description="Camera intrinsics for image-to-geometry transforms",
    tags=["perception", "v1", "camera", "intrinsics"],
)
@dataclass(frozen=True)
class CameraIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    distortion_model: str | None = None
    distortion: tuple[float, ...] = ()


@_register_perception_type(
    "PointCloud3D",
    description="3D point cloud payload",
    tags=["perception", "v1", "pointcloud", "geometry"],
)
@dataclass(frozen=True)
class PointCloud3D:
    points: NDArray
    header: Header | None = None
    colors: NDArray | None = None
    fields: tuple[str, ...] = ("x", "y", "z")

    @property
    def count(self) -> int:
        return int(self.points.shape[0])


@_register_perception_type(
    "BBox2D",
    description="Axis-aligned 2D bounding box",
    tags=["perception", "v1", "bbox", "geometry"],
)
@dataclass(frozen=True)
class BBox2D:
    x: float
    y: float
    width: float
    height: float

    def area(self) -> float:
        return max(self.width, 0.0) * max(self.height, 0.0)


@_register_perception_type(
    "Detection2D",
    description="Single 2D detection payload",
    tags=["perception", "v1", "detection", "2d"],
)
@dataclass(frozen=True)
class Detection2D:
    label: str
    bbox: BBox2D
    confidence: float | None = None
    class_id: int | None = None
    track_id: str | None = None
    centroid_x: float | None = None
    centroid_y: float | None = None


@_register_perception_type(
    "DetectionBatch",
    description="Batch of 2D detections for one frame or observation",
    tags=["perception", "v1", "detection", "batch"],
)
@dataclass(frozen=True)
class DetectionBatch:
    detections: tuple[Detection2D, ...] = ()
    header: Header | None = None


@_register_perception_type(
    "SegmentationMask2D",
    description="2D segmentation mask with optional class-to-label mapping",
    tags=["perception", "v1", "segmentation", "mask"],
)
@dataclass(frozen=True)
class SegmentationMask2D:
    mask: NDArray
    header: Header | None = None
    label_map: dict[int, str] = field(default_factory=dict)

    @property
    def height(self) -> int:
        return int(self.mask.shape[0])

    @property
    def width(self) -> int:
        return int(self.mask.shape[1])


@_register_perception_type(
    "PointTarget2D",
    description="Normalized 2D target point for pointing and grounding flows",
    tags=["perception", "v1", "point", "target"],
)
@dataclass(frozen=True)
class PointTarget2D:
    label: str | None = None
    x_norm: float | None = None
    y_norm: float | None = None
    confidence: float | None = None
    header: Header | None = None


def validate_image2d(msg: Image2D) -> None:
    if msg.data.ndim not in (2, 3):
        raise ValueError("Image2D.data must be a 2D or 3D ndarray")
    if msg.data.size == 0:
        raise ValueError("Image2D.data must be non-empty")
    if not msg.encoding:
        raise ValueError("Image2D.encoding must be non-empty")


def validate_compressed_image2d(msg: CompressedImage2D) -> None:
    if not msg.data:
        raise ValueError("CompressedImage2D.data must be non-empty")
    if not msg.format:
        raise ValueError("CompressedImage2D.format must be non-empty")


def validate_encoded_video(msg: EncodedVideo) -> None:
    if not msg.data and not msg.uri:
        raise ValueError("EncodedVideo requires either data or uri")
    if msg.frame_rate_hz is not None and msg.frame_rate_hz <= 0:
        raise ValueError("EncodedVideo.frame_rate_hz must be > 0 when provided")
    if msg.width is not None and msg.width <= 0:
        raise ValueError("EncodedVideo.width must be > 0 when provided")
    if msg.height is not None and msg.height <= 0:
        raise ValueError("EncodedVideo.height must be > 0 when provided")


def validate_camera_intrinsics(msg: CameraIntrinsics) -> None:
    if msg.width <= 0 or msg.height <= 0:
        raise ValueError("CameraIntrinsics width/height must be > 0")
    if msg.fx <= 0 or msg.fy <= 0:
        raise ValueError("CameraIntrinsics fx/fy must be > 0")


def validate_pointcloud3d(msg: PointCloud3D) -> None:
    if msg.points.ndim != 2 or msg.points.shape[1] < 3:
        raise ValueError("PointCloud3D.points must be an Nx3-or-greater ndarray")
    if msg.colors is not None and msg.colors.shape[0] != msg.points.shape[0]:
        raise ValueError("PointCloud3D.colors must align with points by row count")


def validate_segmentation_mask2d(msg: SegmentationMask2D) -> None:
    if msg.mask.ndim != 2:
        raise ValueError("SegmentationMask2D.mask must be a 2D ndarray")
    if msg.mask.size == 0:
        raise ValueError("SegmentationMask2D.mask must be non-empty")


__all__ = [
    "BBox2D",
    "CameraIntrinsics",
    "CompressedImage2D",
    "Detection2D",
    "DetectionBatch",
    "EncodedVideo",
    "Image2D",
    "PointCloud3D",
    "PointTarget2D",
    "SegmentationMask2D",
    "validate_camera_intrinsics",
    "validate_compressed_image2d",
    "validate_encoded_video",
    "validate_image2d",
    "validate_pointcloud3d",
    "validate_segmentation_mask2d",
]
