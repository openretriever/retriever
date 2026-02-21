---
title: "L06 Pipeline Ergonomics and Composition Antipatterns"
---

# L06 Pipeline Ergonomics and Composition Antipatterns

## Metadata
- Lecture ID: L06
- Track: A (Flow Fundamentals)
- Tier: 1-2
- Duration: 20 minutes
- Prerequisites: L01-L05

## Learning Objectives
1. Show equivalence of explicit/context/functional authoring styles.
2. Validate that style choice does not change graph contract.
3. Identify composition antipatterns that hurt readability and maintenance.

## Core Concept
- Mental model: choose authoring style for clarity, not behavior changes.
- Key pitfall: accidental implicit pipeline coupling when using functional style carelessly.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/a_flow_fundamentals/05_pipeline_ergonomics.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode context --exec step --steps 3
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode functional --exec step --steps 3
pixi run python -m examples.tutorial.a_flow_fundamentals.05_pipeline_ergonomics --mode explicit --exec mp --duration 2
```

## What To Observe
- IR summary line is stable across modes (`nodes=3`, `edges=2`).
- Stepper modes print deterministic sink progression (`2`, `4`, `6`).
- MP run confirms same contract in runtime backend.

## Failure Drill
- Comment out default pipeline reset in functional mode and run multiple times.
- Observe potential hidden coupling from ambient global pipeline state.

## Exercise
- Required task: select one preferred authoring mode and justify it for team-scale code review.
- Stretch task: produce a short anti-pattern list from this file for onboarding docs.

## Evaluation Rubric
- Pass criteria: learner can switch modes without changing contract-level behavior.
- Common failure signature: learner assumes functional style is always safer/faster.

## Follow-up
- Next lecture group: L07-L11 (Debug and Reliability)
- Related tutorials: `c_debug_and_replay/01_debug_stepper.py`, `c_debug_and_replay/06_trace_contract_basics.py`
