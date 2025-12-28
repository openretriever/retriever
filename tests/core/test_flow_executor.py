"""
Tests for Flow and LocalExecutor - with Robotics Examples

These tests demonstrate how to use the Flow abstraction for building
robotics pipelines. Each test shows a common robotics pattern and how
to implement it with Flows.

The examples progress from simple operations to complex multi-stage
pipelines that you might find in real robotics systems.

We use the synchronous executor (execute_sync) for simplicity and clarity.
For performance-critical applications, you can use execute_async instead.
"""

import pytest
from dataclasses import dataclass
from typing import List, Tuple

from retriever.flow import Flow, Arrow  # Flow is new, Arrow for backward compatibility
from retriever.executor import LocalExecutor


# ========================= Mock Robotics Functions =========================
# These simulate real robotics functions you might have in your system

@dataclass
class Detection:
    """A detected object with confidence score."""
    object_id: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height


@dataclass 
class Pose3D:
    """A 3D pose estimate."""
    x: float
    y: float
    z: float
    confidence: float


def detect_objects_yolo(image_data: bytes) -> List[Detection]:
    """Mock YOLO object detection."""
    # In real code: return yolo_model.predict(image_data)
    return [
        Detection("cup", 0.95, (100, 100, 50, 80)),
        Detection("bottle", 0.87, (200, 150, 30, 100))
    ]


def estimate_poses_from_detections(detections: List[Detection]) -> List[Pose3D]:
    """Mock 6D pose estimation from detections."""
    # In real code: return pose_estimator.estimate(detections)
    return [
        Pose3D(0.5, 0.3, 0.8, 0.9),  # cup pose
        Pose3D(0.7, 0.1, 0.9, 0.85)  # bottle pose
    ]


def filter_confident_detections(detections: List[Detection]) -> List[Detection]:
    """Filter detections by confidence threshold."""
    return [d for d in detections if d.confidence > 0.9]


def process_left_camera(timestamp: float) -> bytes:
    """Mock left camera processing."""
    return b"left_camera_image_data"


def process_right_camera(timestamp: float) -> bytes:
    """Mock right camera processing."""
    return b"right_camera_image_data"


# ========================= Simple Flow Tests =========================


def test_simple_perception_flow():
    """
    Test: Single perception module
    
    This shows how to wrap a simple function (object detection) into a Flow.
    Common pattern: wrap existing perception models for use in pipelines.
    """
    executor = LocalExecutor()
    
    # Wrap the detection function as a Flow (new preferred syntax)
    detection_flow = Flow.from_module(detect_objects_yolo)
    
    # Execute with mock image data (simple and reliable)
    mock_image = b"fake_image_data"
    detections = executor.run(detection_flow, mock_image)
    
    # Verify we get expected detections
    assert len(detections) == 2
    assert detections[0].object_id == "cup"
    assert detections[1].object_id == "bottle"


def test_perception_pipeline():
    """
    Test: Chained perception pipeline
    
    This demonstrates the classic robotics pattern:
    Raw sensor data → Object Detection → Pose Estimation
    
    Shows how .then() creates sequential processing pipelines.
    """
    executor = LocalExecutor()
    
    # Build a 2-stage perception pipeline (Flow terminology)
    detection_flow = Flow.from_module(detect_objects_yolo)
    pose_estimation_flow = Flow.from_module(estimate_poses_from_detections)
    
    # Chain them: detection → pose estimation
    perception_pipeline = detection_flow.then(pose_estimation_flow)
    
    # Execute the full pipeline
    mock_image = b"fake_image_data"
    poses = executor.run(perception_pipeline, mock_image)
    
    # Verify we get 3D poses
    assert len(poses) == 2
    assert isinstance(poses[0], Pose3D)
    assert poses[0].x == 0.5  # cup pose


def test_multi_camera_processing():
    """
    Test: Multi-camera processing
    
    This demonstrates fanout() for processing multiple data streams.
    Same timestamp goes to both cameras.
    
    Note: With the simple executor, this runs sequentially (still correct).
    For parallel execution, use DoraExecutor (planned).
    
    Common use cases:
    - Stereo vision (left + right cameras)
    - Multi-view object detection
    - Sensor fusion from multiple sources
    """
    executor = LocalExecutor()
    
    # Create flows for left and right camera processing
    left_camera_flow = Flow.from_module(process_left_camera)
    right_camera_flow = Flow.from_module(process_right_camera)
    
    # Fanout: same timestamp → both cameras
    stereo_flow = left_camera_flow.fanout(right_camera_flow)
    
    # Execute - both cameras process the same timestamp
    timestamp = 1234567890.0
    (left_data, right_data) = executor.run(stereo_flow, timestamp)
    
    # Verify both cameras produced data
    assert left_data == b"left_camera_image_data"
    assert right_data == b"right_camera_image_data"


def test_complex_robotics_pipeline():
    """
    Test: Complex multi-stage robotics pipeline
    
    This demonstrates a realistic robotics pipeline:
    1. Multi-camera capture
    2. Object detection on both images
    3. Confidence filtering
    4. Pose estimation
    
    Shows how to combine .then() and .fanout() for complex workflows.
    """
    executor = LocalExecutor()
    
    # Stage 1: Multi-camera capture
    left_cam = Flow.from_module(process_left_camera)
    right_cam = Flow.from_module(process_right_camera)
    stereo_capture = left_cam.fanout(right_cam)
    
    # Stage 2: Object detection on both images
    detect_left = Flow.from_module(lambda data: detect_objects_yolo(data[0]))  # left image
    detect_right = Flow.from_module(lambda data: detect_objects_yolo(data[1]))  # right image
    dual_detection = detect_left.fanout(detect_right)
    
    # Stage 3: Merge and filter detections
    def merge_and_filter(detection_pair: Tuple[List[Detection], List[Detection]]) -> List[Detection]:
        left_dets, right_dets = detection_pair
        all_detections = left_dets + right_dets
        return filter_confident_detections(all_detections)
    
    filter_flow = Flow.from_module(merge_and_filter)
    
    # Stage 4: Pose estimation
    pose_flow = Flow.from_module(estimate_poses_from_detections)
    
    # Compose the full pipeline
    full_pipeline = (
        stereo_capture           # timestamp → (left_data, right_data)
        .then(dual_detection)    # (left_data, right_data) → (left_dets, right_dets)
        .then(filter_flow)       # (left_dets, right_dets) → filtered_dets
        .then(pose_flow)         # filtered_dets → poses
    )
    
    # Execute the complete robotics pipeline
    timestamp = 1234567890.0
    final_poses = executor.run(full_pipeline, timestamp)
    
    # Verify the pipeline worked end-to-end
    assert len(final_poses) == 2  # Both cup and bottle from dual cameras
    assert final_poses[0].confidence >= 0.9  # High confidence


def test_redundant_processing_for_robustness():
    """
    Test: Redundant detection algorithms for robustness
    
    This shows a common robotics pattern: run multiple algorithms in parallel
    and fuse their results for better reliability.
    
    Real use case: Run YOLO + Faster R-CNN on the same image, then fuse detections.
    """
    executor = LocalExecutor()
    
    # Two different detection algorithms
    def detect_objects_rcnn(image_data: bytes) -> List[Detection]:
        """Mock Faster R-CNN detection with different confidence."""
        return [
            Detection("cup", 0.92, (102, 98, 48, 82)),  # Slightly different bbox
            Detection("book", 0.88, (300, 200, 60, 40))  # Different object
        ]
    
    def fuse_detections(detection_pair: Tuple[List[Detection], List[Detection]]) -> List[Detection]:
        """Simple fusion: combine all detections."""
        yolo_dets, rcnn_dets = detection_pair
        return yolo_dets + rcnn_dets
    
    # Create parallel detection flows
    yolo_flow = Flow.from_module(detect_objects_yolo)
    rcnn_flow = Flow.from_module(detect_objects_rcnn)
    fusion_flow = Flow.from_module(fuse_detections)
    
    # Parallel detection + fusion pipeline
    robust_detection = yolo_flow.fanout(rcnn_flow).then(fusion_flow)
    
    # Execute redundant detection
    mock_image = b"fake_image_data"
    all_detections = executor.run(robust_detection, mock_image)
    
    # Verify we get detections from both algorithms
    assert len(all_detections) == 4  # 2 from YOLO + 2 from R-CNN
    object_ids = [d.object_id for d in all_detections]
    assert "cup" in object_ids  # From both algorithms
    assert "bottle" in object_ids  # From YOLO
    assert "book" in object_ids  # From R-CNN


# ========================= Backward Compatibility Tests =========================


def test_arrow_backward_compatibility():
    """
    Test: Backward compatibility with Arrow terminology
    
    This ensures existing Arrow-based code still works with deprecation warnings.
    """
    executor = LocalExecutor()
    
    # Old Arrow syntax (should work but show deprecation warnings)
    with pytest.warns(DeprecationWarning):
        detection_arrow = Arrow.arr(detect_objects_yolo)
    
    # Should still execute correctly with old execute_sync method
    mock_image = b"fake_image_data"
    detections = executor.execute_sync(detection_arrow, mock_image)  # Backward compatibility
    
    assert len(detections) == 2
    assert detections[0].object_id == "cup"


# ========================= Basic Function Tests =========================

def add_one(x: int) -> int:
    return x + 1

def double(x: int) -> int:
    return x * 2

def to_str(x: int) -> str:
    return str(x)

def test_simple_flow():
    """Test basic Flow functionality with simple functions."""
    executor = LocalExecutor()

    simple_flow = Flow.from_module(add_one)
    result = executor.run(simple_flow, 5)
    assert result == 6

def test_then_composition():
    """Test sequential composition with .then()"""
    executor = LocalExecutor()

    pipeline = Flow.from_module(add_one).then(Flow.from_module(double))
    result = executor.run(pipeline, 5)
    assert result == 12  # (5 + 1) * 2

def test_fanout_composition():
    """Test parallel composition with .fanout()"""
    executor = LocalExecutor()

    parallel = Flow.from_module(add_one).fanout(Flow.from_module(double))
    result = executor.run(parallel, 5)
    assert result == (6, 10)  # (5 + 1, 5 * 2)

def test_complex_composition():
    """Test complex composition combining .then() and .fanout()"""
    executor = LocalExecutor()

    # ((x + 1), (x * 2)) → str(first) + str(second)
    combine = Flow.from_module(lambda pair: f"{pair[0]}_{pair[1]}")

    complex_flow = (
        Flow.from_module(add_one).fanout(Flow.from_module(double))
        .then(combine)
    )

    result = executor.run(complex_flow, 5)
    assert result == "6_10" 