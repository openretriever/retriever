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

### 1.1 Logical graph: `IR`

`IR` is produced by validation:

`Pipeline.validate() → IR`

It describes:

- nodes: flow identity + clock config + ports
- edges: port mapping + adapter + queue sizes

This is the stable “FRP intent” boundary.

### 1.2 Physical graph: `ExecutionGraph`

`ExecutionGraph` is produced by execution build/compilation:

`IR → build_execution() → ExecutionGraph`

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

### 2.1 Pipeline surface (Recommended)

```python
pipe.run(backend="dora", duration=10.0)
```

`retriever.run(...)` still exists as a convenience wrapper around the thread-local
default pipeline. Use an explicit `Pipeline` object for review code, scripts, and
reusable examples.

### 2.2 Low-Level (IR Access)

```py
from retriever.flow import Pipeline
from retriever.rt import execute_ir

pipe = Pipeline("demo")
...

ir = pipe.validate()               # logical graph
graph = pipe.build_execution()     # physical graph (partitions + placement)
execute_ir(graph, backend="dora")  # runs the compiled graph
```

Notes:

- `execute_ir(...)` accepts either `IR` or `ExecutionGraph`.
- If you pass an `IR` directly, you’re implicitly choosing “one executor per flow node”.

### 2.3 Unified Recording & Replay

For deterministic persisted recordings, prefer the explicit stepper surface:

```python
pipe.record("session.rrd", steps=50, dt=0.1, visualize=True)
```

`.rrd` is the native Rerun inspection artifact and is replayable for Retriever session recordings. `.mcap` remains the mirror/interchange artifact:

```python
from retriever import RecordConfig

pipe.record(RecordConfig(path="session.rrd", mirrors=("session.mcap",)), steps=50, dt=0.1)
```

If you want a wall-clock-bounded in-process run that also persists artifacts, be explicit:

```python
pipe.run(
    backend="in-process",
    duration=5.0,
    record=RecordConfig(path="session.rrd", mirrors=("session.mcap",)),
)
```

To replay:
```python
# Inject recorded data into a flow source
pipe.replay(camera, path="session.rrd")  # `.mcap` works too
pipe.run(backend="in-process")
```

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

## 5) Lowering to an executable IR (implementation detail)

Current backends still consume an `IR` where each node is a runnable executor. To bridge this,
`ExecutionGraph.to_execution_ir()` materializes a backend-friendly IR by lowering each grouped partition into a
single node.

Implementation notes:

- The lowered node type is currently named `FusedFlow` (legacy naming).
- Provenance is stored in the IR optimization metadata (legacy field naming preserved internally).

---

## 6) Where this goes next

This split (logical IR vs physical execution graph) is the foundation for:

- explicit placement (multi-process, multi-host, Ray tasks/actors)
- backend selection per partition (e.g., local mp vs dora vs ray)
- richer compilation (non-linear partitions, watermark-aware operators, explicit adapters)

This guide documents the supported public execution surface. Longer-term execution-graph extensions should preserve the same IR and backend boundaries.

## 7) Distributed Execution (Multi-Machine)

Retriever supports distributing pipelines across multiple computers using the **Dora** backend. This is useful for splitting lighter controller logic (low latency) from heavy compute (GPU).

### 7.1 `deploy(machine: str)`

You can map specific flows to machines using the `.deploy()` method:

```python
# Robot Interface on Local Controller
robot_io = RobotInterface() @ Rate(50)
robot_io.deploy("machine_a")

# Heavy Model on Remote GPU Server
vla_model = VLAFlow() @ Trigger("image")
vla_model.deploy("machine_b")
```

### 6.2 Runtime Deployment Overrides (Preferred)
### 7.2 Runtime Deployment Overrides (Preferred)

Decouple your code from physical infrastructure by specifying deployment at runtime:

```python
pipe.run(
    backend="dora",
    deploy={
        robot_io: "machine_alpha",
        vla_model: "machine_beta"
    }
)
```

### 7.3 Backend Configuration

For this to work, you must use the **Dora** backend and have a running Dora Coordinator.

1. **Configure Dora**: Define `machine_a` and `machine_b` in your `coordinator.yaml`.
2. **Start Daemons**: Run `dora daemon --machine-id machine_a` on respective hosts.
3. **Run Pipeline**: `pipe.run(backend="dora")`.

Retriever compiles the Python deployment tags into Dora's node constraints (`_unstable_deploy`).

---

## 8) Native Node Performance

Retriever supports native backends (Rust/C++) via `native_overrides`. When benchmarking:

1. **Serialization Overhead**: Small messages (e.g., 6 floats) may be dominated by Arrow serialization/deserialization costs. Python can sometimes be faster for trivial inputs due to zero overhead in passing data across boundaries (when using `multiprocessing` backend in simple modes) or simply because the serialization cost outweighs the compute cost.
2. **Throughput vs Compute**: Native nodes shine when:
   - Compute load is high (e.g., heavy math, computer vision).
   - Throughput requirements exceed Python's GIL limitations (e.g., >1000 Hz).
3. **Rate Limiting**: Ensure your pipeline `Rate` does not artificially cap performance. A `Rate(hz=50)` will limit all backends to 50 Hz, masking any performance differences.
