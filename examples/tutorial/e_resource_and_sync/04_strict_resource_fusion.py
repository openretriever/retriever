"""
Resource constraints + strict fusion demo.

This is a runtime-aligned rewrite of the legacy "resource annotation" examples.

It demonstrates:
  - How to attach resource hints via `FlowConfig(...) @ flow`
  - How execution grouping ("fusion") can be made strict about resources
    using `pipeline.build_execution(policy="strict")`

Run:
  pixi run python -m examples.tutorial.e_resource_and_sync.04_strict_resource_fusion --case compatible
"""

from __future__ import annotations

import argparse

from retriever.flow import Flow, FlowConfig, Pipeline, Rate, io


@io
class Val:
    x: float


class Source(Flow[None, Val]):
    def reset(self) -> None:
        self.i = 0

    def step(self, _):  # type: ignore[override]
        self.i += 1
        return Val(x=float(self.i))


class Scale(Flow[Val, Val]):
    def step(self, input: Val) -> Val:
        if input.x is None:
            return Val()
        return Val(x=float(input.x) * 2.0)


class Sink(Flow[Val, None]):
    def step(self, input: Val) -> None:
        return None


def build_pipeline(case: str) -> Pipeline:
    pipe = Pipeline(f"strict_resource_fusion:{case}")
    clock = Rate(hz=10)

    # Scenario setup:
    # - "compatible": same priority + overlapping cpu_affinity => can co-locate
    # - "priority_mismatch": different priorities => cannot co-locate (strict policy)
    # - "affinity_mismatch": disjoint cpu_affinity => cannot co-locate (strict policy)
    if case == "compatible":
        cfg_a = FlowConfig(clock=clock, priority=1, cpu_affinity=[0, 1])
        cfg_b = FlowConfig(clock=clock, priority=1, cpu_affinity=[1, 2])
        cfg_c = FlowConfig(clock=clock, priority=1, cpu_affinity=[1])
    elif case == "priority_mismatch":
        cfg_a = FlowConfig(clock=clock, priority=1, cpu_affinity=[0, 1])
        cfg_b = FlowConfig(clock=clock, priority=2, cpu_affinity=[0, 1])
        cfg_c = FlowConfig(clock=clock, priority=1, cpu_affinity=[0, 1])
    elif case == "affinity_mismatch":
        cfg_a = FlowConfig(clock=clock, priority=1, cpu_affinity=[0])
        cfg_b = FlowConfig(clock=clock, priority=1, cpu_affinity=[1])
        cfg_c = FlowConfig(clock=clock, priority=1, cpu_affinity=[0])
    else:
        raise ValueError(f"Unknown case: {case}")

    with pipe:
        a = Source() @ cfg_a
        b = Scale() @ cfg_b
        c = Sink() @ cfg_c
        a >> b >> c

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Strict fusion with resource constraints demo.")
    p.add_argument(
        "--case",
        default="compatible",
        choices=["compatible", "priority_mismatch", "affinity_mismatch"],
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pipe = build_pipeline(args.case)

    ir = pipe.validate()
    exec_graph = pipe.build_execution(policy="strict")

    print(f"Logical nodes: {[n.id for n in ir.nodes]}")
    print("Execution partitions (strict policy):")
    for part in exec_graph.partitions:
        print(f"  - {part.id}: {part.node_ids}")


if __name__ == "__main__":
    main()

