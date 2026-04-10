---
title: "Walkthrough: Stepper, Debugger, and MCAP Replay"
---

# Walkthrough: Stepper, Debugger, and MCAP Replay

This is the shortest operational path for debugging in Retriever.

## Why this workflow exists

- `step()` gives you debugger-friendly, in-process execution.
- `record` captures one real session.
- `replay` lets you rerun that session without hardware variance.
- incident and session inspection drills confirm your diagnosis is repeatable.

## Phase 1: Step Through Logic

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
```

Set a breakpoint inside `Flow.step()` and rerun with `--fail-at 3` if you want
an exception-driven stop.

## Phase 2: Record Real Data

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 10
```

Artifacts:

- `logs/perception.rrd`
- `logs/perception.mcap`

## Phase 3: Replay the Same Session

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 10 --visualize cv2
```

Or use the combined public task:

```bash
pixi run demo-record-replay
```

## Phase 4: Verify the Diagnosis

```bash
pixi run demo-incident-replay
pixi run verify-incident-replay
```

Use `demo-incident-replay` for the narrative drill and `verify-incident-replay`
for the stricter pass/fail gate.

## Phase 5: Inspect MCAP Output

```bash
pixi run demo-mcap-session-inspection
```

This produces a compact session summary and per-step table that are convenient
for notebook analysis or CI artifact review.

## Common mode selection

- Use `step()` when logic correctness is still the main question.
- Use `run(backend=...)` when validating multiprocessing or Dora behavior.
- Use `record/replay` whenever the bug is timing-sensitive or hardware-tied.
