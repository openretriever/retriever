---
title: "Track F: Policy Backends"
---

# Track F: Policy Backends

Focus: backend abstraction for closed-loop policy execution (`openpi_pi05`, `lerobot`, `mock`).

## Module

```bash
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
```

## What To Observe

- Graph topology remains unchanged while backend switches.
- Timing/chunk metrics vary by backend implementation.

## Expected Artifacts (P0)

- `logs/tutorial_policy/tut027_backend_metrics.csv`
- `logs/tutorial_policy/tut027_backend_metrics.json`
