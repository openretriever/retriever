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

## The Debug Loop

<div class="card-grid">
  <div class="info-card"><strong>1. Inspect structure</strong><span>Render the graph before changing runtime code. Ports, clocks, sync policies, and feedback edges should be visible.</span></div>
  <div class="info-card"><strong>2. Prove local logic</strong><span>Use the stepper path to set breakpoints in <code>Flow.step(...)</code> without backend scheduling noise.</span></div>
  <div class="info-card"><strong>3. Remove hardware risk</strong><span>Use mock perception before live camera or Rerun. The output should be deterministic.</span></div>
  <div class="info-card"><strong>4. Save evidence</strong><span>Record once, replay many times, then share the exact artifact instead of a timing-sensitive anecdote.</span></div>
</div>

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

<div class="html-artifact-card">
  <div class="artifact-card-header">
    <div>
      <p class="eyebrow">Live graph</p>
      <strong>The perception pipeline, rendered by the runtime</strong>
      <p>The same interactive HTML <code>pipe.visualize()</code> writes — pan, zoom, and inspect nodes, ports, clocks, and sync policies inline.</p>
    </div>
    <a href="/artifacts/tutorial_perception.html" target="_blank" rel="noreferrer">Open full graph</a>
  </div>
  <iframe
    class="artifact-frame"
    src="/artifacts/tutorial_perception.html"
    title="Retriever perception pipeline graph"
    loading="lazy"
  ></iframe>
</div>

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

### Set a breakpoint in `Flow.step()` (VS Code)

This is the payoff of stepping: `pipe.step()` runs the whole graph **in your
own Python process**, so a normal debugger stops inside your Flow with full
locals. No backend process to attach to, no remote debugger.

1. Put a breakpoint in the Flow you want to inspect:

   ```python
   class ColorDetector(Flow[CameraOut, Detections]):
       def step(self, input: CameraOut) -> Detections:
           hsv = to_hsv(input.image)        # ← breakpoint here
           hits = self.match(hsv)
           return Detections(objects=hits)
   ```

2. Run the stepper script under the debugger — VS Code **Run and Debug** (F5)
   on the file that calls `pipe.step()`, or attach to `pixi run demo-stepper`.

3. Execution stops on that line. In the **Variables** pane you can read
   `input._signals` (which ports fired), `self` state carried between steps,
   and every intermediate — then step through `match()` line by line.

Because the stepper is single-process and synchronous, `pipe.step(dt=0.1)`
advances one tick and returns; the debugger treats your Flow like any other
function. Get the logic right here first — then run it on `multiprocessing` or
`dora`, where each Flow is a separate process and breakpoints are far harder.

<!-- To add: a short screen recording of the debugger stopped inside step(). -->

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
| Rerun does not open | Force stdout visualization with the command below | Separates runtime correctness from viewer setup. |
| Webcam is unreliable | Use `pixi run demo-webcam-detection-mock` | Proves the graph without hardware or permissions. |
| Run is hard to reproduce | Run `pixi run demo-webcam-record`, then `pixi run demo-webcam-replay-rrd` | Turns timing-sensitive input into a stable artifact. |
| Backend differs from local stepping | Compare stepper output, rendered graph, and backend output | Clock/sync choices are often the real difference. |

Exact stdout fallback when viewer setup is the suspected issue:

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception \
  --backend in-process \
  --camera-mode mock \
  --visualize stdout \
  --duration 10
```

## What To Save When Asking For Help

If you need another person or an AI agent to debug the run, include these instead of a screenshot alone:

- the command you ran, including `--backend`, `--camera-mode`, and `--visualize`;
- `artifacts/tutorial_perception.html` when graph shape is relevant;
- the first 20-40 lines of stdout around the failure;
- `logs/perception.rrd` or `logs/perception.mcap` when the issue depends on live sensor timing;
- whether the failing path used mock frames, live webcam, Rerun, multiprocessing, or Dora.

That bundle lets the next reader distinguish graph wiring, Flow logic, viewer setup, sensor timing, and backend scheduling.

## Continue

- Use [Examples and Results](/tutorials/examples-and-results/) for notebook-style expected outputs.
- Use [Time and Sync](/concepts/time-and-sync/) if the issue is event timing or edge sampling.
- Use the [GoldenRetriever Hub quickstart](https://golden.retriever.build/examples/golden-hub-proof/) after the core visual debugging path works.
