---
title: "L02 Typed IO and Adapter Semantics"
---

# L02 Typed IO and Adapter Semantics

## Metadata
- Lecture ID: L02
- Track: A (Flow Fundamentals)
- Tier: 1
- Duration: 20 minutes
- Prerequisites: L01

## Learning Objectives
1. Explain typed port mapping between upstream and downstream flows.
2. Distinguish `Latest`, `Hold`, and `Window` adapter behavior.
3. Wire adapters intentionally via `then(..., map=..., sync=...)`.

## Core Concept
- Mental model: edges are contracts, and adapters define sampling semantics on edges.
- Key pitfall: assuming default sampling matches control intent.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/a_flow_fundamentals/03_adapter_connection.py`
- Optional extension: `examples/tutorial/e_resource_and_sync/01_multirate_window.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
```

## What To Observe
- Adapter printout includes `Latest`, `Hold`, and `Window` parameters.
- Port map `temperature -> temp` is explicit and visible.
- Pipeline reports exactly 1 connection and 2 flows in this demo.

## Failure Drill
- Break the map key intentionally (for example map `temperature` to a wrong destination field) and rerun.
- Observe validation/connection error and identify contract mismatch root cause.

## Exercise
- Required task: switch sync from `Latest()` to `Hold(debounce=0.2)` and explain behavioral expectation.
- Stretch task: introduce a second mapped field and verify edge contract remains explicit.

## Evaluation Rubric
- Pass criteria: learner can choose adapter based on data freshness vs smoothing need.
- Common failure signature: learner treats adapter choice as performance-only instead of semantics.

## Follow-up
- Next lecture: `l03_clocking_and_multirate_intuition.md`
- Related tutorials: `a_flow_fundamentals/02_clock_types.py`
