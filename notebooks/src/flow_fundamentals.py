# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Flow fundamentals
#
# A `Flow` is the smallest unit of Retriever computation: a typed Python class
# with local state and one synchronous `step()`. This notebook builds one, runs
# it as plain Python, then drops it into a graph — with no backend, camera, or
# robot involved. Every cell runs in-process.

# %% [markdown]
# ## The smallest shape
#
# Inputs and outputs are `@io` dataclasses; their fields are the graph ports.
# `Flow[NumberInput, NumberOutput]` is the type boundary Retriever checks.

# %%
from retriever.flow import Flow, io


@io
class NumberInput:
    value: int


@io
class NumberOutput:
    result: int


class DoubleFlow(Flow[NumberInput, NumberOutput]):
    def step(self, input: NumberInput) -> NumberOutput:
        return NumberOutput(result=input.value * 2)


flow = DoubleFlow()
out = flow.step(NumberInput(value=5))
print(out)
print("ports:", flow.input_type.__name__, "->", flow.output_type.__name__)

# %% [markdown]
# A Flow is callable directly — no pipeline, no clock, no event loop. That makes
# it unit-testable and breakpoint-friendly on its own.

# %% [markdown]
# ## `_signals` says what arrived
#
# `@io` makes every field `Optional`, so a Flow can receive a *partial* input.
# `_signals` lists the fields that are actually set, so `step()` can branch on
# what it got instead of assuming a full observation.

# %%
print("empty  _signals:", NumberInput()._signals)
print("filled _signals:", NumberInput(value=7)._signals)

# %% [markdown]
# ## Local state with `reset()`
#
# Runtime-local state — counters, buffers, model handles — belongs in `reset()`,
# which the runtime calls once when a run starts. Keep `__init__` lightweight.

# %%
class Counter(Flow[None, NumberOutput]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _) -> NumberOutput:
        self.count += 1
        return NumberOutput(result=self.count)


c = Counter()
c.reset()
print("counter:", [c.step(None).result for _ in range(3)])

# %% [markdown]
# ## Put timing in the Pipeline, not the Flow
#
# A Flow never decides *when* it runs — the graph does, via a clock (`@`) and a
# sync policy on each edge. `pipe.step(dt=...)` advances the whole graph one tick
# at a time, in your process, where you can set a breakpoint inside any `step()`.

# %%
from retriever.flow import Latest, Pipeline, Rate, Trigger


class Source(Flow[None, NumberInput]):
    def reset(self):
        self.n = 0

    def step(self, _):
        self.n += 1
        return NumberInput(value=self.n)


pipe = Pipeline("flow_fundamentals")
with pipe:
    src = Source() @ Rate(hz=10)
    dbl = DoubleFlow() @ Trigger("value")
    pipe.connect(src, dbl, sync=Latest())

for i in range(3):
    result = pipe.step(dt=0.1)  # in-process; breakpoint-friendly
    print(f"tick {i}: executed={sorted(result.executed)}")
pipe.close_stepper()
