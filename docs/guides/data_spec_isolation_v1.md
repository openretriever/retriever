# Data Tooling Boundary v1

## Summary

This note is historical context for why Retriever keeps dataset/export contracts in
`retriever.types.data` while keeping runtime execution semantics elsewhere.

The near-term recommendation is:

1. Keep Retriever runtime independent from large external data-tool layers.
2. Isolate a small read tool and a mock data write tool outside the main Retriever runtime package.
3. Treat those tools as a small standalone test surface for data workflows.
4. Keep only a narrow adapter boundary inside Retriever for any integration points that are genuinely useful today.

This lets data-focused collaborators experiment on a simpler surface without having to absorb the full Retriever runtime model.

## Why Isolate This

Today, the strongest use cases for the data contract layer are around:

- typed stream identifiers and schema references
- recording and replay utilities
- offline data exchange and dataset tooling
- experiments that do not need the full runtime

The weaker use case is trying to make the data contract layer the main execution
model for Retriever itself. The current runtime already has working flow, step,
and replay semantics. Forcing data/export concerns into the core runtime would
create unnecessary coupling.

In practice, the current shape suggests three layers:

- **Retriever runtime**
  - flow execution, scheduling, backends, replay orchestration, visualization
- **Data tools**
  - reading structured recordings or datasets
  - producing mock data for testing pipelines
- **Shared data contracts**
  - minimal typed identifiers and schemas used by the data tools

Only the last two need to be shared with external collaborators at this stage.

## Recommended Split

### 1. Keep In Retriever

These belong in the main repo and should not depend on a broad all-in-one data layer:

- runtime stepping and flow execution
- backend-specific transport and scheduling
- pipeline composition
- visualization and live logging
- replay orchestration from persisted artifacts

Retriever should only keep small adapter points for external data tooling.

### 2. Move Out As Data-Collaborator Tools

These are good candidates for isolation into a small companion package or repo:

- **read tool**
  - load recordings or dataset shards
  - enumerate streams
  - return typed records in a stable offline-friendly format
- **mock data write tool**
  - emit synthetic or hand-authored test streams
  - generate deterministic fixtures
  - write small datasets or recording-like artifacts for collaborator testing
- **minimal shared types**
  - stream IDs
  - schema references
  - optional clock-domain metadata

This gives collaborators a self-contained loop:

1. generate mock data
2. write artifact
3. read artifact
4. validate expected typed structure

They should not need to run a full Retriever pipeline to do this.

## Minimal Shared Surface

The shared layer should stay intentionally small.

Suggested scope:

- `StreamId`
- `SchemaRef`
- optional `ClockDomain`
- a small record envelope for offline events or samples

Suggested non-goals for now:

- full runtime event buffer semantics
- execution-time scheduling semantics
- broad flow typing integration
- trying to unify all Retriever runtime data movement under one new abstraction

If the shared layer cannot be explained on one page, it is too large for the current collaborator-testing phase.

## Proposed External Tooling Shape

One reasonable split is:

- `data_tools/`
  - `read_tool.py`
  - `mock_write_tool.py`
  - `types.py`
  - `fixtures/`
  - `tests/`

The read tool should answer questions like:

- what streams exist?
- what schema is attached to each stream?
- what records are available in a given range?
- can I materialize those records as plain Python objects, Arrow-like rows, or simple typed payloads?

The mock write tool should answer questions like:

- can I generate a tiny deterministic test artifact?
- can I generate a multi-stream artifact with known ordering?
- can I generate malformed or partial cases for robustness testing?

## Retriever Integration Boundary

Retriever should integrate with these tools through a narrow boundary:

- import a minimal schema/type surface if needed
- call the read tool for offline replay or import
- call the mock write tool in tests or examples

Retriever should not become the implementation home for data-tool experiments.

That keeps the boundary clean:

- collaborators can iterate independently
- Retriever can consume stable outputs
- breaking changes stay localized

## Immediate Plan

### Phase 1

- keep broad data/export experiments out of main runtime merges
- define a tiny shared type surface
- extract or rewrite a standalone read tool
- extract or rewrite a standalone mock data write tool

### Phase 2

- add focused tests for cross-tool interoperability
- validate that collaborators can use the tools without Retriever runtime knowledge
- decide whether the shared types are stable enough for wider adoption

### Phase 3

- only after repeated real usage, decide whether any part of this should move back into Retriever core

## Merge Guidance

For current Retriever development:

- keep runtime, perception, recording, and replay improvements reviewable separately
- keep `retriever.types.data` focused on collection/replay/export contracts
- avoid forcing data/export concerns into the execution core

This reduces risk and preserves room to redesign the data surface with external collaborators before locking it into Retriever.

## Success Criteria

This split is working if:

- a collaborator can generate mock artifacts without Retriever runtime setup
- a collaborator can read and inspect those artifacts with a tiny tool surface
- Retriever can import or replay those artifacts through a narrow adapter
- no core runtime code depends on a large experimental data contract package

That is the right bar for the current phase.
