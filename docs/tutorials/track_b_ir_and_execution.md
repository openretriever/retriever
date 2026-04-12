---
title: "Track B: IR and Execution"
---

# Track B: IR and Execution

Focus: pipeline validation, IR structure, execution graph build, and backend behavior.

## Start Here

Run these in order:
- `04_rt_execution`
- `02_ir_validation`
- `03_execution_build`

Use these later, once the basic execution story is clear:
- `05_dora_simple`
- `06_dora_perception`
- `09_backend_parity_benchmark`

`06_dora_perception` keeps a historical filename. The public learning path is backend-neutral; Dora is optional and should be requested explicitly.

## Modules

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.01_context_graph
pixi run python -m examples.tutorial.b_ir_and_execution.02_ir_validation
pixi run python -m examples.tutorial.b_ir_and_execution.03_execution_build
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution
pixi run python -m examples.tutorial.b_ir_and_execution.05_dora_simple
pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception
pixi run python -m examples.tutorial.b_ir_and_execution.07_request_response
pixi run python -m examples.tutorial.b_ir_and_execution.08_detection_window_stats --backend multiprocessing --duration 3
pixi run python -m examples.tutorial.b_ir_and_execution.09_backend_parity_benchmark
```

## Generate An HTML View

Run this from the repository root. The snippet imports a repo-local helper from
`support/`, so the repository root needs to be on the default Python path.

```bash
pixi run env PYTHONPATH=src:. python - <<'PY'
from examples.shared.perception_runtime import build_tutorial_perception_pipeline

path = build_tutorial_perception_pipeline(
    use_real_camera=False,
    show_window=False,
).visualize("/tmp/tutorial_perception.html")

print(path)
PY
```

## What To Observe

- Graph-level validation and error surfaces.
- The difference between “inspect the graph” and “run the graph”.
- Backend differences only after the basic runtime model is clear.
