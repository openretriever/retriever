---
title: "Track F: Policy Backends"
---

# Track F: Policy Backends

Focus: keep the same closed-loop policy contract and switch only the backend.

This is a specialized track. It makes more sense after the basics in Tracks D and G are already clear.

<div class="rt-command-grid rt-command-grid-single">
  <div class="rt-command-card"><span>01</span><strong>Compare backend rows</strong><small>Run the same closed-loop policy surface against mock/OpenPI/LeRobot-style backend adapters and compare latency/action-horizon behavior.</small><code>pixi run demo-policy-backends</code></div>
</div>

## What To Observe

- The same example and policy interface run across backend adapters.
- Latency and action-horizon behavior differ by backend, but the closed-loop contract does not.
- CSV/JSON artifacts are optional evidence for later release-readiness checks.
