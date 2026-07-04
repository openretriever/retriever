# Concepts and Lineage

Retriever did not invent its ideas in a vacuum. This page maps each core
concept to the research and systems it descends from, so you can transfer
intuition you already have — and know what to read when you want the deeper
theory.

If you are new, read [Flow](guide_flow.md) and the
[Temporal Model](guide_temporal.md) first; this page is the "where does this
come from" companion.

## The map in one table

| Retriever concept | Closest ancestor | What transfers |
| --- | --- | --- |
| Port event history (`EventBuffer`) | FRP *event streams* [1, 2] | A port is a discrete stream of `(timestamp, value)` occurrences. |
| `Latest()` / `Hold()` sampling | FRP *behaviors* [1, 2] | Holding the last event gives a continuous time-varying value (zero-order hold). |
| `Window(duration=..., agg=...)` | Stream processing windows | Aggregate a bounded slice of history instead of one sample. |
| `Rate` / `Tick` / `Trigger` / `Hybrid` clocks | Synchronous dataflow clocks [4, 5, 6] | *When* a node runs is part of the program, not an accident of arrival order. |
| Mandatory `sync=` on every edge | Synchronous languages' explicit sampling [4] | No implicit races: how a consumer samples its inputs is written in the graph. |
| Typed `Flow[I, O]` graph → IR → backend | Dataflow process networks [3, 6] | The multiprocessing backend is close to a Kahn network with bounded queues and explicit drop policies. |
| `pipe.step(dt=...)` in-process stepper | Synchronous semantics [4, 5] | A deterministic logical clock you can single-step, breakpoint, and replay. |
| `Rate(on_lag=...)` policies | Real-time scheduling / backpressure | `drop`/`warn` = lossy real-time; `catch_up` = lossless simulation time. |
| `Flow.step()` override + `>>` composition | PyTorch `nn.Module` [9] | Author units as plain classes; compose them with operators; swap implementations. |
| `pipe.run(backend="dora")` | dora-rs dataflow runtime [8] | The same authored graph lowers onto an external real-time dataflow runtime. |

## Functional reactive programming, made operational

Classic FRP [1] models a reactive system with two types:

- **Event**: a discrete stream of timestamped occurrences.
- **Behavior**: a continuous function of time, `t -> value`.

Retriever keeps both, but makes the operational cost visible instead of
hiding it behind denotational elegance:

- Each input port *is* an event stream (a bounded `EventBuffer` of
  `(timestamp, value)` pairs).
- A **sync policy** is the sampling function that turns streams into the one
  value your `step()` sees: `Latest()` and `Hold()` construct a behavior by
  zero-order hold; `Events()` hands you the raw occurrences; `Window()`
  aggregates a slice.
- A **clock policy** decides *when* sampling happens at all.

The clock/adapter split is the FRP event/behavior split, refactored for
robots: *when do I run* (clock) is independent of *what do I see when I run*
(adapter). Push-pull FRP [2] wrestles with the same separation — Retriever
resolves it by making both choices explicit syntax at every edge.

## Synchronous dataflow, without the whole-program compiler

Synchronous languages — Lustre [4], Esterel [5], and SDF graphs [6] — showed
that giving every computation an explicit clock yields programs you can
reason about, bound, and replay. Their price is a global compilation model.

Retriever borrows the discipline, not the compiler: clocks are per-node
declarations (`@ Rate(hz=30)`), validation happens when the typed graph is
compiled to IR, and determinism is offered where it is most valuable — the
in-process stepper and recording/replay — while the distributed backends
trade strict synchrony for throughput with *declared* lag policies instead
of silent queue growth.

## What is deliberately different

- **Versus ReactiveX / Rx [7]:** Rx composes operator chains over untyped
  observables and leaves time implicit. Retriever types every edge, makes
  time first-class (every value is timestamped; every node has a clock), and
  keeps the graph inspectable as data (IR) rather than closures.
- **Versus ROS-style pub/sub [10]:** topics decouple processes but hide
  sampling semantics — "latest message wins" is an accident of callback
  timing. Retriever's mandatory `sync=` turns that accident into a reviewed
  decision, and the same graph runs in-process for debugging.
- **Versus PyTorch modules [9]:** `nn.Module` composition is synchronous and
  instantaneous. `Flow` keeps the authoring ergonomics but adds the temporal
  contract a robot needs: rates, triggers, histories, and lag behavior.

## References

1. C. Elliott and P. Hudak. *Functional Reactive Animation.* ICFP 1997.
2. C. Elliott. *Push-Pull Functional Reactive Programming.* Haskell
   Symposium 2009.
3. G. Kahn. *The Semantics of a Simple Language for Parallel Programming.*
   IFIP Congress 1974.
4. N. Halbwachs, P. Caspi, P. Raymond, and D. Pilaud. *The Synchronous Data
   Flow Programming Language LUSTRE.* Proceedings of the IEEE, 1991.
5. G. Berry and G. Gonthier. *The Esterel Synchronous Programming Language:
   Design, Semantics, Implementation.* Science of Computer Programming, 1992.
6. E. A. Lee and D. G. Messerschmitt. *Synchronous Data Flow.* Proceedings
   of the IEEE, 1987.
7. ReactiveX documentation. <https://reactivex.io/>
8. dora-rs: a dataflow runtime for robotics. <https://github.com/dora-rs/dora>
9. PyTorch `nn.Module` documentation.
   <https://pytorch.org/docs/stable/generated/torch.nn.Module.html>
10. ROS 2 design documentation. <https://design.ros2.org/>

Further reading: Z. Wan and P. Hudak, *Functional Reactive Programming from
First Principles* (PLDI 2000), for the semantics of sampling; E. Czaplicki
and S. Chong, *Asynchronous Functional Reactive Programming for GUIs* (PLDI
2013), for a practical take on avoiding global synchrony.
