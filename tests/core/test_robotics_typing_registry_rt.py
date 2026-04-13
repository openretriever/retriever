from __future__ import annotations

from retriever import get_type
from retriever.flow import Flow
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




def make_pose_stamped() -> PoseStamped:
    return PoseStamped(
        header=Header(stamp_ns=1, frame_id='map'),
        pose=SE3Pose(
            position=Vector3(1.0, 2.0, 3.0),
            orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        ),
    )


class PoseEcho(Flow[PoseStamped, PoseStamped]):
    def step(self, pose: PoseStamped) -> PoseStamped:
        return pose


def test_spatial_primitives_work_in_direct_flow_signatures() -> None:
    assert PoseEcho._input_types == (PoseStamped,)
    assert PoseEcho._output_types == (PoseStamped,)

    pose = make_pose_stamped()
    echoed = PoseEcho().step(pose)
    assert echoed == pose
