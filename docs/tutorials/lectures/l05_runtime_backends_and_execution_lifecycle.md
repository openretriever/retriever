---
title: "L05 Runtime Backends and Execution Lifecycle"
---

# L05 Runtime Backends and Execution Lifecycle

## Metadata
- Lecture ID: L05
- Track: B (IR and Execution)
- Tier: 2
- Duration: 25 minutes
- Prerequisites: L04

## Learning Objectives
1. Run the same contract on multiprocessing and (optionally) Dora backends.
2. Explain runtime lifecycle phases: build, start, run, stop.
3. Read executor/channel counts and key runtime logs as health signals.

## Core Concept
- Mental model: backends change execution engine, not pipeline contract.
- Key pitfall: mixing backend transport concerns into application flow logic.

## Live Demo Mapping
- Primary runnable files:
  - `examples/tutorial/b_ir_and_execution/04_rt_execution.py`
  - `examples/tutorial/b_ir_and_execution/05_dora_simple.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution --backend multiprocessing --duration 2
pixi run python -m examples.tutorial.b_ir_and_execution.05_dora_simple --backend multiprocessing --duration 2
```

Optional if Dora runtime is installed:

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.05_dora_simple --backend dora --duration 2
```

## What To Observe
- Runtime logs show pipeline build and executor/channel counts.
- Stage outputs show deterministic transform chain (for example final value `12`, then `14`).
- Lifecycle logs include start, wait timeout/duration stop, and clean termination.

## Failure Drill
- Run with unsupported backend config and inspect startup error path.
- Identify whether failure is pre-run validation vs runtime backend bring-up.

## Exercise
- Required task: run both commands and compare stdout shape between examples.
- Stretch task: enable `--print-ir` on `05_dora_simple.py` and map runtime behavior to IR fields.

## Evaluation Rubric
- Pass criteria: learner can explain which runtime signals prove healthy start/stop.
- Common failure signature: learner reads only flow prints and ignores runtime lifecycle logs.

## Follow-up
- Next lecture: `l06_pipeline_ergonomics_and_composition_antipatterns.md`
- Related tutorials: `a_flow_fundamentals/05_pipeline_ergonomics.py`
