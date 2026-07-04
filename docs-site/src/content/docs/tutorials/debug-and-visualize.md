---
title: Debug and Visualize
---

# Debug and Visualize

Retriever should be easy to inspect before you run a robot backend. If you want concrete command outputs first, start with [Examples and Results](/tutorials/examples-and-results/). The recommended debugging loop is:

1. render the graph,
2. step the same graph in-process,
3. record the consumed events,
4. replay the run when behavior changes.

## Render a graph

```bash
pixi run docs-tutorial-perception-html
```

This writes an HTML artifact with nodes, ports, clocks, and sync policies. Open the generated file and check:

- which Flows are in the graph,
- which clock wakes each Flow,
- which sync policy is on each edge,
- whether the graph has expected feedback loops.

When a robot pipeline feels confusing, this is usually the first artifact to inspect because it shows timing and handoff decisions without requiring a backend.

## Step locally

```bash
pixi run demo-stepper
pixi run demo-perception-stepper
```

The stepper path is useful because it keeps debugging inside ordinary Python. The idea is the same in your own script:

```python
pipe.validate()

for _ in range(10):
    result = pipe.step(dt=0.1)
    print(result.executed)

pipe.close_stepper()
```

Use this mode when you want breakpoints inside `Flow.step(...)`, deterministic local state changes, or a short failing case before launching multiprocessing or dora.

## Visualize perception runs

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

## Record and replay

```bash
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
```

A recorded run gives you a stable artifact for debugging, regression tests, and sharing evidence. The default record command writes `logs/perception.rrd` plus `logs/perception.mcap`, then the replay command consumes the recorded events instead of relying on live camera timing.

## A practical debugging checklist

- **Graph looks wrong**: run `pixi run docs-tutorial-perception-html` and inspect nodes, ports, clocks, and edge sync policies.
- **Flow logic looks wrong**: use `pixi run demo-stepper` or `pixi run demo-perception-stepper` and set breakpoints inside `step(...)`.
- **Visualization is missing**: rerun the perception demo with `--visualize stdout` to separate runtime issues from viewer issues.
- **Behavior changes between runs**: record once with `pixi run demo-webcam-record`, then replay with `pixi run demo-webcam-replay-rrd`.
- **Backend behavior differs from local stepping**: keep the same Pipeline source, compare stepper output with the multiprocessing/Rerun command, then inspect the rendered graph for clock or sync-policy differences.
