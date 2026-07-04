---
title: Install
---

# Install

Retriever's public runtime distribution name is `retriever-core`; the Python import package is `retriever`. The PyPI install path for the `0.0.1` release is:

```bash
pip install retriever-core
```

Until that package is published, use the source-checkout path below if you already have repository access. It is also the recommended route for demos because it includes the example files and optional visualization dependencies. Public clone access opens when the GitHub repo visibility is flipped for launch.

```bash
# public source path after repo visibility flips
git clone https://github.com/openretriever/retriever
cd retriever
pixi install
pixi run demo-basic-flow
pixi run demo-webcam-detection
```

The source-checkout demo commands install optional example and visualization dependencies that are intentionally not part of the minimal runtime package:

```python
from retriever.flow import Flow, Pipeline, Rate, io
```
