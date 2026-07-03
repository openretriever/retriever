---
title: "Track C: Debug and Replay"
---

# Track C: Debug and Replay

Focus: stepper-first debugging, deterministic replay, and trace diagnostics.

<div class="rt-learning-panel">
  <h2>Recommended Path</h2>
  <p>Debug in-process first, then record/replay the same behavior. This keeps failures local before adding backend scheduling.</p>
</div>

<div class="rt-command-grid">
  <div class="rt-command-card"><span>01</span><strong>Step the graph</strong><small>Use ordinary Python debugging before backend execution.</small><code>pixi run demo-stepper</code></div>
  <div class="rt-command-card"><span>02</span><strong>Step perception</strong><small>Inspect a perception pipeline one tick at a time.</small><code>pixi run demo-perception-stepper</code></div>
  <div class="rt-command-card"><span>03</span><strong>Record and replay</strong><small>Capture a short session and replay it deterministically.</small><code>pixi run demo-record-replay</code></div>
  <div class="rt-command-card"><span>04</span><strong>Incident drill</strong><small>Compare live and replay signatures to isolate a failure.</small><code>pixi run demo-incident-replay</code></div>
</div>

??? note "More debugging tools"
    | Goal | Command |
    | --- | --- |
    | Real-camera stepper | `pixi run demo-webcam-stepper` |
    | Buffer engine basics | `pixi run demo-buffer-engine` |
    | Trace contract basics | `pixi run demo-trace-contract` |
    | MCAP inspection | `pixi run demo-mcap-session-inspection` |
    | HTML graph artifact | `pixi run docs-tutorial-perception-html` |

    The MCAP inspection command expects a recording. Run `pixi run demo-webcam-record` first if `logs/perception.mcap` does not exist.

## What To Observe

- In-process stepping gives normal breakpoints and deterministic inspection.
- Replay turns a transient robot failure into a repeatable local artifact.
- Trace contracts and MCAP inspection should support debugging, not replace the first stepper pass.
