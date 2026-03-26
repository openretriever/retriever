---
title: "L07 Stepper-First Debugging"
---

# L07 Stepper-First Debugging

## Metadata
- Lecture ID: L07
- Track: C (Debug and Replay)
- Tier: 2
- Duration: 20 minutes
- Prerequisites: L01-L06

## Learning Objectives
1. Use `Pipeline.step()` for in-process debugging with real breakpoints.
2. Explain why child-process backends are not the first tool for local logic debugging.
3. Capture deterministic debug traces as release-readiness evidence.

## Core Concept
- Mental model: debug logic in-process first, then validate behavior on runtime backends.
- Key pitfall: trying to debug `Flow.step()` logic directly in multiprocessing mode.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/c_debug_and_replay/01_debug_stepper.py`
- Extension file: `examples/tutorial/c_debug_and_replay/06_trace_contract_basics.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
```

## What To Observe
- Step output is deterministic and breakpoint-friendly.
- Trace report includes top latency edges and first bottleneck record.
- Output artifacts are written to `logs/tutorial_trace/`.

## Failure Drill
- Run with `--fail-at 3` in `01_debug_stepper` and inspect the exact step where exception is raised.

## Exercise
- Required: reproduce one failure with `--fail-at`, then run again without failure.
- Stretch: adjust `--lag-ms` in trace tutorial and compare bottleneck edge ranking.

## Evaluation Rubric
- Pass: learner can explain when to use `step()` vs `run(...)`.
- Failure signature: learner cannot tie a trace event back to a concrete edge/node stage.

## Follow-up
- Next lecture: `l08_record_replay_and_determinism.md`
