"""Mirror-native robotics typing standard v1."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Final

from retriever.types_registry import register_type

_ROBOTICS_CATEGORY: Final[str] = "robotics"


@register_type(
    "Header",
    description="Header for stamped robotics payloads",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "header", "metadata"],
)
@dataclass(frozen=True)
class Header:
    stamp_ns: int
    frame_id: str
    source: str = "unknown"


@register_type(
    "Vector3",
    description="3D vector payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "geometry", "vector"],
)
@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float


@register_type(
    "Quaternion",
    description="Quaternion rotation payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "geometry", "quaternion"],
)
@dataclass(frozen=True)
class Quaternion:
    x: float
    y: float
    z: float
    w: float

    def norm(self) -> float:
        return sqrt(self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w)

    def is_unit(self, tol: float = 1e-3) -> bool:
        return abs(self.norm() - 1.0) <= tol


@register_type(
    "SE3Pose",
    description="SE(3) pose payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "geometry", "pose"],
)
@dataclass(frozen=True)
class SE3Pose:
    position: Vector3
    orientation: Quaternion


@register_type(
    "Twist",
    description="Spatial velocity payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "motion", "twist"],
)
@dataclass(frozen=True)
class Twist:
    linear: Vector3
    angular: Vector3


@register_type(
    "Wrench",
    description="Force and torque payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "force", "wrench"],
)
@dataclass(frozen=True)
class Wrench:
    force: Vector3
    torque: Vector3


@register_type(
    "JointState",
    description="Joint state payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "joint", "state"],
)
@dataclass(frozen=True)
class JointState:
    names: tuple[str, ...]
    positions: tuple[float, ...]
    velocities: tuple[float, ...]
    efforts: tuple[float, ...]

    def is_aligned(self) -> bool:
        n = len(self.names)
        return (
            len(self.positions) == n
            and len(self.velocities) == n
            and len(self.efforts) == n
        )


@register_type(
    "PoseStamped",
    description="Timestamped pose payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "pose", "stamped"],
)
@dataclass(frozen=True)
class PoseStamped:
    header: Header
    pose: SE3Pose


@register_type(
    "TwistStamped",
    description="Timestamped twist payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "twist", "stamped"],
)
@dataclass(frozen=True)
class TwistStamped:
    header: Header
    twist: Twist


@register_type(
    "WrenchStamped",
    description="Timestamped wrench payload",
    category=_ROBOTICS_CATEGORY,
    tags=["robotics", "v1", "wrench", "stamped"],
)
@dataclass(frozen=True)
class WrenchStamped:
    header: Header
    wrench: Wrench


def validate_header(header: Header) -> None:
    if not header.frame_id:
        raise ValueError("frame_id must be non-empty")
    if header.stamp_ns <= 0:
        raise ValueError("stamp_ns must be > 0")


def validate_quaternion(q: Quaternion, tol: float = 1e-3) -> None:
    if not q.is_unit(tol=tol):
        raise ValueError("orientation quaternion must be unit-norm")


def validate_pose_stamped(msg: PoseStamped) -> None:
    validate_header(msg.header)
    validate_quaternion(msg.pose.orientation)


def validate_joint_state(msg: JointState) -> None:
    if not msg.is_aligned():
        raise ValueError("joint state arrays must align by length")


__all__ = [
    "Header",
    "Vector3",
    "Quaternion",
    "SE3Pose",
    "PoseStamped",
    "Twist",
    "TwistStamped",
    "Wrench",
    "WrenchStamped",
    "JointState",
    "validate_header",
    "validate_quaternion",
    "validate_pose_stamped",
    "validate_joint_state",
]
