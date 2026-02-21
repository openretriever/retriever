---
title: "L11 Monitoring and Feedback Loops"
---

# L11 Monitoring and Feedback Loops

## Metadata
- Lecture ID: L11
- Track: D (Closed-Loop, State, and Feedback)
- Tier: 3
- Duration: 25 minutes
- Prerequisites: L10

## Learning Objectives
1. Read closed-loop behavior from runtime traces.
2. Distinguish control-loop output vs monitor-event output.
3. Interpret alert events as operational reliability signals.

## Core Concept
- Mental model: monitoring flows emit events only when policy/plant behavior violates expectations.
- Key pitfall: logging everything but defining no actionable alert contract.

## Live Demo Mapping
- Primary runnable files:
  - `examples/tutorial/d_closed_loop_state_feedback/07_feedback_intro.py`
  - `examples/tutorial/d_closed_loop_state_feedback/09_execution_monitoring.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.07_feedback_intro --backend multiprocessing --duration 2
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.09_execution_monitoring --backend multiprocessing --duration 2
```

## What To Observe
- Feedback intro converges toward target with decreasing error.
- Monitoring tutorial emits explicit `STUCK` alerts during injected degradation interval.
- Alert stream is sparse and event-driven by contract.

## Failure Drill
- Tighten stuck threshold and observe alert storm behavior.

## Exercise
- Required: identify which steps show controller convergence and where monitoring triggers alerts.
- Stretch: propose one additional alert condition with a typed output field.

## Evaluation Rubric
- Pass: learner can explain operational difference between state telemetry and alert events.
- Failure signature: learner cannot map an alert to its triggering state condition.

## Follow-up
- Next group: L12-L16 (systems/robotics)
