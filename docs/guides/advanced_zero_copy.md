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

To verify that your setup is truly Zero-Copy, run the included benchmark.

```bash
pixi run python examples/advanced/pytorch_cuda_async/benchmark.py --plot benchmark_plot.png
```

**Expected Results:**
- **Throughput**: Should be extremely high (> 10 GB/s, often >> 100 GB/s for large payloads).
- **Explanation**: Since we only send a "pointer" (handle or offset), the transfer time is constant regardless of tensor size (O(1)), leading to effectively infinite MB/s for large tensors.
