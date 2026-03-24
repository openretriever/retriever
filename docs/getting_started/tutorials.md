---
title: "Tutorials"
---

# Tutorials

Canonical tutorials are grouped into one-level topic tracks under `examples/tutorial/`.

## Start Here

1. Read the runtime quickstart first: [../quickstart.md](../quickstart.md)
2. Skim the tutorial entrypoint: [`examples/tutorial/README.md`](../../examples/tutorial/README.md)
3. Pick one of the restructured topic tracks:
   - `examples/tutorial/a_flow_fundamentals`
   - `examples/tutorial/b_ir_and_execution`
   - `examples/tutorial/c_debug_and_replay`
   - `examples/tutorial/d_closed_loop_state_feedback`
   - `examples/tutorial/e_resource_and_sync`
   - `examples/tutorial/f_policy_backends`
   - `examples/tutorial/g_operations_interfaces`
   - `examples/tutorial/h_release_readiness`

## Recommended first runs

```bash
pixi run demo-dora-simple
pixi run demo-webcam-detection
pixi run demo-record-replay
pixi run demo-perception-stepper
```

## Advanced Examples

- **PyTorch/CUDA Zero-Copy**: `examples/advanced/pytorch_cuda_async`
  - Demonstrates ultra-fast zero-copy tensor transfer.
  - See [Zero-Copy Guide](../guides/advanced_zero_copy.md).

- **VLA Inference**: `examples/advanced/vla_inference_optim`
  - Optimization for Vision-Language-Action models.
