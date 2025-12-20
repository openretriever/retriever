# Tutorials

This page lists the available tutorials and examples included in the repository.

## Basic Tutorials

- **009_dora_perception**: Basic camera -> detection -> display pipeline using the Dora backend.
- **010_request_response**: Demonstrates Service RPC patterns.
- **013_debug_perception_stepper**: Shows how to use the stepper for frame-by-frame debugging.
- **016_closed_loop_env**: Closed-loop control example (simulated environment).

To run any tutorial:

```sh
pixi run demo-dora  # runs 009_dora_perception
# or
python -m examples.tutorial.009_dora_perception
```

## Advanced Examples

- **PyTorch/CUDA Zero-Copy**: `examples/advanced/pytorch_cuda_async`
  - Demonstrates ultra-fast zero-copy tensor transfer.
  - See [Zero-Copy Guide](../guides/advanced_zero_copy.md).

- **VLA Inference**: `examples/advanced/vla_inference_optim`
  - Optimization for Vision-Language-Action models.
