---
title: "Tutorials"
---

# Tutorials

This page lists the available tutorials and examples included in the repository.

## Basic Tutorials

- **b_ir_and_execution/06_dora_perception**: Basic camera -> detection -> display pipeline using the Dora backend.
- **b_ir_and_execution/07_request_response**: Demonstrates Service RPC patterns.
- **c_debug_and_replay/02_debug_perception_stepper**: Shows how to use the stepper for frame-by-frame debugging.
- **d_closed_loop_state_feedback/01_closed_loop_env**: Closed-loop control example (simulated environment).

To run any tutorial:

```sh
pixi run demo-webcam-detection
# or
python -m examples.tutorial.b_ir_and_execution.06_dora_perception
```

## Advanced Examples

- **PyTorch/CUDA Zero-Copy**: `examples/advanced/pytorch_cuda_async`
  - Demonstrates ultra-fast zero-copy tensor transfer.
  - See [Zero-Copy Guide](../guides/advanced_zero_copy.md).

- **VLA Inference**: `examples/advanced/vla_inference_optim`
  - Optimization for Vision-Language-Action models.
