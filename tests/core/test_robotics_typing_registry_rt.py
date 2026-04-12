from __future__ import annotations

from retriever import get_type
from retriever.types.spatial import (
    Header,
    JointState,
    PoseStamped,
    Quaternion,
    SE3Pose,
    Twist,
    TwistStamped,
    Vector3,
    Wrench,
    WrenchStamped,
)
from retriever.types.spatial.v1 import PoseStamped as PinnedPoseStamped
from retriever.types.spatial.v1 import SE3Pose as PinnedSE3Pose


def test_registry_lookup_for_v1_types() -> None:
    expected = {
        'Header': Header,
        'Vector3': Vector3,
        'Quaternion': Quaternion,
        'SE3Pose': SE3Pose,
        'PoseStamped': PoseStamped,
        'Twist': Twist,
        'TwistStamped': TwistStamped,
        'Wrench': Wrench,
        'WrenchStamped': WrenchStamped,
        'JointState': JointState,
    }
    for name, cls in expected.items():
        assert get_type(name) is cls


def test_public_package_surface_matches_pinned_v1() -> None:
    assert PoseStamped is PinnedPoseStamped
    assert SE3Pose is PinnedSE3Pose


