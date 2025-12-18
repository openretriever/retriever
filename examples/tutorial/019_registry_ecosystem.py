"""
Registry ecosystem demo (types + flows + pipeline factories).

This is a modernized, runtime-aligned rewrite of the legacy
`examples/legacy/01_core_concepts/04_complete_registry_ecosystem.py`.

What this demonstrates:
  - Type registry:      `register_type`, `get_type`, `list_types`, `find_types`
  - Flow registry:      `register_flow`, `get_flow`, `list_flows`, `find_flows`
  - Pipeline registry:  `register_pipeline` + `get_pipeline_factory` + `build_ir`
  - Substitution: pass a different registered component name (e.g. `--camera noisy_camera`)

Run:
  pixi run python -m examples.tutorial.019_registry_ecosystem --steps 3
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

import retriever
from retriever.core.flow import Flow, Pipeline, Rate, Trigger, Latest, flow_io


# =============================================================================
# 1) Type registry (custom I/O dataclasses)
# =============================================================================

@retriever.register_type("Frame", category="vision", description="Mock camera frame summary", tags=["mock"])
@flow_io
@dataclass
class Frame:
    frame_id: int
    brightness: float


@retriever.register_type("Pose2D", category="geometry", description="Tiny 2D pose type", tags=["robotics", "spatial"])
@flow_io
@dataclass
class Pose2D:
    x: float
    y: float


@retriever.register_type("RobotStatus", category="robotics", description="Toy robot status", tags=["status", "monitoring"])
@flow_io
@dataclass
class RobotStatus:
    battery: float
    mode: str


# =============================================================================
# 2) Flow registry (components you can swap by name)
# =============================================================================

@retriever.register_flow("mock_camera", category="vision", description="Deterministic mock camera", tags=["mock", "input"])
class MockCamera(Flow[None, Frame]):
    def init(self) -> None:
        self.frame_id = 0

    def run(self, _):  # type: ignore[override]
        self.frame_id += 1
        b = 0.5 + 0.5 * math.sin(self.frame_id * 0.2)
        return Frame(frame_id=self.frame_id, brightness=b)


@retriever.register_flow(
    "noisy_camera",
    category="vision",
    description="Mock camera with deterministic 'noise' injected into brightness",
    tags=["mock", "input"],
)
class NoisyCamera(Flow[None, Frame]):
    def __init__(self, *, noise_amp: float = 0.15):
        super().__init__()
        self.noise_amp = float(noise_amp)

    def init(self) -> None:
        self.frame_id = 0

    def run(self, _):  # type: ignore[override]
        self.frame_id += 1
        base = 0.5 + 0.5 * math.sin(self.frame_id * 0.2)
        noise = self.noise_amp * math.sin(self.frame_id * 3.7)
        b = max(0.0, min(1.0, base + noise))
        return Frame(frame_id=self.frame_id, brightness=b)


@retriever.register_flow("pose_estimator", category="perception", description="Estimate Pose2D from Frame", tags=["pose"])
class PoseEstimator(Flow[Frame, Pose2D]):
    def run(self, input: Frame) -> Pose2D:
        if input.brightness is None:
            return Pose2D()
        x = (float(input.brightness) - 0.5) * 2.0
        y = math.cos(float(input.frame_id or 0) * 0.1)
        return Pose2D(x=x, y=y)


@retriever.register_flow("robot_monitor", category="system", description="Battery drain + mode from pose", tags=["status"])
class RobotMonitor(Flow[Pose2D, RobotStatus]):
    def init(self) -> None:
        self.battery = 100.0

    def run(self, input: Pose2D) -> RobotStatus:
        if input.x is None or input.y is None:
            return RobotStatus()

        movement = abs(float(input.x)) + abs(float(input.y))
        self.battery = max(0.0, self.battery - 0.5 * movement)

        if movement > 1.0:
            mode = "moving"
        elif movement > 0.05:
            mode = "working"
        else:
            mode = "idle"

        return RobotStatus(battery=self.battery, mode=mode)


@retriever.register_flow("status_printer", category="examples", description="Prints RobotStatus", tags=["output"])
class StatusPrinter(Flow[RobotStatus, None]):
    def run(self, input: RobotStatus) -> None:
        if input.battery is None or input.mode is None:
            return None
        print(f"[status] battery={input.battery:5.1f}% mode={input.mode}")
        return None


# =============================================================================
# 3) Pipeline registry (register pipeline factories)
# =============================================================================

@retriever.register_pipeline(
    "robot_localization",
    category="examples",
    description="Mock camera → pose estimator → robot monitor",
    tags=["registry", "robotics", "vision"],
)
def build_robot_localization_pipeline(*, camera: str = "mock_camera") -> Pipeline:
    """
    Pipeline factory.

    The pipeline registry expects factories to return either:
      - `IRStruct`, or
      - `FlowContext` (including `Pipeline`)

    Returning `Pipeline` lets you:
      - `retriever.build_ir(...)` (validates to IR), and also
      - use the same factory for `Pipeline.step()` debugging (in-process).
    """
    pipe = Pipeline("robot_localization")

    with pipe:
        cam = retriever.get_flow(camera) @ Rate(hz=10)
        # Use Rate clocks here so `Pipeline.step()` samples all available inputs each
        # step (Trigger sampling is field-by-field and is better suited to single-port
        # inputs like `image`).
        est = retriever.get_flow("pose_estimator") @ Rate(hz=10)
        mon = retriever.get_flow("robot_monitor") @ Rate(hz=10)
        out = retriever.get_flow("status_printer") @ Rate(hz=10)

        cam.then(est, sync=Latest())
        est.then(mon, sync=Latest())
        mon.then(out, sync=Latest())

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Registry ecosystem demo (types/flows/pipelines).")
    p.add_argument("--camera", default="mock_camera", choices=["mock_camera", "noisy_camera"])
    p.add_argument("--steps", type=int, default=3, help="Stepper iterations (in-process).")
    p.add_argument("--dt", type=float, default=0.1, help="Logical dt per step (seconds).")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print("=== Types ===")
    print("geometry:", sorted(retriever.list_types(category="geometry").keys()))
    print("robotics:", sorted(retriever.find_types(category="robotics", tags=["status"]).keys()))

    print("\n=== Flows ===")
    print("vision flows:", sorted(retriever.list_flows(category="vision").keys()))
    print("pose flows:", sorted(retriever.find_flows(tags=["pose"]).keys()))

    print("\n=== Pipelines ===")
    print("examples pipelines:", sorted(retriever.list_pipelines(category="examples").keys()))
    print("tagged vision:", sorted(retriever.find_pipelines(tags=["vision"]).keys()))

    # Build IR via pipeline registry (factory → FlowContext.validate → IRStruct)
    ir = retriever.build_ir("robot_localization", camera=args.camera)
    print(f"\n[IR] name={ir.metadata.name!r} nodes={len(ir.nodes)} edges={len(ir.edges)} camera={args.camera!r}")

    # Debug-friendly execution: run in-process so breakpoints inside Flow.run() work.
    factory = retriever.get_pipeline_factory("robot_localization")
    pipe = factory(camera=args.camera)  # type: ignore[call-arg]

    print(f"\n=== Run (Pipeline.step, {args.steps} steps) ===")
    try:
        for i in range(args.steps):
            print(f"\n--- step {i} ---")
            pipe.step(dt=args.dt)
    finally:
        pipe.close_stepper()


if __name__ == "__main__":
    main()
