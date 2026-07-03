---
title: Install
---

# Install

Retriever is published as a Python runtime package. The public release target is:

```bash
pip install pyretriever
```

For this repository while release preparation is ongoing, use Pixi from the repo root:

```bash
pixi install
pixi run demo-basic-flow
pixi run demo-webcam-detection
```

The import package is still `retriever`:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```
