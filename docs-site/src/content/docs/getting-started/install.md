---
title: Install
description: Use the source checkout for demos, then use the runtime package track when you only need the API.
---

The `retriever` command lives in the `retriever-core` package. There are two ways to get it:

- **Package install** — `pip install retriever-core`. This is all you need for the runtime API and the `retriever` CLI.
- **Source checkout** — clone the repo for the bundled demos, graph renderers, Rerun visualization, and tests.

On the source path you do **not** run `pip install` yourself: Retriever uses [Pixi](https://pixi.sh) as its package and environment manager, and the checkout installs `retriever-core` (editable) into a Pixi environment for you. The `retriever` command wraps Pixi, so you rarely call `pixi` directly.

**What you'll get from the source path:** a Python 3.11 environment with `retriever-core` installed editable, plus a working first demo you can run in under a minute — no camera, no GUI, no robot hardware.

## 1. Package install

The public package target is `retriever-core`; the import package and executable command are both `retriever`:

```bash
python -m pip install retriever-core
retriever --version
```

After package install, create a tiny reproducible starter workspace:

```bash
retriever init my-retriever-app --bootstrap-pixi
cd my-retriever-app
retriever run hello
```

`retriever init` creates a minimal Pixi workspace and a `main.py` that imports the runtime. Use this path for new projects that do not need the repository demos.

## 2. Source checkout for demos

```bash
git clone https://github.com/openretriever/retriever.git
cd retriever
retriever install --bootstrap-pixi
```

`retriever install` installs the source checkout environment. It can bootstrap Pixi first, then runs the checkout install.

## 3. Run the first demo

```bash
retriever run webcam-mock
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
from retriever import Flow, Pipeline, Rate, io
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

Users who only need the API — not the repository demos, graph renderer, or tutorial assets — install the runtime package directly:

```bash
python -m pip install retriever-core
```

The source checkout remains the path for repository demos, `docs-tutorial-*` graph renderers, Rerun examples, and tests.

## First-command reference

| Situation | Command |
| --- | --- |
| Reliable first smoke, no camera, no GUI | `retriever run webcam-mock` |
| Live webcam with automatic Rerun/stdout fallback | `retriever run webcam` |
| Understand the smallest Flow first | `retriever run basic-flow` |
| Render an interactive HTML graph | `retriever run graph` |
| Record a run, then `retriever run replay` it | `retriever run record` then `retriever run replay` |

`demo-webcam-detection` needs a real webcam and uses `--visualize auto` (Rerun when available, stdout otherwise). If you have no camera or a permission prompt blocks it, stay on `-mock`.


## Retriever command surface

`retriever` is the package executable, installed by `pip install retriever-core`.
From a source checkout with the environment built, run the demos with it directly:

```bash
retriever run webcam-mock
retriever run webcam
retriever run graph
retriever run basic-flow
```

Use `retriever tasks` to see the curated run targets. Raw repository task names
still work through `retriever run <task>` when you need an exact source-checkout
entrypoint. Curated names are the public path; raw task names are an escape hatch
for repository contributors.

Hub commands do not require a source checkout. They operate on Hub refs and use the same loader as `hub.use(...)`:

```bash
retriever hub parse openretriever/hello-world:HelloFlow
retriever hub inspect openretriever/hello-world --json
retriever hub cache-dir
```

Use `retriever --dry-run hub inspect <ref>` when you want to validate the ref shape without fetching anything. Use `--refresh` when you intentionally want to bypass an existing cache entry.

## If something fails

| Symptom | Try first | Why |
| --- | --- | --- |
| Camera permission or hardware fails | `retriever run webcam-mock` | Proves the runtime graph with no local devices. |
| Rerun viewer does not open | `retriever run perception-stepper` | Separates viewer setup from runtime correctness. |
| A graph behaves unexpectedly | `retriever run graph` | Inspect nodes, ports, clocks, and sync policies first. |
| A result is hard to reproduce | `retriever run record` then `retriever run replay` | Turns timing-sensitive input into a stable artifact. |

## Next steps

- [Visual Quickstart](/getting-started/visual-quickstart/) — see the first run, then switch to live webcam and Rerun.
- [Examples and Results](/tutorials/examples-and-results/) — compare real command output before reading source.
- [Debug and Visualize](/tutorials/debug-and-visualize/) — render the graph, step locally, record, and replay.
