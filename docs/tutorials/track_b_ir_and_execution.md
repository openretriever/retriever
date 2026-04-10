---
title: "Track B: IR and Execution"
---

# Track B: IR and Execution

Focus: canonical examples from `examples/tutorial/b_ir_and_execution/`.

## Modules

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.01_context_graph
pixi run python -m examples.tutorial.b_ir_and_execution.02_ir_validation
pixi run python -m examples.tutorial.b_ir_and_execution.03_execution_build
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution
pixi run python -m examples.tutorial.b_ir_and_execution.05_dora_simple
pixi run demo-webcam-detection
pixi run demo-webcam-detection-dora
pixi run python -m examples.tutorial.b_ir_and_execution.07_request_response
pixi run python -m examples.tutorial.b_ir_and_execution.08_detection_window_stats
pixi run python -m examples.tutorial.b_ir_and_execution.09_backend_parity_benchmark
```

## What To Observe

- The difference between authored pipelines, IR, and execution graphs.
- How `validate()` / execution lowering changes what gets deployed.
- When to use multiprocessing vs explicit Dora execution.
- How backend parity and request/response surfaces are checked.
