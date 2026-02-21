---
title: "L03 Clocking Model and Multirate Intuition"
---

# L03 Clocking Model and Multirate Intuition

## Metadata
- Lecture ID: L03
- Track: A (Flow Fundamentals)
- Tier: 1
- Duration: 20 minutes
- Prerequisites: L01-L02

## Learning Objectives
1. Compare `Rate`, `Trigger`, and `Hybrid` clock semantics.
2. Predict execution timing from clock declarations.
3. Explain why clock choice is independent from flow business logic.

## Core Concept
- Mental model: clocks define when a node is eligible to run.
- Key pitfall: using `Rate` where strict event-driven behavior is required.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/a_flow_fundamentals/02_clock_types.py`
- Optional extension: `examples/tutorial/e_resource_and_sync/03_multirate_robot_system.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.02_clock_types
```

## What To Observe
- `Rate(hz=10)` prints periodic scheduling intent.
- `Trigger('value')` prints field-driven semantics.
- `Hybrid(hz=5, trigger=['value'])` prints combined semantics.

## Failure Drill
- Replace a trigger clock with rate clock in an event-driven stage and inspect downstream behavior assumptions.
- Discuss stale or over-sampled data risk.

## Exercise
- Required task: set `Rate(hz=20)` and explain expected impact on producer cadence.
- Stretch task: write one paragraph on when `Hybrid` is safer than pure `Rate`.

## Evaluation Rubric
- Pass criteria: learner predicts schedule behavior without running code.
- Common failure signature: learner confuses queue adapter behavior with clock policy.

## Follow-up
- Next lecture: `l04_building_and_validating_ir.md`
- Related tutorials: `b_ir_and_execution/01_context_graph.py`
