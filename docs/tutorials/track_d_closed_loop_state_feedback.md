---
title: "Track D: Closed-Loop, State, and Feedback"
---

# Track D: Closed-Loop, State, and Feedback

Focus: stateful control patterns, feedback loops, authority transitions, and intervention semantics.

<div class="rt-learning-panel">
  <h2>Recommended Path</h2>
  <p>Learn local state and authority before the larger environment/planning examples.</p>
</div>

<div class="rt-command-grid">
  <div class="rt-command-card"><span>01</span><strong>State boundaries</strong><small>See how <code>reset()</code> defines local Flow state.</small><code>pixi run demo-stateful-reset</code></div>
  <div class="rt-command-card"><span>02</span><strong>Feedback loop</strong><small>Run a small closed-loop graph with explicit feedback.</small><code>pixi run demo-feedback-intro</code></div>
  <div class="rt-command-card"><span>03</span><strong>Authority handoff</strong><small>Model operator intervention and control ownership.</small><code>pixi run demo-authority-fsm</code></div>
  <div class="rt-command-card"><span>04</span><strong>Deadline response</strong><small>Switch behavior when a slow component misses timing.</small><code>pixi run demo-deadline-mode-switch</code></div>
</div>

??? note "More closed-loop modules"
    | Goal | Command |
    | --- | --- |
    | Closed-loop environment | `pixi run demo-closed-loop-env` |
    | Symbolic planning | `pixi run demo-symbolic-planning` |
    | Belief updater | `pixi run demo-belief-updater` |
    | Stateful replanning | `pixi run demo-stateful-replanning` |
    | Advanced time patterns | `pixi run demo-advanced-time-patterns` |

## What To Observe

- State lives inside the Flow that owns it; there is no hidden shared global timestep.
- Feedback changes behavior over time, so reset/replay boundaries matter.
- Authority and intervention markers fit into the same typed runtime model as perception and control.
