---
title: Install
---

# Install

Current launch status: the package and source release are staged, but public PyPI/source access is not the default path until the final release switch. If you already have a source checkout, use Pixi for demos because it includes example files and optional visualization dependencies.

```bash
# public source path after repo visibility flips
git clone https://github.com/openretriever/retriever
cd retriever
pixi install
pixi run demo-basic-flow
pixi run demo-webcam-detection-mock
pixi run demo-webcam-detection
```

The public runtime distribution name is `retriever-core`; the Python import package is `retriever`. The PyPI install path for the `0.0.1` release is fixed, but keep it treated as pending until the package resolves from PyPI:

```bash
pip install retriever-core
```

`demo-webcam-detection-mock` is the deterministic first smoke: synthetic frames, stdout output, no camera permission, no GUI requirement. `demo-webcam-detection` is the live visual step: real webcam, `--visualize auto`, Rerun when available and stdout otherwise.

The source-checkout demo commands install optional example and visualization dependencies that are intentionally not part of the minimal runtime package:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```
