---
title: "Track F: Policy Backends"
---

# Track F: Policy Backends

Focus: keep the same closed-loop policy contract and switch only the backend.

This is a specialized track. It makes more sense after the basics in Tracks D and G are already clear.

Shortest path: run the demo once, then compare the backend rows in the printed table.

## Module

```bash
pixi run demo-policy-backends
```

## What To Observe

- The same example and policy interface run across `openpi_pi05`, `lerobot`, and `mock`.
- Latency and action-horizon behavior differ by backend, but the closed-loop contract does not.
- The CSV/JSON artifacts are optional evidence for later release-readiness checks.
