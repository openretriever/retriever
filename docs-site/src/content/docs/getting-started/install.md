---
title: Install
---

# Install

Retriever has two install paths. Use the source checkout today for the working demos, examples, and visualization extras. The package target is `retriever-core` once the 0.0.1 PyPI release resolves.

```bash
git clone https://github.com/openretriever/retriever
cd retriever
pixi install
pixi run demo-basic-flow
pixi run demo-webcam-detection-mock
pixi run demo-webcam-detection
```

After `retriever-core==0.0.1` is published on PyPI, install the minimal runtime package with:

```bash
pip install retriever-core
```

The public runtime distribution name is `retriever-core`; the Python import package is `retriever`.

`demo-webcam-detection-mock` is the deterministic first smoke: synthetic frames, stdout output, no camera permission, no GUI requirement. `demo-webcam-detection` is the live visual step: real webcam, `--visualize auto`, Rerun when available and stdout otherwise.

The source-checkout demo commands install optional example and visualization dependencies that are intentionally not part of the minimal runtime package:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```
