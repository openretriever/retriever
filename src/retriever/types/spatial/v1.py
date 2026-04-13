"""Canonical spatial payload standard v1."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Final, Iterable

from retriever.flow import io
from retriever.flow.io import compose
from retriever.registry.types import register_type

_SPATIAL_CATEGORY: Final[str] = "spatial"
_SPATIAL_NAMESPACE: Final[str] = "spatial"
_SPATIAL_VERSION: Final[str] = "v1"


def _register_spatial_type(
    name: str,
    *,
    description: str,
    tags: Iterable[str],
):
    return register_type(
        name,
        description=description,
        category=_SPATIAL_CATEGORY,
        namespace=_SPATIAL_NAMESPACE,
        version=_SPATIAL_VERSION,
        kind="payload",
        tags=tags,
        schema_name=f"spatial/{name}",
        schema_version=_SPATIAL_VERSION,
    )


@_register_spatial_type(
    "Header",
    description="Header for stamped spatial payloads",
    tags=["spatial", "v1", "header", "metadata"],
)
@io
@dataclass(frozen=True)
class Header:
    stamp_ns: int
    frame_id: str
    source: str = "unknown"


@_register_spatial_type(
    "Vector3",
    description="3D vector payload",
    tags=["spatial", "v1", "geometry", "vector"],
)
@io
@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float


@_register_spatial_type(
    "Quaternion",
    description="Quaternion rotation payload",
    tags=["spatial", "v1", "geometry", "quaternion"],
)
@io
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


SE3Pose = _register_spatial_type(
    "SE3Pose",
    description="SE(3) pose payload",
    tags=["spatial", "v1", "geometry", "pose"],
)(compose("SE3Pose", position=Vector3, orientation=Quaternion))

Twist = _register_spatial_type(
    "Twist",
    description="Spatial velocity payload",
    tags=["spatial", "v1", "motion", "twist"],
)(compose("Twist", linear=Vector3, angular=Vector3))

Wrench = _register_spatial_type(
    "Wrench",
    description="Force and torque payload",
    tags=["spatial", "v1", "force", "wrench"],
)(compose("Wrench", force=Vector3, torque=Vector3))


@_register_spatial_type(
    "JointState",
    description="Joint state payload",
    tags=["spatial", "v1", "joint", "state"],
)
@io
@dataclass(frozen=True)
class JointState:
    names: tuple[str, ...]
    positions: tuple[float, ...]
    velocities: tuple[float, ...]
    efforts: tuple[float, ...]

    def is_aligned(self) -> bool:
        if any(value is None for value in (self.names, self.positions, self.velocities, self.efforts)):
            return False
        n = len(self.names)
        return (
            len(self.positions) == n
            and len(self.velocities) == n
            and len(self.efforts) == n
        )


PoseStamped = _register_spatial_type(
    "PoseStamped",
    description="Timestamped pose payload",
    tags=["spatial", "v1", "pose", "stamped"],
)(compose("PoseStamped", header=Header, pose=SE3Pose))

TwistStamped = _register_spatial_type(
    "TwistStamped",
    description="Timestamped twist payload",
    tags=["spatial", "v1", "twist", "stamped"],
)(compose("TwistStamped", header=Header, twist=Twist))

WrenchStamped = _register_spatial_type(
    "WrenchStamped",
    description="Timestamped wrench payload",
    tags=["spatial", "v1", "wrench", "stamped"],
)(compose("WrenchStamped", header=Header, wrench=Wrench))


def validate_header(header: Header) -> None:
    if header.stamp_ns is None or header.stamp_ns <= 0:
        raise ValueError("stamp_ns must be > 0")
    if not header.frame_id:
        raise ValueError("frame_id must be non-empty")


def validate_quaternion(q: Quaternion, tol: float = 1e-3) -> None:
    if any(value is None for value in (q.x, q.y, q.z, q.w)):
        raise ValueError("orientation quaternion must set x, y, z, and w")
    if not q.is_unit(tol=tol):
        raise ValueError("orientation quaternion must be unit-norm")


def validate_pose_stamped(msg: PoseStamped) -> None:
    if msg.header is None or msg.pose is None:
        raise ValueError("PoseStamped requires header and pose")
    validate_header(msg.header)
    validate_quaternion(msg.pose.orientation)


def validate_joint_state(msg: JointState) -> None:
    if not msg.is_aligned():
        raise ValueError("joint state arrays must align by length and be fully specified")


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
