---
title: "L01 Retriever Mental Model (Flow, TemporalFlow, Pipeline)"
---

# L01 Retriever Mental Model (Flow, TemporalFlow, Pipeline)

## Metadata
- Lecture ID: L01
- Track: A (Flow Fundamentals)
- Tier: 0-1
- Duration: 20 minutes
- Prerequisites: baseline `pixi` environment in `retriever/`

## Learning Objectives
1. Explain `Flow` as typed input/output transformation.
2. Explain `TemporalFlow` as `Flow` bound to a clock.
3. Explain `Pipeline` as explicit graph owner for composition and execution.

## Core Concept
- Mental model: write pure flow logic first, then bind time, then wire graph.
- Key pitfall: mixing graph concerns into flow logic too early.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/a_flow_fundamentals/01_basic_flow.py`
- Optional extension: `examples/tutorial/a_flow_fundamentals/04_full_pipeline.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
```

## What To Observe
- `Input type` and `Output type` are explicit and printed.
- `_signals` differs between empty input and populated input.
- Result values match simple deterministic math (`5 -> 10`, `7 -> 14`).

## Failure Drill
- Remove `@flow_io` from one dataclass and rerun.
- Observe contract/type handling degrade and discuss why typed boundary is required.

## Exercise
- Required task: change `DoubleFlow` to triple the value and verify output.
- Stretch task: add one more output field and handle `_signals` consistently.

## Evaluation Rubric
- Pass criteria: learner can explain each layer (`Flow`, clock binding, pipeline wiring) using this demo.
- Common failure signature: learner describes clocks as business logic instead of temporal scheduling.

## Follow-up
- Next lecture: `l02_typed_io_and_adapter_semantics.md`
- Related tutorials: `a_flow_fundamentals/03_adapter_connection.py`
