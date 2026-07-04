---
title: Install
---

# Install

Retriever's public runtime distribution name is `retriever-core`; the Python import package is `retriever`. The planned package install path is:

```bash
pip install retriever-core
```

For source-checkout demos while release preparation is ongoing, use Pixi from the repo root:

```bash
pixi install
pixi run demo-basic-flow
pixi run demo-webcam-detection
```

The source-checkout demo commands install optional example and visualization dependencies that are intentionally not part of the minimal runtime package:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```
