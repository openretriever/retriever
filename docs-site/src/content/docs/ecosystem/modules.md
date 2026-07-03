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

```toml
[name]
package = "your-org/lidar-slam"
exports = ["LidarSlamFlow", "build_pipeline"]
version = "0.1.0"
```
