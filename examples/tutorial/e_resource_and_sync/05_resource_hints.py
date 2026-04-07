"""
Resource hints with FlowConfig + ResourceSpec.

Run:
  pixi run python -m examples.tutorial.e_resource_and_sync.05_resource_hints --print-ir
  pixi run python -m examples.tutorial.e_resource_and_sync.05_resource_hints --steps 4 --dt 0.1
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from retriever.flow import Flow, FlowConfig, Pipeline, Rate, Latest, TemporalFlow, io
from retriever.flow.config import ResourceSpec


@io
class SensorOut:
    value: float | None = None


@io
class VisionOut:
    features: int | None = None


@io
class PlanOut:
    plan: str | None = None


@io
class SafetyOut:
    status: str | None = None


class SensorFlow(Flow[None, SensorOut]):
    def reset(self) -> None:
        self._step_idx = 0

    def step(self, _):  # type: ignore[override]
        self._step_idx += 1
        return SensorOut(value=float(self._step_idx))


class VisionFlow(Flow[SensorOut, VisionOut]):
    def step(self, input: SensorOut) -> VisionOut:
        if input.value is None:
            return VisionOut()
        features = int(input.value) * 4
        return VisionOut(features=features)


class PlannerFlow(Flow[VisionOut, PlanOut]):
    def step(self, input: VisionOut) -> PlanOut:
        if input.features is None:
            return PlanOut()
        return PlanOut(plan=f"plan_for_{input.features}_features")


class SafetyFlow(Flow[SensorOut, SafetyOut]):
    def step(self, input: SensorOut) -> SafetyOut:
        if input.value is None:
            return SafetyOut()
        status = "ok" if input.value < 3 else "warn"
        return SafetyOut(status=status)


class Printer(Flow[PlanOut, None]):
    def step(self, input: PlanOut) -> None:
        if input.plan is None:
            return None
        print(f"[plan] {input.plan}")
        return None


class SafetyPrinter(Flow[SafetyOut, None]):
    def step(self, input: SafetyOut) -> None:
        if input.status is None:
            return None
        print(f"[safety] {input.status}")
        return None


def build_pipeline(*, hz: float) -> tuple[Pipeline, dict[str, TemporalFlow]]:
    pipe = Pipeline("resource_hints")
    clock = Rate(hz=hz)

    with pipe:
        sensor = SensorFlow() @ FlowConfig(
            clock=clock,
            resources=ResourceSpec(cpu=0.5, memory=0.5, custom={"camera": 1}, node_type="edge"),
        )
        vision = VisionFlow() @ FlowConfig(
            clock=clock,
            resources=ResourceSpec(cpu=2.0, gpu=0.5, memory=4.0, gpu_memory=2.0, node_type="gpu"),
        )
        planner = PlannerFlow() @ FlowConfig(
            clock=clock,
            resources=ResourceSpec(cpu=3.0, memory=6.0, priority=2),
        )
        safety = SafetyFlow() @ FlowConfig(
            clock=clock,
            resources=ResourceSpec(cpu=1.0, max_runtime=0.01, priority=10, preemptible=False),
        )
        printer = Printer() @ FlowConfig(clock=clock)
        safety_printer = SafetyPrinter() @ FlowConfig(clock=clock)

        pipe.connect(sensor, vision, sync=Latest())
        pipe.connect(vision, planner, sync=Latest())
        pipe.connect(planner, printer, sync=Latest())

        pipe.connect(sensor, safety, sync=Latest())
        pipe.connect(safety, safety_printer, sync=Latest())

    return pipe, {
        "sensor": sensor,
        "vision": vision,
        "planner": planner,
        "safety": safety,
    }


def print_resources(handles: dict[str, TemporalFlow]) -> None:
    print("Resource hints:")
    for name, handle in handles.items():
        resources = handle.config.resources
        if resources is None:
            print(f"- {name}: <default>")
            continue
        print(
            f"- {name}: cpu={resources.cpu} gpu={resources.gpu} mem={resources.memory} "
            f"custom={resources.custom} node_type={resources.node_type} "
            f"priority={resources.priority} max_runtime={resources.max_runtime}"
        )


def print_ir(pipe: Pipeline) -> None:
    ir = pipe.validate()
    print("IR resource config:")
    for node in ir.nodes:
        resources = node.config.get("resources", {})
        print(f"- {node.id}: {resources}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Resource hint patterns (FlowConfig + ResourceSpec).")
    p.add_argument("--steps", type=int, default=0)
    p.add_argument("--dt", type=float, default=0.1)
    p.add_argument("--print-ir", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    hz = 1.0 / max(args.dt, 1e-6)
    pipe, handles = build_pipeline(hz=hz)

    print_resources(handles)
    if args.print_ir:
        print_ir(pipe)

    if args.steps > 0:
        for _ in range(args.steps):
            pipe.step(dt=args.dt)
        pipe.close_stepper()


if __name__ == "__main__":
    main()
