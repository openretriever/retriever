---
title: "Track A: Flow Fundamentals"
---

# Track A: Flow Fundamentals

Focus: typed Flow authoring, clocks, sync policies, and pipeline ergonomics.

<div class="rt-learning-panel">
  <h2>Recommended Path</h2>
  <p>Run the short path first. It teaches the API shape before introducing every variant.</p>
</div>

<div class="rt-command-grid">
  <div class="rt-command-card"><span>01</span><strong>Smallest Flow</strong><small>Define typed input/output objects and a stateful <code>step(...)</code>.</small><code>pixi run demo-basic-flow</code></div>
  <div class="rt-command-card"><span>02</span><strong>Edge Sync</strong><small>Connect two Flows and make the sampling rule explicit.</small><code>pixi run demo-adapter-connection</code></div>
  <div class="rt-command-card"><span>03</span><strong>Pipeline Ergonomics</strong><small>Compare explicit wiring with the convenience forms.</small><code>pixi run demo-pipeline-ergonomics</code></div>
</div>

??? note "More modules in this track"
    Use these after the core shape is clear:

    | Lesson | Command |
    | --- | --- |
    | Clock types | `pixi run demo-clock-types` |
    | Full pipeline | `pixi run demo-full-pipeline` |

## What To Observe

- `@io` defines the typed envelopes that move through the graph.
- A Flow is still a normal Python class; Retriever adds explicit clocks and sync policies around it.
- The ergonomic helpers and explicit `Pipeline(...)` authoring map to the same graph model.
