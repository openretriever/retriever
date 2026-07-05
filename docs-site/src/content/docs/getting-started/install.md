---
title: Install
description: Choose the source-checkout path for demos today, or the minimal runtime package after release.
---

Start with the source checkout if you want working demos, graph rendering, Rerun visualization, and repository tests. Use the package path only after `retriever-core==0.0.1` is available from PyPI.

## One-Minute Source Path

```bash
git clone https://github.com/openretriever/retriever.git
cd retriever
pixi install
pixi run demo-webcam-detection-mock
```

Expected result: a deterministic mock camera graph runs without camera permission, GUI windows, Rerun, or robot hardware. You should see stdout lines for a camera Flow, color detector Flow, display Flow, and detected red/blue objects.

<div class="card-grid">
  <a class="info-card" href="/getting-started/visual-quickstart/"><strong>First visual run</strong><span>Run mock color detection, then switch to webcam and Rerun/stdout.</span></a>
  <a class="info-card" href="/tutorials/examples-and-results/"><strong>Expected outputs</strong><span>Compare command output before reading implementation details.</span></a>
  <a class="info-card" href="/tutorials/debug-and-visualize/"><strong>Debug path</strong><span>Render the graph, step locally, record, and replay.</span></a>
</div>

## Install Tracks

| Track | Use it when | Command |
| --- | --- | --- |
| Source checkout | You want demos, examples, graph rendering, Rerun, replay artifacts, or tests. | `pixi install` then `pixi run demo-webcam-detection-mock` |
| Minimal package | You only need the runtime API after release. | `python -m pip install retriever-core` |

The public runtime distribution name is `retriever-core`; the Python import package is `retriever`:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```

Repository demos such as `demo-webcam-detection`, graph-rendering helpers, Rerun examples, and tutorial assets require the source checkout unless their optional dependencies are installed separately.

## First Command Choice

| Situation | Command |
| --- | --- |
| Reliable first smoke, no camera, no GUI | `pixi run demo-webcam-detection-mock` |
| Live webcam plus Rerun/stdout fallback | `pixi run demo-webcam-detection` |
| Understand the smallest Flow first | `pixi run demo-basic-flow` |
| Render an HTML graph artifact | `pixi run docs-tutorial-perception-html` |
| Record and replay a portable perception run | `pixi run demo-webcam-record` then `pixi run demo-webcam-replay-rrd` |

`demo-webcam-detection-mock` is the deterministic first smoke: synthetic frames, stdout output, no camera permission, no GUI requirement. `demo-webcam-detection` is the live visual step: real webcam, `--visualize auto`, Rerun when available and stdout otherwise.

## If Something Fails

| Symptom | Use this path first | Why |
| --- | --- | --- |
| Clone or install is blocked | Stay on the hosted docs and retry the source checkout later. | The hosted docs remain useful even when a launch surface is temporarily unavailable. |
| Camera permission or hardware fails | `pixi run demo-webcam-detection-mock` | Proves the runtime graph without local devices. |
| Rerun does not open | Keep the stdout path or use `--visualize stdout`. | Separates viewer setup from runtime correctness. |
| A graph behaves unexpectedly | `pixi run docs-tutorial-perception-html` | Inspect nodes, ports, clocks, and sync policies first. |
| A result is hard to reproduce | `pixi run demo-webcam-record` then replay. | Turns timing-sensitive inputs into a stable artifact. |

## Next Steps

- Run the [Visual Quickstart](/getting-started/visual-quickstart/).
- Compare outputs in [Examples and Results](/tutorials/examples-and-results/).
- Use [Debug and Visualize](/tutorials/debug-and-visualize/) for graph rendering, stepping, recording, and replay.
- Move to [Retriever Hub](/ecosystem/) and [GoldenRetriever](https://retriever-space.pages.dev/examples/) after the core runtime path is clear.
