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
# # Step, debug, and replay
#
# `pipe.step(dt=...)` advances a Retriever graph **one tick at a time, in your own
# Python process** — no backend, no separate processes, so a normal debugger stops
# right inside `Flow.step()`. This notebook steps a small graph, reads back a
# `StepResult`, inspects the validated IR with `pipe.validate()`, and records a run
# to disk so it can be replayed deterministically. Every cell runs in-process with
# only `retriever-core` — no camera, GPU, or robot.

# %% [markdown]
# > **Running in Colab?** The next cell installs `retriever-core`. From a source
# > checkout (or once it's already installed) the install is skipped.

# %%
# Colab setup: install retriever-core only if it isn't importable yet.
try:
    import retriever  # noqa: F401
except ImportError:  # pragma: no cover
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "retriever-core"], check=True
    )

# %% [markdown]
# ## A graph to debug
#
# Three tiny Flows: a `Counter` source on a clock, a `Doubler` that fires on each
# arrival, and a `Sink` that keeps the last value it saw. This is an ordinary
# Retriever graph — the only difference is that we'll drive it with `step()`
# instead of handing it to a backend.

# %%
from retriever.flow import Flow, Latest, Pipeline, Rate, Trigger, io


@io
class Value:
    value: int


class Counter(Flow[None, Value]):
    def reset(self) -> None:
        self.count = 0

    def step(self, _) -> Value:
        self.count += 1
        return Value(value=self.count)


class Doubler(Flow[Value, Value]):
    def step(self, input: Value) -> Value:
        return Value(value=input.value * 2)  # set a breakpoint here


class Sink(Flow[Value, None]):
    def reset(self) -> None:
        self.last = None

    def step(self, input: Value) -> None:
        self.last = input.value
        return None


pipe = Pipeline("step_debug_replay")
with pipe:
    counter = Counter() @ Rate(hz=10)
    doubler = Doubler() @ Trigger("value")
    sink = Sink() @ Rate(hz=10)
    pipe.connect(counter, doubler, sync=Latest())
    pipe.connect(doubler, sink, sync=Latest())

print("built:", pipe.get_name(), "with", len(pipe.get_handles()), "nodes")

# %% [markdown]
# ## `pipe.step(dt=...)` advances one tick
#
# `step(dt=0.1)` runs one `sample -> step -> publish` pass over the whole graph and
# advances a logical clock by `dt`. It returns synchronously, so a breakpoint in
# any `Flow.step()` stops here in this process — no remote debugger to attach.

# %%
pipe.reset()  # gym-style: clear buffers and call Flow.reset() on every node

first_now = None
for i in range(4):
    result = pipe.step(dt=0.1)
    if first_now is None:
        first_now = result.now
    elapsed = round(result.now - first_now, 2)
    print(f"tick {i}: t=+{elapsed:.1f}s  executed={sorted(result.executed)}")

# %% [markdown]
# Every tick advances logical time by `dt` and, because both clocks fire each tick,
# all three nodes execute. The debugger treats `step()` like any other function.

# %% [markdown]
# ## Read back a `StepResult`
#
# Each `step()` returns a `StepResult` — a frozen record of what that tick did:
# `.executed` (node ids that ran), `.outputs` (each node's returned object), and
# `.inputs` (what each node consumed). No printing inside a Flow required; you read
# the tick's effects straight off the result.

# %%
pipe.reset()
result = pipe.step(dt=0.1)

print("type    :", type(result).__name__)
print("executed:", sorted(result.executed))
for node_id in sorted(result.outputs):
    print(f"output[{node_id}] = {result.outputs[node_id]}")
print("sink.last =", sink.flow.last)

# %% [markdown]
# `Counter` emitted `value=1`; `Doubler` turned it into `value=2`; `Sink` returned
# `None` but stashed the value in its own state — exactly what a breakpoint would
# have shown you mid-tick.

# %% [markdown]
# ## `pipe.validate()` gives you the IR
#
# Before debugging *runtime* behavior, check the graph you actually built.
# `pipe.validate()` compiles the authored graph to its Intermediate Representation:
# typed nodes, edges (with sync adapter and queue size), and the execution
# topology. This is the same IR the backends and `pipe.visualize()` consume.

# %%
ir = pipe.validate()

print(f"IR '{ir.metadata.name}' (v{ir.version}): "
      f"{len(ir.nodes)} nodes, {len(ir.edges)} edges")

print("nodes:")
for node in ir.nodes:
    print(f"  {node.id:8s} <- {node.type}")

print("edges:")
for edge in ir.edges:
    src = f"{edge.source.node}.{edge.source.port}"
    dst = f"{edge.destination.node}.{edge.destination.port}"
    print(f"  {src:16s} -> {dst:16s} [{edge.adapter}, qsize={edge.qsize}]")

print("topology:")
print("  sources:", ir.topology.sources)
print("  sinks  :", ir.topology.sinks)
print("  groups :", ir.topology.groups)

# %% [markdown]
# If the IR is wrong — a missing edge, an unexpected adapter, the wrong execution
# order — fix the wiring first. Do not start by debugging backend scheduling.

# %% [markdown]
# ## Record a run, then replay it
#
# `pipe.record(node, path, steps=...)` steps the graph and saves a node's output
# stream to disk. A `.pkl.gz` artifact is pure `gzip` + `pickle` — no extra
# dependencies — so it round-trips anywhere `retriever-core` runs.

# %%
import tempfile
from pathlib import Path

rec_path = Path(tempfile.gettempdir()) / "retriever_counter_stream.pkl.gz"

pipe.reset()
buffer = pipe.record(counter, str(rec_path), steps=4, dt=0.1)

print("recorded ", [item.value for _ts, item in buffer], "to", rec_path.name)
print("exists  :", rec_path.exists())

# %% [markdown]
# `pipe.replay(node, path=...)` swaps that node for an in-process replay source
# that re-emits the recorded values in order. The rest of the graph is untouched,
# so downstream Flows re-run against a fixed input — no live source needed, and
# every run is identical.

# %%
pipe.replay(counter, path=str(rec_path))  # Counter -> recorded stream

replayed = []
for _ in range(4):
    result = pipe.step(dt=0.1)
    replayed.append(result.outputs["Doubler"].value)

pipe.close_stepper()  # finalize flows created for stepping

print("replayed source  :", [item.value for _ts, item in buffer])
print("doubler output   :", replayed)

# %% [markdown]
# The replayed source reproduces the recorded values exactly, and `Doubler` doubles
# each one deterministically. That is the debug loop: **inspect** the IR,
# **step** in-process with a debugger, then **record once and replay many times**
# to turn a timing-sensitive run into a stable artifact you can share.
