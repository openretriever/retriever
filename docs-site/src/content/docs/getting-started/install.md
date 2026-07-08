---
title: Install
description: Use the source checkout for demos, then use the runtime package track when you only need the API.
---

Install from source. Retriever ships a repository of runnable demos, graph-rendering scripts, Rerun visualization, and tests — none of which are useful without the source tree. Pixi builds the environment and runs every demo through one command.

**What you'll get:** a Python 3.11 environment with `retriever-core` installed editable, plus a working first demo you can run in under a minute — no camera, no GUI, no robot hardware.

## 1. Clone and build the environment

```bash
git clone https://github.com/openretriever/retriever.git
cd retriever
pixi install
```

`pixi install` reads `pixi.toml`, resolves conda and PyPI dependencies, pins Python to 3.11, and installs `retriever-core` as an editable package. Every demo is a Pixi task, so you never manage a virtualenv by hand.

## 2. Run the first demo

```bash
pixi run demo-webcam-detection-mock
```

This is the deterministic first smoke: synthetic camera frames, stdout output, no camera permission, no GUI, no backend to configure. Stripped of INFO log lines, it prints:

```text
============================================================
Perception Demo - Live or Mock Camera to Detection

Building perception pipeline:
  Camera @ Rate(20Hz) -> ColorDetector @ Trigger -> Display @ Rate

✓ Graph created: 3 nodes, 5 edges

Running for 0.1 seconds...
Tip: This run is using mock frames. Use --camera-mode real to require a live webcam path.
------------------------------------------------------------
  Frame 1: 2 objects - [('red_object', '0.95'), ('blue_object', '0.95')]
------------------------------------------------------------
```

A camera Flow emitted a frame, a color detector sampled it, and a display Flow printed the detections. The graph ran to a fixed duration and stopped. If you see this, the runtime works.

<div class="card-grid">
  <a class="info-card" href="/getting-started/visual-quickstart/"><strong>Visual quickstart</strong><span>The fastest first success, then the live webcam and Rerun path.</span></a>
  <a class="info-card" href="/tutorials/examples-and-results/"><strong>Examples and results</strong><span>Several demos, each paired with its real output.</span></a>
  <a class="info-card" href="/tutorials/"><strong>Tutorial path</strong><span>The ordered route from first demo to robot examples.</span></a>
</div>

## The runtime API

The distribution name is `retriever-core`; the import package is `retriever`:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```

A Flow is a stateful stream function. You declare typed IO with `@io`, subclass `Flow`, and override `step()`:

```python
@io
class NumberInput:
    value: int

@io
class NumberOutput:
    result: int

class DoubleFlow(Flow[NumberInput, NumberOutput]):
    def step(self, input: NumberInput):
        return NumberOutput(result=input.value * 2)
```

You compose Flows into a `Pipeline`, giving each edge an explicit `sync=` policy, then debug in-process before deploying async:

```python
pipe.step(dt=0.1)              # advance the graph in-process, deterministically
pipe.run(backend="dora")       # deploy async; also "multiprocessing" or "in-process"
```

The same timestamped input trace yields the same output trace regardless of backend scheduling. That functional determinism is what makes local stepping, record, and replay well-defined.

## Runtime-only package (target track)

Once `retriever-core` is published to PyPI, users who only need the API — not the demos, graph renderer, or tutorial assets — will install it directly:

```bash
python -m pip install retriever-core   # planned; not yet on PyPI
```

Until then, the source checkout above is the supported path, and it is the only path that includes the repository demos, `docs-tutorial-*` graph renderers, Rerun examples, and tests.

## First-command reference

| Situation | Command |
| --- | --- |
| Reliable first smoke, no camera, no GUI | `retriever webcam-mock` or `pixi run demo-webcam-detection-mock` |
| Live webcam with automatic Rerun/stdout fallback | `retriever webcam` or `pixi run demo-webcam-detection` |
| Understand the smallest Flow first | `retriever basic-flow` or `pixi run demo-basic-flow` |
| Render an interactive HTML graph | `retriever graph` or `pixi run docs-tutorial-perception-html` |
| Record a run, then replay it | `retriever record` then `retriever replay` |

`demo-webcam-detection` needs a real webcam and uses `--visualize auto` (Rerun when available, stdout otherwise). If you have no camera or a permission prompt blocks it, stay on `-mock`.


## Retriever CLI wrapper

The source checkout also installs a small `retriever` console script. It does not
replace Pixi; it wraps the same Pixi tasks with shorter names:

```bash
retriever webcam-mock      # pixi run demo-webcam-detection-mock
retriever webcam           # pixi run demo-webcam-detection
retriever graph            # pixi run docs-tutorial-perception-html
retriever run demo-basic-flow
```

Use `retriever tasks` to see the curated aliases. Use raw `pixi run ...` whenever
you want the exact task name or Pixi environment flags.

## If something fails

| Symptom | Try first | Why |
| --- | --- | --- |
| Camera permission or hardware fails | `pixi run demo-webcam-detection-mock` | Proves the runtime graph with no local devices. |
| Rerun viewer does not open | `pixi run demo-perception-stepper` | Separates viewer setup from runtime correctness. |
| A graph behaves unexpectedly | `pixi run docs-tutorial-perception-html` | Inspect nodes, ports, clocks, and sync policies first. |
| A result is hard to reproduce | `pixi run demo-webcam-record` then replay | Turns timing-sensitive input into a stable artifact. |

## Next steps

- [Visual Quickstart](/getting-started/visual-quickstart/) — see the first run, then switch to live webcam and Rerun.
- [Examples and Results](/tutorials/examples-and-results/) — compare real command output before reading source.
- [Debug and Visualize](/tutorials/debug-and-visualize/) — render the graph, step locally, record, and replay.
