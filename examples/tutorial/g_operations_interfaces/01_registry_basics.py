"""
Registry basics (types / flows / pipelines).

This is a lightweight demo of Retriever's "PyTorch-ish" registries:
  - Type registry:   `register_type`, `get_type`, `list_types`
  - Flow registry:   `register_flow`, `get_flow`, `list_flows`
  - Pipeline registry (IR-first): `register_pipeline`, `list_pipelines`, `build_ir`

Why this matters:
  - Examples and plugins can register components without deep imports.
  - You can swap implementations by registering a different class under the same name.

Run:
  pixi run python -m examples.tutorial.g_operations_interfaces.01_registry_basics
"""

from __future__ import annotations

from dataclasses import dataclass

import retriever
from retriever.flow import Flow, Pipeline, Rate, Trigger, Latest, io


@retriever.register_type("CounterValue", category="examples", description="Tiny demo type")
@io
@dataclass
class CounterValue:
    value: int


@retriever.register_flow("counter", category="examples", description="Counts up each tick")
class Counter(Flow[None, CounterValue]):
    def init(self) -> None:
        self.i = 0

    def run(self, _):  # type: ignore[override]
        self.i += 1
        return CounterValue(value=self.i)


@retriever.register_flow("printer", category="examples", description="Prints values")
class Printer(Flow[CounterValue, None]):
    def run(self, input: CounterValue) -> None:
        print(f"[printer] value={input.value}")
        return None


@retriever.register_pipeline("registry_demo", category="examples", description="Pipeline registered by name")
def build_registry_demo_ir():
    pipe = Pipeline("registry_demo")

    # Get flows from the registry (instances).
    counter = retriever.get_flow("counter") @ Rate(hz=10)
    printer = retriever.get_flow("printer") @ Trigger("value")

    pipe.connect(counter, printer, sync=Latest())
    return pipe.validate()


def main() -> None:
    print("=== Types ===")
    print("registered type names:", sorted(retriever.list_types().keys())[:10], "...")
    T = retriever.get_type("CounterValue")
    print("get_type('CounterValue'):", T)

    print("\n=== Flows ===")
    flows = retriever.list_flows(category="examples")
    print("examples flows:", sorted(flows.keys()))

    print("\n=== Pipelines ===")
    pipes = retriever.list_pipelines(category="examples")
    print("examples pipelines:", sorted(pipes.keys()))

    ir = retriever.build_ir("registry_demo")
    print(f"[IR] name={ir.metadata.name!r} nodes={len(ir.nodes)} edges={len(ir.edges)}")

    print("\n=== Run (in-process stepper, 3 steps) ===")
    pipe = Pipeline("registry_demo_stepper")
    counter = retriever.get_flow("counter") @ Rate(hz=10)
    printer = retriever.get_flow("printer") @ Trigger("value")
    pipe.connect(counter, printer, sync=Latest())
    try:
        for i in range(3):
            print(f"\n--- step {i} ---")
            pipe.step(dt=0.1)
    finally:
        pipe.close_stepper()


if __name__ == "__main__":
    main()
