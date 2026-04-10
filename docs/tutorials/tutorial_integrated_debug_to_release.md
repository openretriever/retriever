---
title: "Integrated Tutorial: Debug to Release"
---

# Integrated Tutorial: Debug to Release

This is the shortest end-to-end workflow for using Retriever on a real project:
write flow logic, debug it in-process, record one reproducible session, replay
that session while iterating, and turn the resulting artifacts into a release
readiness decision.

All commands below assume you are in the repository root.

## One-Time Setup

```bash
pixi install
```

## Interface Map

Keep these locations in mind:

- `examples/tutorial/` contains the runnable public examples.
- `docs/tutorials/` contains the walkthroughs and lecture-style notes.
- `pixi.toml` contains the public task surface.
- `logs/` is the evidence/output directory for recordings and reports.

## Part 1: Start With In-Process Debugging

Use the stepper first. `Pipeline.step()` executes in your current process, so
breakpoints inside `Flow.step()` work the way you expect.

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
```

Try again with an injected failure:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5 --fail-at 3
```

What to inspect:

- typed input/output payloads at each step
- per-flow state before and after the failing step
- whether `reset()` returns the flow to a clean baseline

## Part 2: Capture Timing Evidence

Once the logic is correct, capture a trace contract so you can explain where
time went and which edge first became the bottleneck.

```bash
pixi run demo-trace-contract
```

Artifacts:

- `logs/tutorial_trace/tut024_trace_envelopes.jsonl`
- `logs/tutorial_trace/tut024_trace_report.json`

## Part 3: Record One Session and Mirror It to MCAP

Record once, then replay as many times as you need.

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 10
```

That gives you two complementary artifacts:

- `logs/perception.rrd` for Rerun-centric inspection
- `logs/perception.mcap` as a compact interchange artifact

## Part 4: Replay the Same Session While You Iterate

Replay keeps the input fixed while you change code.

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 10 --visualize cv2
```

You can also use the bundled combined task:

```bash
pixi run demo-record-replay
```

Use replay when you want debugger-friendly iteration without hardware variance.

## Part 5: Run Incident and Inspection Drills

Once record/replay works, exercise the exact artifacts you would use during an
incident review.

```bash
pixi run demo-incident-replay
pixi run demo-mcap-session-inspection
```

Artifacts:

- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`
- `logs/tutorial_mcap/tut036_mcap_session_summary.json`
- `logs/tutorial_mcap/tut036_mcap_step_table.jsonl`

## Part 6: Add Run Manifests and Lineage

Release readiness is not just "it worked once". You need a run id, artifact
hashes, and a replay command that another person can use.

```bash
pixi run demo-manifest-lineage
```

That writes a manifest bundle under `logs/tutorial_manifest/`.

## Part 7: Turn Artifacts Into a GO / NO-GO Decision

Finish with the release-readiness walkthrough.

```bash
pixi run demo-release-readiness
```

That task reads the public reference pack, checks the required artifacts, and
returns an explicit `GO` / `NO-GO` decision.

## Rule of Thumb

- Use `step()` when writing or debugging flow logic.
- Use `run(backend=...)` when validating backend/runtime behavior.
- Use record/replay when hardware variance or timing makes bugs hard to
  reproduce.
- Treat `.rrd`, `.mcap`, trace JSON, and manifests as the evidence bundle for a
  real release review.
