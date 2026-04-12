from __future__ import annotations

import numpy as np
import pytest

from retriever import get_type, get_type_info, resolve_schema_ref
from retriever.types.spatial import Header
from retriever.types.perception import (
    BBox2D,
    CameraIntrinsics,
    CompressedImage2D,
    Detection2D,
    DetectionBatch,
    EncodedVideo,
    Image2D,
    PointCloud3D,
    PointTarget2D,
    SegmentationMask2D,
    validate_camera_intrinsics,
    validate_compressed_image2d,
    validate_encoded_video,
    validate_image2d,
    validate_pointcloud3d,
    validate_segmentation_mask2d,
)
from retriever.types.perception.v1 import Image2D as PinnedImage2D
from retriever.types import SchemaRef


def test_perception_package_exports_canonical_surface() -> None:
    frame = Image2D(data=np.zeros((8, 10, 3), dtype=np.uint8), encoding='rgb8')
    assert frame.height == 8
    assert frame.width == 10
    assert frame.channels == 3
    assert PinnedImage2D is Image2D


def test_perception_types_register_with_registry() -> None:
    assert get_type('Image2D') is Image2D
    assert get_type('DetectionBatch') is DetectionBatch
    info = get_type_info('PointCloud3D')
    assert info.namespace == 'perception'
    assert info.schema_ref == SchemaRef(name='perception/PointCloud3D', version='v1', encoding='python')


def test_resolve_schema_ref_supports_perception_types() -> None:
    msg = DetectionBatch(
        detections=(
            Detection2D(label='red', bbox=BBox2D(x=1.0, y=2.0, width=3.0, height=4.0), confidence=0.9),
        ),
        header=Header(stamp_ns=1, frame_id='camera'),
    )
    assert resolve_schema_ref(msg) == SchemaRef(name='perception/DetectionBatch', version='v1', encoding='python')


def test_validate_image_and_compressed_image() -> None:
    validate_image2d(Image2D(data=np.zeros((4, 5), dtype=np.uint8), encoding='mono8'))
    validate_compressed_image2d(CompressedImage2D(data=b'abc', format='jpeg'))

    with pytest.raises(ValueError):
        validate_image2d(Image2D(data=np.zeros((2, 2, 2, 2), dtype=np.uint8), encoding='rgb8'))
    with pytest.raises(ValueError):
        validate_compressed_image2d(CompressedImage2D(data=b'', format='jpeg'))


def test_validate_video_pointcloud_and_mask() -> None:
    validate_encoded_video(EncodedVideo(uri='file:///tmp/demo.mp4', container='mp4', frame_rate_hz=30.0))
    validate_camera_intrinsics(CameraIntrinsics(width=10, height=8, fx=100.0, fy=100.0, cx=5.0, cy=4.0))
    validate_pointcloud3d(PointCloud3D(points=np.zeros((4, 3), dtype=np.float32)))
    validate_segmentation_mask2d(SegmentationMask2D(mask=np.zeros((5, 6), dtype=np.int32), label_map={0: 'bg'}))

    with pytest.raises(ValueError):
        validate_encoded_video(EncodedVideo(container='mp4'))
    with pytest.raises(ValueError):
        validate_camera_intrinsics(CameraIntrinsics(width=0, height=8, fx=100.0, fy=100.0, cx=5.0, cy=4.0))
    with pytest.raises(ValueError):
        validate_pointcloud3d(PointCloud3D(points=np.zeros((4, 2), dtype=np.float32)))
    with pytest.raises(ValueError):
        validate_segmentation_mask2d(SegmentationMask2D(mask=np.zeros((5, 6, 1), dtype=np.int32)))


def test_point_target2d_is_simple_optional_boundary() -> None:
    target = PointTarget2D(label='red', x_norm=0.2, y_norm=0.7, confidence=0.8)
    assert target.label == 'red'
