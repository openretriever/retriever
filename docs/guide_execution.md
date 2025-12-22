---
title: "Execution Build (IR → ExecutionGraph)"
---

# Execution Build (IR → ExecutionGraph)

Retriever distinguishes between a **logical graph** (what you want) and a **physical graph** (how it runs).

Historically the project called this step “IR optimization”. That wording is misleading: we are not changing
pipeline semantics, we are producing a *separate execution graph* that describes **partitioning** and
(eventually) **placement**.

---

## 1) The two graphs

### 1.1 Logical graph: `IRStruct`

`IRStruct` is produced by validation:

`Pipeline (or FlowContext) → validate() → IRStruct`

It describes:

- nodes: flow identity + clock config + ports
- edges: port mapping + adapter + queue sizes

This is the stable “FRP intent” boundary.

### 1.2 Physical graph: `ExecutionGraph`

`ExecutionGraph` is produced by execution build/compilation:

`IRStruct → build_execution() → ExecutionGraph`

It describes:

- **partitions**: groups of flow node ids that should run together
- **cross-partition edges**: boundaries that require messaging between executors
- **placement hints**: where a partition should run (currently informational)

`ExecutionGraph` is *not* the backend-specific descriptor (e.g., Dora YAML). Backends may further compile the
execution graph into their own concrete formats.

Today, partitions are limited to *linear chains* (the current partitioner), but the API is intentionally
general so we can later support non-linear subgraphs and multi-node deployment.

---


## 2) Canonical API

### 2.1 Unified (Recommended)

```python
import retriever

# Implicit execution of default pipeline
retriever.run(backend="dora", duration=10.0)

# With manual pipeline
pipe.run(backend="dora", duration=10.0)
```

### 2.2 Low-Level (IR Access)

```py
from retriever.flow import Pipeline
from retriever.ir import validate, build_execution
from retriever.rt import execute_ir

pipe = Pipeline("demo")
...

ir = validate(pipe)                # logical graph
graph = build_execution(ir)        # physical graph (partitions + placement)
execute_ir(graph, backend="dora")  # runs the compiled graph
```

Notes:

- `execute_ir(...)` accepts either `IRStruct` or `ExecutionGraph`.
- If you pass an `IRStruct` directly, you’re implicitly choosing “one executor per flow node”.
- `compile_execution(...)` remains as a compatibility alias for `build_execution(...)`.

---

## 3) Policies (grouping / co-location)

`build_execution(..., policy=...)` uses a *grouping predicate* (legacy name: fusion predicate) to decide which
flows can safely run together.

Builtins:

- `"conservative"`
- `"aggressive"`
- `"strict"`

These policies are composed from predicates like:

- `linear_chain`
- `not_in_cycle`
- `same_effective_rate`
- `latest_adapter`

---

## 4) Interactive Stepping (Debugging)

For debugging logic without running the full runtime, you can manually step the pipeline in-process.

```python
import retriever

# Ensure state is fresh
retriever.reset()

# Manually advance time by dt
retriever.step(dt=0.1)

# Check your flows/state...
retriever.step(dt=0.1)
```

**Note**: `retriever.step` simulates execution in the *current process*. It ignores the `backend` argument normally passed to `run()`.

---

## 4) Lowering to an executable IR (implementation detail)

Current backends still consume an `IRStruct` where each node is a runnable executor. To bridge this,
`ExecutionGraph.to_execution_ir()` materializes a backend-friendly IR by lowering each grouped partition into a
single node.

Implementation notes:

- The lowered node type is currently named `FusedFlow` (legacy naming).
- Provenance is stored in `IRStruct.optimization` (legacy name; it records the grouping map).

---

## 5) Where this goes next

This split (logical IR vs physical execution graph) is the foundation for:

- explicit placement (multi-process, multi-host, Ray tasks/actors)
- backend selection per partition (e.g., local mp vs dora vs ray)
- richer compilation (non-linear partitions, watermark-aware operators, explicit adapters)

See also: `docs/temp_notes/2025-12-16_outline_design_alignment.md`.

## 6) Native Node Performance

Retriever supports native backends (Rust/C++) via `native_overrides`. When benchmarking:

1.  **Serialization Overhead**: Small messages (e.g., 6 floats) may be dominated by Arrow serialization/deserialization costs. Python can sometimes be faster for trivial inputs due to zero overhead in passing data across boundaries (when using `multiprocessing` backend in simple modes) or simply because the serialization cost outweighs the compute cost.
2.  **Throughput vs Compute**: Native nodes shine when:
    - Compute load is high (e.g., heavy math, computer vision).
    - Throughput requirements exceed Python's GIL limitations (e.g., >1000 Hz).
3.  **Rate Limiting**: Ensure your pipeline `Rate` does not artificially cap performance. A `Rate(hz=50)` will limit all backends to 50 Hz, masking any performance differences.

