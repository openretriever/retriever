---
title: Why Retriever
description: How Retriever positions against raw Python, ROS 2, and dora — the mental model and an at-a-glance comparison.
---

If you know PyTorch, you already have the mental model: you compose `Flow`s the
way you compose `nn.Module`s — except a `Flow` carries **explicit time**. It
runs at its own rate, samples its inputs by a policy you choose, and can be
stepped, recorded, and replayed. A robot runs in the real world, not in one
forward pass, so time is part of the program, not an accident of scheduling.

## What Retriever gives you

- **Typed handoff.** Ports are declared with `@io`; the graph's interfaces are
  inspectable before you run it.
- **Time is explicit.** Every node has a clock (`Rate` / `Trigger` / `Hybrid`)
  and every edge a sampling policy (`sync=`) — no implicit "latest message wins."
- **Step-debug in-process.** `pipe.step()` runs the graph in your Python
  process with real breakpoints, before you scale to a backend.
- **Record and replay.** Any run captures to MCAP/Rerun and replays
  deterministically — the same graph, inspectable after the fact.
- **One graph, many backends.** Author once; run on multiprocessing, dora, or
  in-process.

## How Retriever compares

What you get *out of the box* — ✓ built-in · ~ possible with effort · ✕ not really:

| Capability (default) | raw Python | ROS 2 | dora | Retriever |
| --- | :---: | :---: | :---: | :---: |
| Typed port / message contracts | ✕ | ~ | ~ | ✓ `@io` |
| Explicit per-node rates | ✕ | ~ | ✓ | ✓ |
| Sampling / sync made explicit | ✕ | ✕ | ~ | ✓ mandatory `sync=` |
| In-process step-debug | ~ | ✕ | ✕ | ✓ `pipe.step()` |
| Record + deterministic replay | ✕ | ~ bags | ~ | ✓ MCAP/Rerun |
| Same graph on multiple backends | — | ✕ | ~ | ✓ mp / dora / in-proc |
| Python-native authoring | ✓ | ~ `rclpy` | ~ | ✓ |

`~` means achievable but not the default path (e.g. ROS 2 sync via
`message_filters`, replay via bags). The point is what the framework gives you
without extra scaffolding.

## When to use it — and when not

**Use Retriever** when perception, reasoning, and control need to run together
at mismatched rates, and you want the handoff and timing to be explicit,
debuggable, and replayable.

**You don't need it** for a single-rate script, a pure offline batch job, or a
one-shot model call — plain Python is fine there. Retriever earns its keep once
the system is *closed-loop and multi-rate*.

For where these ideas come from (FRP, synchronous dataflow, Kahn networks), see
[Concepts and Lineage](/concepts/lineage/).
