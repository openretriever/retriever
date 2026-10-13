---
title: "Walkthrough: Stepper, Debugger, and MCAP Replay"
---

# Walkthrough: Stepper, Debugger, and MCAP Replay

For MCAP session inspection, `MCAPReader.read_all()` uses the writer's step
boundaries in file order. Nearby or equal timestamps do not merge steps. Keep
each step's metadata before its payloads when processing a recording; orphaned,
duplicate, or timestamp-mismatched payloads raise `ValueError` instead of being
silently dropped or reassigned. The writer's format is unchanged.

`pipe.replay(...)` supplies a source's recorded values sequentially. If a
downstream decision depends on time, drive the original clock schedule as well;
equal replayed values alone do not establish equal timing-dependent decisions.

This is the shortest operational path for debugging in Retriever.

## Why this workflow exists

- `step()` gives you debugger-friendly, in-process execution.
- `record` captures one deterministic session by default.
- `replay` lets you rerun that session without hardware variance.
- incident and session inspection drills confirm your diagnosis is repeatable.

## Phase 1: Step Through Logic

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
```

Set a breakpoint inside `Flow.step()` and rerun with `--fail-at 3` if you want
an exception-driven stop.

## Phase 2: Record a Deterministic Session

```bash
pixi run demo-webcam-record
```

Artifacts:

- `logs/perception.rrd`
- `logs/perception.mcap`

The packaged task records deterministic mock frames by default so replay works the same way on any machine. If you explicitly want a live webcam capture instead:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --camera-mode real
```

## Phase 3: Replay the Same Session

```bash
pixi run demo-webcam-replay-rrd
pixi run demo-webcam-replay-mcap
```

Use `stdout` as the cross-platform default. On a local desktop session, you can opt into GUI replay:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 10 --visualize stdout
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10 --visualize rerun
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
- Use `record/replay` whenever the bug is timing-sensitive or hardware-tied. Start with the deterministic mock path, then opt into live hardware only when that is part of the bug.
