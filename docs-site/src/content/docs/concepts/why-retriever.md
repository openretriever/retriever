---
title: Why Retriever
description: How Retriever positions against raw Python, ROS 2, and Dora - the mental model and an at-a-glance comparison.
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
- **Step-debug in-process.** `Pipeline.step(...)` runs the graph in your Python
  process with real breakpoints before you scale to a backend.
- **Record and replay.** Recording-enabled runs can persist MCAP or Rerun
  artifacts and replay the consumed streams later.
- **One graph, many backends.** Author once; run in-process, with
  multiprocessing, or on a Dora backend when the integration path is ready.

## How Retriever compares

What you get by default: Yes = built in, Partial = possible with effort, No = not the default path.

| Capability | Raw Python | ROS 2 | Dora | Retriever |
| --- | :---: | :---: | :---: | :---: |
| Typed port / message contracts | No | Partial | Partial | Yes: `@io` |
| Explicit per-node rates | No | Partial | Yes | Yes |
| Sampling / sync made explicit | No | No | Partial | Yes: `sync=` |
| In-process step-debug | Partial | No | No | Yes: `Pipeline.step(...)` |
| Record + replay artifacts | No | Partial: bags | Partial | Yes: MCAP/Rerun paths |
| Same graph on multiple backends | N/A | No | Partial | Yes: in-process / mp / Dora |
| Python-native authoring | Yes | Partial: `rclpy` | Partial | Yes |

`Partial` means achievable but not the default path, such as ROS 2 sync via
`message_filters` or replay through bags. The point is what the framework gives
you without extra scaffolding.

## When to use it - and when not

**Use Retriever** when perception, reasoning, and control need to run together
at mismatched rates, and you want the handoff and timing to be explicit,
debuggable, and replayable.

**You don't need it** for a single-rate script, a pure offline batch job, or a
one-shot model call; plain Python is fine there. Retriever earns its keep once
the system is *closed-loop and multi-rate*.

For where these ideas come from (FRP, synchronous dataflow, Kahn networks), see
[Concepts and Lineage](/concepts/lineage/).
