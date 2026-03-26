"""Robotics typing boundaries tutorial.

Covers:
1) mirror-native robotics typing imports
2) registry lookup parity for typed boundary payloads
3) a small typed boundary flow that rewrites frame metadata

Run:
  pixi run python -m examples.tutorial.g_operations_interfaces.05_robotics_typing_boundaries
"""

from __future__ import annotations

from pathlib import Path

import retriever
from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io
from retriever.robotics_typing import (
    Header,
    PoseStamped,
    Quaternion,
    SE3Pose,
    Vector3,
    validate_pose_stamped,
)

from examples.tutorial._p0_utils import format_table, utc_now_iso, write_json


@io
class PoseEnvelope:
    pose: PoseStamped | None = None


class PoseSource(Flow[None, PoseEnvelope]):
    def reset(self) -> None:
        self._seq = 0

    def step(self, _):  # type: ignore[override]
        self._seq += 1
        stamp_ns = self._seq * 100_000_000
        msg = PoseStamped(
            header=Header(stamp_ns=stamp_ns, frame_id="camera", source="tutorial.pose_source"),
            pose=SE3Pose(
                position=Vector3(float(self._seq), 0.0, 0.0),
                orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
            ),
        )
        return PoseEnvelope(pose=msg)


class CameraToBase(Flow[PoseEnvelope, PoseEnvelope]):
    def step(self, input: PoseEnvelope) -> PoseEnvelope:
        if input.pose is None:
            return PoseEnvelope()

        validate_pose_stamped(input.pose)
        pose = input.pose.pose
        translated = PoseStamped(
            header=Header(
                stamp_ns=input.pose.header.stamp_ns,
                frame_id="base",
                source="tutorial.camera_to_base",
            ),
            pose=SE3Pose(
                position=Vector3(pose.position.x + 1.0, pose.position.y, pose.position.z),
                orientation=pose.orientation,
            ),
        )
        return PoseEnvelope(pose=translated)


def main() -> None:
    out_path = Path("logs/tutorial_robotics_typing/tut037_robotics_typing_summary.json")

    public_cls = PoseStamped
    registry_cls = retriever.get_type("PoseStamped")
    print("=== Registry Parity ===")
    print(f"PoseStamped import == get_type('PoseStamped'): {public_cls is registry_cls}")

    pipe = Pipeline("tut037_robotics_typing")
    src = PoseSource() @ Rate(hz=5)
    projector = CameraToBase() @ Trigger("pose")
    pipe.connect(src, projector, sync=Latest())

    projector_id = pipe.get_node_id(projector)
    rows: list[list[str]] = []
    outputs: list[dict[str, object]] = []
    try:
        for step_idx in range(3):
            result = pipe.step(dt=0.2)
            out = result.outputs.get(projector_id)
            pose = getattr(out, "pose", None)
            if pose is None:
                continue
            rows.append(
                [
                    str(step_idx + 1),
                    pose.header.frame_id,
                    pose.header.source,
                    f"{pose.pose.position.x:.2f}",
                ]
            )
            outputs.append(
                {
                    "step": step_idx + 1,
                    "frame_id": pose.header.frame_id,
                    "source": pose.header.source,
                    "x": pose.pose.position.x,
                    "stamp_ns": pose.header.stamp_ns,
                }
            )
    finally:
        pipe.close_stepper()

    print("\n=== Boundary Walkthrough ===")
    print(format_table(["step", "frame_id", "source", "x"], rows))

    write_json(
        out_path,
        {
            "generated_at": utc_now_iso(),
            "registry_parity": public_cls is registry_cls,
            "outputs": outputs,
        },
    )
    print(f"\n[artifact] wrote {out_path}")


if __name__ == "__main__":
    main()
