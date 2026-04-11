---
title: "Zero-Copy PyTorch Transfer Guide"
---

# Zero-Copy PyTorch Transfer Guide

Zero-copy transport matters only when tensors cross a process boundary. In Retriever, that is a backend concern,
not something you manually implement inside `Flow.step(...)`.

For the dora runtime path, Retriever uses serializer helpers in
`src/retriever/rt/backend/dora/serde.py` to avoid unnecessary copies when the payload type and environment support it.

## What Users Need To Know

1. Return tensors normally from `@io` envelopes.
2. CPU tensors and CUDA tensors use different transport paths.
3. Zero-copy is best-effort across supported backends, not a blanket guarantee for every tensor layout.
4. If transport cost matters, benchmark the backend you actually plan to run.

## CPU Tensors

For CPU tensors, Retriever follows the standard shared-memory path:

`torch.Tensor -> NumPy view -> Arrow/shared memory -> NumPy view -> torch.Tensor`

This can stay zero-copy when the tensor layout is compatible with the conversion path.

## CUDA Tensors

For CUDA tensors, Retriever uses CUDA IPC handles instead of copying device memory back to CPU.
That keeps the payload on the GPU, but it depends on backend support, driver setup, and device visibility in the worker processes.

## What Your Code Looks Like

```python
from retriever.flow import Flow, io


@io
class PolicyOut:
    hidden_state: "torch.Tensor"


class Policy(Flow[None, PolicyOut]):
    def step(self, _):  # type: ignore[override]
        return PolicyOut(hidden_state=self.model_state)
```

You return the tensor normally. Retriever decides how to serialize it for the selected backend.

## Caveats

- `Pipeline.step(...)` runs in-process, so transport overhead is usually irrelevant there.
- Non-contiguous tensors or unsupported environments may fall back to a copy.
- Claims about throughput depend on payload size, backend, and device placement.

## Validation

If you need to verify behavior, inspect `src/retriever/rt/backend/dora/serde.py` and benchmark a real pipeline on the target backend rather than relying on a synthetic claim in the abstract.
