---
title: "L09 Synchronization and Fan-In/Fan-Out Behavior"
---

# L09 Synchronization and Fan-In/Fan-Out Behavior

## Metadata
- Lecture ID: L09
- Track: E (Resource and Synchronization)
- Tier: 2-3
- Duration: 20 minutes
- Prerequisites: L03, L04

## Learning Objectives
1. Explain multi-rate coordination with edge adapters.
2. Understand fan-out sampling and fan-in aggregation behavior.
3. Diagnose dropped-frame/backpressure signals in runtime logs.

## Core Concept
- Mental model: sampling semantics are edge-level decisions, not node-level guesses.
- Key pitfall: assuming downstream rates automatically preserve all upstream events.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/e_resource_and_sync/01_multirate_window.py`
- Optional extension: `examples/tutorial/e_resource_and_sync/02_synchronization.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.01_multirate_window --backend multiprocessing --duration 2
```

Optional fan-in sync demo:

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.02_synchronization
```

## What To Observe
- 30Hz source + 10Hz smoother + 1Hz printer behavior is visible in output cadence.
- `Window(..., agg="mean")` stabilizes downstream signal.
- Runtime warnings indicate queue pressure and sampling tradeoffs.

## Failure Drill
- Reduce buffer/window settings and observe increased dropped-frame warnings.

## Exercise
- Required: tune duration/window and explain trend smoothness changes.
- Stretch: compare `Window` behavior with a `Latest`-only edge in the same topology.

## Evaluation Rubric
- Pass: learner can explain where fan-in/out behavior is defined in the graph.
- Failure signature: learner cannot relate queue warnings to adapter/rate decisions.

## Follow-up
- Next lecture: `l10_stateful_flows_and_reset_contracts.md`
