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

```py
from retriever.core.flow import Pipeline
from retriever.core.ir import validate, build_execution
from retriever.core.rt import execute_ir

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
