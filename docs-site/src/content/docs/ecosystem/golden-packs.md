---
title: GoldenRetriever Examples
---
GoldenRetriever is the reference for a real Hub type pack. It is not a second runtime — the runtime is `retriever-core`, imported as `retriever`. GoldenRetriever is a maintained example repo whose `pyproject.toml` carries a `[tool.retriever.module]` manifest, so its robot-facing payloads load through the same `hub.use(...)` path as any other module.

## Load GoldenRetriever exports through Hub

```python
from retriever import hub

WorldState = hub.use("openretriever/golden-retriever:WorldState")
Plan       = hub.use("openretriever/golden-retriever:Plan")
convert_to_arrow = hub.use("openretriever/golden-retriever:convert_to_arrow")
```

The module name is `retriever_typing`; its manifest exports the applied types and their Arrow conversions:

```text
WorldState  RobotState  BeliefGraph  Skill  Plan  StructuredPlan
TaskGoal    Trajectory  ExecutionStatus  Action  Command  Status
convert_to_arrow  convert_from_arrow
```

Until the public index and repo are live, that networked call returns `HUB_MODULE_NOT_FOUND`. The proof below loads the identical manifest through the real loader today.

## Local source proof

From a GoldenRetriever source checkout, run the pack smoke:

```bash
pixi run demo-golden-hub-pack
```

```text
GoldenRetriever pack exports: WorldState, BeliefGraph, Skill, Plan, Trajectory, convert_to_arrow, convert_from_arrow
Registry WorldState: _retriever_hub.golden_hub_pack_smoke__retriever_typing.robotics_types.WorldState
Constructed WorldState: ['cup']
Constructed Plan skills: ['pick']
Arrow round-trip: Action OK
Hub reference: hub.use("openretriever/golden-retriever:WorldState")
Graph proof: run `pixi run demo-pipeline-html-viz` to validate and render an IR HTML artifact.
```

The smoke reads the repo's own `[tool.retriever.module]` manifest and loads it through `retriever.hub`'s loader — the same code path a networked `hub.use` runs after the download step. The namespaced `Registry WorldState` line is the commit-scoped import namespace the loader assigns; `Arrow round-trip: Action OK` confirms an `Action` payload survives `convert_to_arrow` → `convert_from_arrow` unchanged.

That round-trip is the point: the cross-version contract for a GoldenRetriever payload is its **registered schema and serialization behavior**, not Python class identity. Pin one ref per app and rely on the schema, not the class object.

## What belongs in a GoldenRetriever pack

Put a payload or helper here when it is useful across robot examples but not universal enough for the runtime standard library:

- world and belief state envelopes
- skill, plan, trajectory, and execution-status payloads
- Arrow conversions for robot-facing payloads
- domain examples that compose runtime standard types

Canonical, broadly reusable primitives stay in `retriever.types.*`. GoldenRetriever packs compose those types; they never redefine them.

## Next step

- Run `pixi run demo-golden-hub-pack` from a GoldenRetriever checkout to reproduce the output above.
- Open the [GoldenRetriever Hub quickstart](https://golden.retriever.build/examples/golden-hub-proof/), then the [GoldenRetriever example catalog](https://golden.retriever.build/examples/).
- Read [Hub packs and modules](/ecosystem/modules/) for the general ref shape and [Publishing](/ecosystem/publishing/) to expose your own pack this way.

Only manifest-declared exports are Hub-loadable. Promoted demos stay source-checkout examples until they are exported, versioned, smoke-tested, and indexed.
