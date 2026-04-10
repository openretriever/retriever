---
title: "Zero-Copy PyTorch Transfer Guide"
---

# Zero-Copy PyTorch Transfer Guide

This guide explains how `retriever` achieves ultra-high performance zero-copy tensor transfer between PyTorch processes.

## 1. The Challenge

Transferring large neural network tensors (hundreds of MBs or GBs) between processes typically incurs massive overhead due to:
1.  **Serialization**: Copying data into a buffer (pickling).
2.  **Transport**: Sending bytes over a socket or pipe.
3.  **Deserialization**: Reconstructing the tensor in the receiver.

For real-time (robotics) or high-throughput (training) applications, this latency is unacceptable.

## 2. The Solution: "Zero-Copy" Protocol

"Zero-Copy" means the receiving process accesses the **exact same physical memory** as the sender, with no data duplication.

### Architecture

The `retriever` framework (via its `dora` backend) natively handles this for you using `src/retriever/rt/backend/dora/serde.py`.

#### A. CPU Tensors (Shared Memory)

We rely on the standard integration path for the Python data ecosystem:
**PyTorch** ↔ **NumPy** ↔ **PyArrow** ↔ **Shared Memory**

1.  **Sender**:
    - `tensor.numpy()`: Returns a Numpy view of the tensor. This is **Zero-Copy** (pointer passing).
    - `pa.array(numpy_array)`: Creates an Arrow array from the Numpy view. This is **Zero-Copy** (if memory is contiguous).
    - **Transmission**: The Arrow array is placed in Shared Memory (RAM mapped to multiple processes).
2.  **Receiver**:
    - **Reception**: Maps the Shared Memory block.
    - `arrow_array.to_numpy()`: Returns a Numpy view of the shared memory.
    - `torch.from_numpy(numpy_array)`: Creates a PyTorch tensor wrapping that memory.

**Why not pass PyTorch directly to PyArrow?**
PyArrow does not natively accept PyTorch Tensors (`pa.array(tensor)` fails). The `numpy()` bridge is the standard, efficient, and zero-overhead way to expose the memory buffer to Arrow.

#### B. CUDA Tensors (IPC Handles)

For GPU tensors, we cannot use system RAM. We use **CUDA IPC (Inter-Process Communication)**.

1.  **Sender**:
    - Captures a **CUDA IPC Handle** (a small descriptor pointing to the GPU memory address).
    - Sends this highly lightweight handle (~bytes) via shared memory.
2.  **Receiver**:
    - Opens the IPC Handle.
    - Maps the remote GPU memory directly into its own virtual address space.

This allows different processes to operate on the same GPU memory buffer without ever moving data to the CPU.

## 3. Implementation Details

You do **not** need to handle this manually. The framework's serializer detects `torch.Tensor` objects automatically.

**Your Code (app.py):**
```python
# Sending
return SourceOutput(hidden_state=my_tensor)

# Receiving
my_tensor = input.hidden_state.to(device)
```

**Framework Logic (serde.py):**
```python
if isinstance(value, torch.Tensor):
    if value.device.type == "cuda":
        # Create IPC Handle
        return serialize_cuda_handle(value)
    else:
        # Create Numpy View -> Arrow
        return pa.array(value.numpy()) 
```

## 4. Performance Verification

This trimmed runtime repo does not currently ship a standalone zero-copy
benchmark script. The practical way to verify the path is:

1. send a large `torch.Tensor` through a Dora-backed Retriever pipeline,
2. confirm the serializer stays on the tensor-specific path in
   `src/retriever/rt/backend/dora/serde.py`,
3. measure end-to-end latency/throughput in your own benchmark harness.

Expected behavior:
- **Throughput** should stay high for large tensors because the transfer path is
  dominated by lightweight shared-memory or CUDA-IPC handles rather than full
  tensor copies.
- **CPU tensors** should stay on the PyTorch → NumPy → Arrow zero-copy bridge
  when memory is contiguous.
- **CUDA tensors** should stay on the CUDA IPC handle path instead of bouncing
  through host memory.
