---
title: Debug and Visualize
---
Retriever debugging should start before a robot backend is involved. Use the same Pipeline source and move through four increasingly concrete views: graph, local stepper, live visualization, and replay artifact.

## The Debug Loop

| Question | Command | Artifact |
| --- | --- | --- |
| Did I wire the graph I intended? | `pixi run docs-tutorial-perception-html` | `artifacts/tutorial_perception.html` |
| Does Flow logic work in ordinary Python? | `pixi run demo-stepper` | stdout step trace |
| Does perception work without camera/GUI risk? | `pixi run demo-webcam-detection-mock` | stdout detection events |
| Does live perception visualize correctly? | `pixi run demo-webcam-detection` | Rerun viewer or stdout fallback |
| Can I debug the same events again? | `pixi run demo-webcam-record` then `pixi run demo-webcam-replay-rrd` | `logs/perception.rrd`, `logs/perception.mcap` |

## Render the Graph

```bash
pixi run docs-tutorial-perception-html
```

Open the generated HTML artifact and inspect:

- Flow nodes,
- input/output ports,
- each Flow clock,
- each edge sync policy,
- feedback edges and fan-in points.

When a robot pipeline feels confusing, this is usually the first artifact to inspect because it shows timing and handoff decisions without requiring a backend.

## Step Locally

```bash
pixi run demo-stepper
pixi run demo-perception-stepper
```

The stepper path is useful because it keeps debugging inside ordinary Python:

```python
pipe.validate()

for _ in range(10):
    result = pipe.step(dt=0.1)
    print(result.executed)

pipe.close_stepper()
```

Use this mode when you want breakpoints inside `Flow.step(...)`, deterministic local state changes, or a short failing case before launching multiprocessing or dora.

## Visualize Perception Runs

Use the deterministic mock/stdout path first when you are checking setup, running headless, or asking an agent to verify the graph:

```bash
pixi run demo-webcam-detection-mock
```

Then use the live webcam path. It tries Rerun first and falls back to stdout when a viewer is not available:

```bash
pixi run demo-webcam-detection
```

Useful variants:

```bash
pixi run demo-webcam-detection-mp-rerun
pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception \
  --backend in-process \
  --camera-mode mock \
  --visualize stdout \
  --duration 10
```

Use Rerun when you need to inspect image frames, detections, and timing visually. Use stdout when the question is simply whether the graph runs and emits events.

## Record and Replay

```bash
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
```

A recorded run gives you a stable artifact for debugging, regression tests, and sharing evidence. The default record command writes `logs/perception.rrd` plus `logs/perception.mcap`, then the replay command consumes the recorded events instead of relying on live camera timing.

## Practical Triage

- **Graph looks wrong:** render the graph and inspect nodes, ports, clocks, and edge sync policies.
- **Flow logic looks wrong:** use the stepper commands and set breakpoints inside `step(...)`.
- **Visualization is missing:** force `--visualize stdout` to separate runtime issues from viewer issues.
- **Behavior changes between runs:** record once, then replay the same events.
- **Backend behavior differs from local stepping:** keep the same Pipeline source, compare stepper output with multiprocessing/Rerun output, then inspect the rendered graph for clock or sync-policy differences.

For concrete expected outputs, continue to [Examples and Results](/tutorials/examples-and-results/).
