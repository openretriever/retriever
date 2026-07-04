---
title: Install
---

# Install

Retriever has two install tracks. Use the source checkout today for working demos, examples, Rerun visualization, and repository tests. Use the minimal package track after `retriever-core==0.0.1` resolves from PyPI.

## Today: source checkout + Pixi

```bash
git clone https://github.com/openretriever/retriever
cd retriever
pixi install
pixi run demo-webcam-detection-mock
```

Then try the live webcam/Rerun path:

```bash
pixi run demo-webcam-detection
```

This track includes repository examples and optional visualization dependencies. It is the recommended public-preview path until the PyPI package is live.

## Package target: minimal runtime

After `retriever-core==0.0.1` is published on PyPI, install the minimal runtime package with:

```bash
python -m pip install retriever-core
```

The public runtime distribution name is `retriever-core`; the Python import package is `retriever`:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```

The minimal runtime package is for library use. Repository demos such as `demo-webcam-detection`, graph-rendering helpers, Rerun examples, and tutorial assets still require the source checkout unless their dependencies are installed separately.

## First command choice

| Situation | Command |
| --- | --- |
| Reliable first smoke, no camera, no GUI | `pixi run demo-webcam-detection-mock` |
| Live webcam plus Rerun/stdout fallback | `pixi run demo-webcam-detection` |
| Understand the smallest Flow first | `pixi run demo-basic-flow` |
| Render an HTML graph artifact | `pixi run docs-tutorial-perception-html` |

`demo-webcam-detection-mock` is the deterministic first smoke: synthetic frames, stdout output, no camera permission, no GUI requirement. `demo-webcam-detection` is the live visual step: real webcam, `--visualize auto`, Rerun when available and stdout otherwise.

## Next steps

- Run the [Visual Quickstart](/getting-started/visual-quickstart/).
- Compare outputs in [Examples and Results](/tutorials/examples-and-results/).
- Use [Debug and Visualize](/tutorials/debug-and-visualize/) for graph rendering, stepping, recording, and replay.
- Move to [Retriever Hub](/ecosystem/) and [GoldenRetriever](https://retriever-space.pages.dev/) after the core runtime path is clear.
