---
title: Why Retriever
description: How Retriever positions against raw Python, Ray, ROS 2, and Dora - the mental model and an at-a-glance comparison.
---

If you know PyTorch, you already have the mental model: you compose `Flow`s the
way you compose `nn.Module`s - except a `Flow` carries **explicit time**. It
runs at its own rate, samples its inputs by a policy you choose, and can be
stepped, recorded, and replayed. A robot runs in the real world, not in one
forward pass, so time is part of the program, not an accident of scheduling.

## What Retriever gives you

- **Typed handoff.** Ports are declared with `@io`; the graph's interfaces are
  inspectable before you run it.
- **Time is explicit.** Every node has a clock (`Rate` / `Trigger` / `Hybrid`)
  and every edge a sampling policy (`sync=`). There is no implicit "latest message wins" hidden at graph boundaries.
- **Functional determinism.** The same timestamped input trace produces the same
  output trace regardless of how the runtime schedules the graph. That property
  is what makes replay and verification well-defined — not best-effort.
- **Step-debug in-process.** `Pipeline.step(...)` runs the graph in your Python
  process with real breakpoints before you scale to a backend.
- **Record and replay.** Recording-enabled runs can persist MCAP or Rerun
  artifacts and replay the consumed streams later.
- **One graph, many backends.** Author once; run in-process, with
  multiprocessing, or on a Dora backend when the integration path is ready.

## How Retriever compares

Retriever borrows from familiar *categories* rather than competing with any
single tool. So the comparison is by category — Yes = built in, Partial =
possible with extra scaffolding, No = not what the category is designed for.

| | Plain Python | DL frameworks (PyTorch / TF) | Distributed Python (Ray) | Robotics dataflow (ROS 2 / Dora) | Retriever |
| --- | :---: | :---: | :---: | :---: | :---: |
| **What it's for** | scripts & glue | building / training models | distributed Python tasks and actors | distributed message passing | closed-loop, multi-rate agents |
| Typed port / message contracts | No | Partial: tensors | Partial: Python APIs | Partial | **Yes:** `@io` |
| Explicit per-node rates | No | No | No | Yes | **Yes** |
| Sampling / sync made explicit | No | No | No | Partial | **Yes:** `sync=` |
| In-process step-debug | Partial | Yes: eager | Partial: local mode / logs | No | **Yes:** `Pipeline.step(...)` |
| Record + replay of the run | No | No: weights only | Partial: logs / artifacts | Partial: bags | **Yes:** MCAP/Rerun |
| Same graph, many backends | N/A | Partial: export | Partial: local / cluster | Partial | **Yes:** in-process / mp / Dora |
| Python-native authoring | Yes | Yes | Yes | Partial: bindings | **Yes** |

Each category owns a different problem: **DL frameworks** own the *model* — a
compute graph with autodiff, run one forward pass at a time; **Ray** owns
*distributed Python execution* with tasks, actors, and cluster scheduling;
**robotics dataflow** owns *distributed messaging* between nodes; **Retriever**
owns *closed-loop time* — how a graph of stateful components runs, samples its
inputs, and stays reproducible across mismatched rates. Retriever keeps the
PyTorch-style authoring feel (compose typed components), borrows the actor/DAG
intuition from Ray, and adds the timing and replay guarantees a real robot loop
needs.

`Partial` means achievable but not the default path — ROS 2 sync via
`message_filters`, replay through bags, Ray logs/artifacts, or exporting a model
with TorchScript.

## When to use it - and when not

**Use Retriever** when perception, reasoning, and control need to run together
at mismatched rates, and you want the handoff and timing to be explicit,
debuggable, and replayable.

**You don't need it** for a single-rate script, a pure offline batch job, or a
one-shot model call; plain Python is fine there. Retriever earns its keep once
the system is *closed-loop and multi-rate*.

For where these ideas come from (FRP, synchronous dataflow, Kahn networks), see
[Concepts and Lineage](/concepts/lineage/).
