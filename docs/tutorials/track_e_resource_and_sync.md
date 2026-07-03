---
title: "Track E: Resource and Synchronization"
---

# Track E: Resource and Synchronization

Focus: fan-in synchronization, multi-rate sampling, resource compatibility, and fusion constraints.

<div class="rt-learning-panel">
  <h2>Recommended Path</h2>
  <p>Start with data handoff and fan-in behavior. Resource hints are useful later, after the synchronization story is clear.</p>
</div>

<div class="rt-command-grid">
  <div class="rt-command-card"><span>01</span><strong>Join event streams</strong><small>Bridge runtime buffer records with data/event stream structures.</small><code>pixi run demo-data-multistream-join</code></div>
  <div class="rt-command-card"><span>02</span><strong>Sync policies</strong><small>Compare explicit sampling behavior across edges.</small><code>pixi run demo-synchronization</code></div>
  <div class="rt-command-card"><span>03</span><strong>Fan-in and fan-out</strong><small>Use functional composition for branching graph shapes.</small><code>pixi run demo-functional-fanin-fanout</code></div>
  <div class="rt-command-card"><span>04</span><strong>Multi-rate robot system</strong><small>See a larger example with different sensor/control rates.</small><code>pixi run demo-multirate-robot-system</code></div>
</div>

??? note "More resource modules"
    | Goal | Command |
    | --- | --- |
    | Windowed multi-rate sampling | `pixi run demo-multirate` |
    | Strict resource fusion | `pixi run demo-strict-resource-fusion` |
    | Resource hints in IR | `pixi run demo-resource-hints` |

## What To Observe

- Sync policies make “which upstream value did I consume?” explicit.
- Prefer shared payloads and direct composition where possible; named wrappers are useful when the synchronization surface is itself the lesson.
- Resource hints belong after the timing and data-handoff model is clear.
