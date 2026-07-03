---
title: "Track B: IR and Execution"
---

# Track B: IR and Execution

Focus: pipeline validation, IR structure, execution graph build, and backend behavior.

<div class="rt-learning-panel">
  <h2>Recommended Path</h2>
  <p>Start with one backend-neutral runtime pass, then inspect the IR and execution build. Treat Dora and backend parity as optional follow-ups, not the first experience.</p>
</div>

<div class="rt-command-grid">
  <div class="rt-command-card"><span>01</span><strong>Run the runtime path</strong><small>Execute a small graph through Retriever's runtime surface.</small><code>pixi run demo-rt-execution</code></div>
  <div class="rt-command-card"><span>02</span><strong>Validate the graph</strong><small>See the typed graph checks before a backend runs.</small><code>pixi run demo-ir-validation</code></div>
  <div class="rt-command-card"><span>03</span><strong>Build execution IR</strong><small>Inspect how pipeline structure becomes an executable graph.</small><code>pixi run demo-execution-build</code></div>
  <div class="rt-command-card"><span>04</span><strong>Render an HTML graph</strong><small>Generate a local visualization artifact without pasting Python heredocs.</small><code>pixi run docs-tutorial-perception-html</code></div>
</div>

??? note "Optional backend and perception modules"
    Use these when you are already comfortable with the runtime path:

    | Goal | Command |
    | --- | --- |
    | Context graph inspection | `pixi run demo-context-graph` |
    | Webcam or mock perception graph | `pixi run demo-webcam-detection` |
    | Dora backend smoke | `pixi run demo-dora-simple` |
    | Request/response edge | `pixi run demo-request-response` |
    | Detection window stats | `pixi run demo-detection-window-stats` |
    | Backend parity check | `pixi run demo-backend-parity` |

## What To Observe

- Validation happens before backend execution.
- IR inspection answers “what graph did I build?” while runtime execution answers “how does it run?”.
- Backend-specific examples come after the graph contract is clear.
