---
title: Hub Modules
---

# Hub Modules

A Hub module is a reusable Retriever component with a stable public surface.

Good module boundaries include:

- typed payloads such as poses, detections, task commands, and action chunks
- perception, localization, planning, policy, or control Flows
- transforms between common robotics/data formats
- pipeline factories that expose a stable public surface while keeping internals replaceable

Keep one-off tutorial code in the examples tree until the public boundary is stable.

## Module reference shape

Users load modules with string references:

```python
from retriever import hub

module = hub.use("org/name")
FlowCls = hub.use("org/name:Export")
VersionedFlow = hub.use("org/name:Export@0.1.0")
```

- `hub.use("org/name")` returns a module proxy over declared exports.
- `hub.use("org/name:Export")` returns the exported class, function, type, or value.
- `@version` pins the module ref to a release/tag understood by the Hub index.

The module repository declares its export table in `pyproject.toml` under
`[tool.retriever.module]`. Users should not need to read that metadata for the
common import path.
