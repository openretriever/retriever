---
title: "Example Gallery"
---

# Example Gallery

Use the examples in this order. The core repo teaches the runtime itself; GoldenRetriever carries larger perception, memory, language, robotics, and integration examples.

<div class="rt-path-grid rt-path-grid-three">
  <a class="rt-path-step" href="/quickstart/">
    <span>01</span>
    <strong>First visual demo</strong>
    <p>Webcam frames flow through a color detector into Rerun/stdout visualization.</p>
    <code>pixi run demo-webcam-detection</code>
  </a>
  <a class="rt-path-step" href="/tutorials/track_a_flow_fundamentals/">
    <span>02</span>
    <strong>Core mechanics</strong>
    <p>Typed payloads, Flow classes, clocks, sync policies, and pipeline wiring.</p>
    <code>pixi run demo-basic-flow</code>
  </a>
  <a class="rt-path-step" href="https://retriever-space.pages.dev/">
    <span>03</span>
    <strong>Golden examples</strong>
    <p>Perception, memory, language, notebooks, and robotics integration lanes.</p>
    <code>pixi run -e golden-local ...</code>
  </a>
</div>

## Core Runtime Examples

These examples are intentionally small. They are meant to make the runtime model obvious before you bring in heavier robot stacks.

| Goal | Command | What it teaches |
| --- | --- | --- |
| See a graph run on real input | `pixi run demo-webcam-detection` | Webcam color detection with Rerun when available and stdout fallback. |
| Understand the minimum API | `pixi run demo-basic-flow` | `@io`, `Flow`, `Rate`, `Trigger`, `Pipeline.connect`. |
| Inspect backend execution | `pixi run demo-rt-execution` | Runtime validation and backend execution. |
| Debug in one Python process | `pixi run demo-stepper` | `Pipeline.step(...)` before multiprocessing/dora. |
| Record and replay perception | `pixi run demo-webcam-record` | Deterministic replay artifacts for debugging. |
| Join multi-rate streams | `pixi run demo-data-multistream-join` | Synchronization and event joins. |

## Rerun Visualization

Rerun is the first visual path for Retriever examples. Use `pixi run demo-webcam-detection` for automatic Rerun/stdout fallback, `pixi run demo-webcam-detection-mp-rerun` when you specifically want a worker-backend live viewer, and `pixi run demo-webcam-record` when you want a portable replay artifact.

## Core vs GoldenRetriever

- Keep examples in this repo when they teach the **runtime contract**: typed flows, clocks, sync, IR, execution, stepping, replay, or release checks.
- Put examples in GoldenRetriever when they teach a **robotics application lane**: perception models, memory, language grounding, notebooks, simulation, real robot adapters, or larger system demos.
- Link across repos instead of copying code when the same concept would otherwise appear twice.

!!! note "Current boundary"
    No example move is needed for the current docs polish pass. The core repo already has the right tutorial primitives; GoldenRetriever remains the right home for larger robot-facing examples.

## Next Paths

- [Tutorial Tracks](tutorials/index.md) for the ordered core curriculum.
- [Runtime Handbook](handbook.md) for the canonical reference path.
- [GoldenRetriever site](https://retriever-space.pages.dev/) for application examples.
