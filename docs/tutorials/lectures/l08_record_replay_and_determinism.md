---
title: "L08 Record/Replay Workflows and Determinism"
---

# L08 Record/Replay Workflows and Determinism

## Metadata
- Lecture ID: L08
- Track: C (Debug and Replay)
- Tier: 2
- Duration: 20 minutes
- Prerequisites: L07

## Learning Objectives
1. Run a deterministic perception debug loop without hardware.
2. Understand the role of recording/replay in post-incident analysis.
3. Separate data capture from logic debugging.

## Core Concept
- Mental model: replay gives reproducible inputs so debugging focuses on logic, not sensors.
- Key pitfall: using live sensors for every debugging iteration.

## Live Demo Mapping
- Primary runnable file: `examples/tutorial/c_debug_and_replay/02_debug_perception_stepper.py`
- Extension file: `examples/tutorial/c_debug_and_replay/04_record_replay_perception.py`
- Incident drill extension: `examples/tutorial/c_debug_and_replay/07_incident_response_replay_drill.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.02_debug_perception_stepper
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 4
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 4 --visualize cv2
pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
```

Optional longer capture path:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 10
```

## What To Observe
- Deterministic synthetic-frame outputs in stepper mode.
- Replay run executes in-process and does not require live camera input.
- Same detector logic is reusable across debug and replay flows.

## Failure Drill
- Intentionally modify color threshold logic and confirm replay exposes regression consistently.

## Exercise
- Required: run debug stepper and replay mode; compare output stability.
- Stretch: record a short hardware session and replay it through the same path.

## Evaluation Rubric
- Pass: learner can describe why replay reduces debugging variance.
- Failure signature: learner treats replay as a backend switch instead of an input-control strategy.

## Follow-up
- Next lecture: `l09_synchronization_and_fan_in_fan_out.md`
