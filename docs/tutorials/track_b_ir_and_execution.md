---
title: "Track B: IR and Execution"
---

# Track B: IR and Execution

Focus: pipeline validation, IR structure, execution graph build, and backend behavior.

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

## What To Observe

- Graph-level validation and error surfaces.
- Runtime differences between multiprocessing and Dora.
- Perception and request/response in the same contract model.
- Hard-gated backend parity artifacts in `logs/tutorial_parity/`.

Expected output reference:
- `examples/tutorial/expected_outputs/032_backend_parity_benchmark.md`
