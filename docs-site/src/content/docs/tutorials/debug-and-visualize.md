---
title: Debug and Visualize
description: Inspect graphs, step locally, visualize perception, and replay recorded runs.
---
Retriever debugging should start before a robot backend is involved. Use one source graph and move through four views: render the graph, step it locally, visualize events, then record and replay the same run.

## Fast Path

Run these in order when a graph feels wrong:

```bash
pixi run docs-tutorial-perception-html
pixi run demo-stepper
pixi run demo-webcam-detection-mock
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
```

| Stage | Question it answers | Artifact to inspect |
| --- | --- | --- |
| Render | Did I wire the graph I intended? | `artifacts/tutorial_perception.html` |
| Step | Does Flow logic work in ordinary Python? | stdout step trace |
| Mock perception | Does perception work without camera or GUI risk? | stdout detection events |
| Record | Can I preserve the run as evidence? | `logs/perception.rrd`, `logs/perception.mcap` |
| Replay | Can I debug the same events again? | replay stdout and recorded events |

## 1. Render The Graph First

```bash
pixi run docs-tutorial-perception-html
```

Typical output:

```text
[Success] Visualization saved to: artifacts/tutorial_perception.html
Open this file in your browser to view the interactive graph.
```

Open the generated HTML and check these before debugging backend behavior:

- Flow nodes: is every module present?
- Ports: do input and output names match what the code expects?
- Clocks: which Flow wakes itself, and which Flow wakes on upstream events?
- Sync policies: how is upstream history sampled before `step(...)` runs?
- Feedback edges: where can closed-loop state re-enter the graph?

If this graph is wrong, fix wiring first. Do not start by debugging multiprocessing, Rerun, or camera setup.

## 2. Step Locally

```bash
pixi run demo-stepper
```

Typical output:

```text
=== step 0 ===
[Sink] got value=2

=== step 1 ===
[Sink] got value=4
```

Use local stepping when you want to set breakpoints inside `Flow.step(...)`, inspect local state, or reduce a backend issue to a small deterministic case. The mental model is ordinary Python:

```python
pipe.validate()

for _ in range(10):
    result = pipe.step(dt=0.1)
    print(result.executed)

pipe.close_stepper()
```

For perception-specific stepping without camera permissions or GUI windows:

```bash
pixi run demo-perception-stepper
```

## 3. Visualize Perception Safely

Start with mock frames and stdout. This is the reliable path for laptops, CI, remote machines, and AI-agent verification.

```bash
pixi run demo-webcam-detection-mock
```

Typical output includes:

```text
Building perception pipeline:
  Camera @ Rate(20Hz) -> ColorDetector @ Trigger -> Display @ Rate

Graph created: 3 nodes, 5 edges
Frame 1: 2 objects - [('red_object', '0.95'), ('blue_object', '0.95')]
```

Then switch to a live webcam path:

```bash
pixi run demo-webcam-detection
```

That command uses real camera input with `--visualize auto`: Rerun when a viewer is available, stdout otherwise. Use Rerun when you need to inspect image frames, detections, and timing visually. Use stdout when the question is simply whether the graph runs and emits events.

Useful variants:

```bash
pixi run demo-webcam-detection-mp-rerun
pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception \
  --backend in-process \
  --camera-mode mock \
  --visualize stdout \
  --duration 10
```

## 4. Record And Replay

```bash
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
```

The record command writes replayable artifacts:

```text
logs/perception.rrd
logs/perception.mcap
```

Replay consumes recorded events instead of relying on live camera timing. Use this when behavior changes between runs, when you need to share evidence, or when downstream logic should be debugged without a sensor attached.

## Practical Triage

| Symptom | First action | Why |
| --- | --- | --- |
| Graph shape is surprising | Render `artifacts/tutorial_perception.html` | Wiring, clocks, ports, and sync policies are visible there. |
| Flow output is wrong | Run `demo-stepper` or `demo-perception-stepper` | Keeps debugging in ordinary Python before backend scheduling enters. |
| Rerun does not open | Force stdout visualization | Separates runtime correctness from viewer setup. |
| Webcam is unreliable | Use `demo-webcam-detection-mock` | Proves the graph without hardware or permissions. |
| Run is hard to reproduce | Record once, replay many times | Turns timing-sensitive input into a stable artifact. |
| Backend differs from local stepping | Compare stepper output, rendered graph, and backend output | Clock/sync choices are often the real difference. |

## Continue

- Use [Examples and Results](/tutorials/examples-and-results/) for notebook-style expected outputs.
- Use [Time and Sync](/concepts/time-and-sync/) if the issue is event timing or edge sampling.
- Use [Golden examples](https://retriever-space.pages.dev/examples/) after the core visual debugging path works.
