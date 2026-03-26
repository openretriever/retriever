---
title: "Walkthrough: Stepper, Debugger, and MCAP Replay"
---

# Walkthrough: Stepper, Debugger, and MCAP Replay

This is the shortest semantic path for debugging in Retriever.

## Why This Workflow Exists
- `step()` is for logic debugging with real breakpoints in-process.
- `record` captures real sensor behavior once.
- `replay` lets you re-run the same data many times without hardware variance.
- incident drills verify your diagnosis is reproducible, not a one-off guess.

## Phase 1: Step Through Pipeline Logic
Goal: prove local logic and state transitions are correct.

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
```

What to look for:
- deterministic step-by-step output
- clear failing step if you inject failure (`--fail-at 3`)

## Phase 2: Debug Inside `Flow.step()`
Goal: inspect intermediate values while stepping.

1. Open the flow file used by the tutorial.
2. Put a breakpoint inside `run()`.
3. Re-run stepper command from Phase 1.
4. Inspect typed input/output payloads per step.

Use this phase before trying multiprocessing/dora backend debugging.

## Phase 3: Record Real Data to MCAP
Goal: capture one real session that can be replayed repeatedly.

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10
```

Artifact:
- `logs/perception.mcap`

## Phase 4: Replay the Same Session
Goal: reproduce behavior exactly and iterate quickly.

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
```

What to look for:
- stable, repeatable output across runs
- debugging changes affect logic, not input randomness

## Phase 5: Incident Drill and Diagnosis Consistency
Goal: verify your incident diagnosis survives replay.

```bash
pixi run verify-incident-replay
```

Artifacts:
- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`

Pass condition:
- live and replay diagnosis signatures match
- root cause is identified

## Common Mode Selection
- Use `step()` when writing/fixing flow logic.
- Use `run(backend=...)` when validating runtime behavior.
- Use `record/replay` when hardware or timing noise makes bugs hard to reproduce.
