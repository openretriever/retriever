---
title: "L10 Stateful Flows and Reset Contracts"
---

# L10 Stateful Flows and Reset Contracts

## Metadata
- Lecture ID: L10
- Track: D (Closed-Loop, State, and Feedback)
- Tier: 2-3
- Duration: 20 minutes
- Prerequisites: L07

## Learning Objectives
1. Implement stateful flows with explicit reset behavior.
2. Use `pipe.reset()` to reinitialize pipeline state deterministically.
3. Validate two-run equivalence after reset.

## Core Concept
- Mental model: reset is a contract, not an afterthought.
- Key pitfall: hidden state persisting across debug runs.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/d_closed_loop_state_feedback/04_stateful_flow_reset.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.04_stateful_flow_reset --steps 5 --dt 0.1
```

## What To Observe
- Run #1 increments state as expected.
- Reset clears internal counter state.
- Run #2 restarts from the same initial condition.

## Failure Drill
- Remove `reset()` implementation in `Counter` and show state leakage across runs.

## Exercise
- Required: verify first printed value after reset is identical to first run.
- Stretch: add another state variable and include it in reset contract.

## Evaluation Rubric
- Pass: learner can explain deterministic reset criteria.
- Failure signature: learner cannot detect state leakage in repeated runs.

## Follow-up
- Next lecture: `l11_monitoring_and_feedback_loops.md`
