from __future__ import annotations

import pytest

from retriever.robotics_typing import (
    Header,
    JointState,
    PoseStamped,
    Quaternion,
    SE3Pose,
    Vector3,
    validate_joint_state,
    validate_pose_stamped,
)


def test_pose_stamped_valid_payload_passes() -> None:
    msg = PoseStamped(
        header=Header(stamp_ns=100, frame_id="map", source="unit-test"),
        pose=SE3Pose(
            position=Vector3(0.0, 0.0, 0.0),
            orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        ),
    )
    validate_pose_stamped(msg)


def test_pose_stamped_rejects_empty_frame() -> None:
    msg = PoseStamped(
        header=Header(stamp_ns=100, frame_id="", source="unit-test"),
        pose=SE3Pose(
            position=Vector3(0.0, 0.0, 0.0),
            orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        ),
    )
    with pytest.raises(ValueError, match="frame_id"):
        validate_pose_stamped(msg)


def test_pose_stamped_rejects_non_positive_timestamp() -> None:
    msg = PoseStamped(
        header=Header(stamp_ns=0, frame_id="map", source="unit-test"),
        pose=SE3Pose(
            position=Vector3(0.0, 0.0, 0.0),
            orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        ),
    )
    with pytest.raises(ValueError, match="stamp_ns"):
        validate_pose_stamped(msg)


def test_pose_stamped_rejects_non_unit_quaternion() -> None:
    msg = PoseStamped(
        header=Header(stamp_ns=100, frame_id="map", source="unit-test"),
        pose=SE3Pose(
            position=Vector3(0.0, 0.0, 0.0),
            orientation=Quaternion(1.0, 0.0, 0.0, 1.0),
        ),
    )
    with pytest.raises(ValueError, match="unit-norm"):
        validate_pose_stamped(msg)


def test_joint_state_alignment_check() -> None:
    good = JointState(
        names=("j1", "j2"),
        positions=(0.0, 0.1),
        velocities=(0.0, 0.0),
        efforts=(0.0, 0.0),
    )
    validate_joint_state(good)

    bad = JointState(
        names=("j1", "j2"),
        positions=(0.0,),
        velocities=(0.0, 0.0),
        efforts=(0.0, 0.0),
    )
    with pytest.raises(ValueError, match="align"):
        validate_joint_state(bad)
