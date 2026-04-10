"""
Composable pipeline demo.

What this demonstrates:
  - registering a pipeline with explicit external surface selectors
  - naming internal flows for stable selectors
  - extending a declared pipeline via `select_flow(...)` + `replace(...)`
  - treating a registered pipeline as a reusable flow via `build_pipeline_flow(...)`

Run:
  pixi run demo-composable-pipelines
"""

from __future__ import annotations

import retriever
from retriever.flow import Flow, Pipeline, Rate, Latest, io


@io
class CounterOut:
    value: int
    aux: int


@io
class ProcIn:
    value: int
    bias: int


@io
class ProcOut:
    value: int


@io
class BiasOut:
    bias: int


@io
class DecisionView:
    value: int
    aux: int


class Counter(Flow[None, CounterOut]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _):  # type: ignore[override]
        self.count += 1
        return CounterOut(value=self.count, aux=99)


class BiasPolicy(Flow[ProcIn, ProcOut]):
    def step(self, input: ProcIn) -> ProcOut:
        return ProcOut(value=input.value + input.bias)


class OverridePolicy(Flow[ProcIn, ProcOut]):
    def __init__(self, *, delta: int = 100):
        super().__init__()
        self.delta = int(delta)

    def step(self, input: ProcIn) -> ProcOut:
        return ProcOut(value=input.value + input.bias + self.delta)


class BiasSource(Flow[None, BiasOut]):
    def __init__(self, *, bias: int):
        super().__init__()
        self.bias = int(bias)

    def step(self, _):  # type: ignore[override]
        return BiasOut(bias=self.bias)


class DecisionPrinter(Flow[DecisionView, None]):
    def step(self, input: DecisionView) -> None:
        print(f"[outer] value={input.value} aux={input.aux}")
        return None


@retriever.register_pipeline(
    "tutorial.composable_counter",
    category="examples",
    description="Small registered pipeline that can be extended or wrapped as a flow",
    surface_policy="explicit",
    input_ports=["policy.bias"],
    output_ports=["counter.aux", "policy.value"],
    overwrite=True,
)
def build_composable_counter() -> Pipeline:
    pipe = Pipeline("tutorial.composable_counter")
    with pipe:
        counter = (Counter() @ Rate(hz=10)).named("counter")
        policy = (BiasPolicy() @ Rate(hz=10)).named("policy")
        counter.then(policy, map={"value": "value"}, sync=Latest())
    return pipe


def demo_extend_declared_pipeline() -> None:
    print("=== Extend Declared Pipeline ===")
    pipe = build_composable_counter()
    print("internal flows:", sorted(pipe.get_flow_dict().keys()))

    pipe.replace(pipe.select_flow("policy"), OverridePolicy(delta=100) @ Rate(hz=10))
    pipe.inject_input("policy", "bias", 3, timestamp=0.0)

    try:
        result = pipe.step(now=0.0)
        print("policy output after replacement:", result.outputs["policy"])
    finally:
        pipe.close_stepper()


def build_outer_composable_counter(*, bias: int = 4) -> Pipeline:
    outer = Pipeline("outer.composable_counter")

    with outer:
        bias_source = BiasSource(bias=bias) @ Rate(hz=10)
        sub = (retriever.build_pipeline_flow("tutorial.composable_counter") @ Rate(hz=10)).named("stage")
        sink = DecisionPrinter() @ Rate(hz=10)

        bias_source.then(sub, sync=Latest())
        sub.then(sink, sync=Latest())

    return outer


def demo_compose_pipeline_as_flow() -> None:
    print("\n=== Compose Pipeline As Flow ===")
    outer = build_outer_composable_counter()

    try:
        result = outer.step(now=0.0)
        print("wrapped stage output:", result.outputs["stage"])
    finally:
        outer.close_stepper()


def main() -> None:
    demo_extend_declared_pipeline()
    demo_compose_pipeline_as_flow()


if __name__ == "__main__":
    main()
