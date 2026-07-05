---
title: Golden Examples
---

# Golden Examples

GoldenRetriever is the maintained reference examples layer for robot-facing examples, reusable type packs, and Hub-pack candidates. The
runtime stays in `retriever-core`; Golden provides maintained examples, robot
payload types, simulator/visualization lanes, and small proof paths that show how a pack is loaded, inspected,
and composed. This path intentionally avoids a separate Golden PyPI runtime package.

Use this page when you want the concrete extension story rather than a generic
Hub template.

## Load Golden exports through Hub

Golden refs use the same string-ref API as other Hub exports:

```python
from retriever import hub

WorldState = hub.use("openretriever/golden-retriever:WorldState")
Plan = hub.use("openretriever/golden-retriever:Plan")
convert_to_arrow = hub.use("openretriever/golden-retriever:convert_to_arrow")
```

The important boundary is boring on purpose:

- install the runtime once with `retriever-core`
- import the runtime as `retriever`
- load reusable Golden payloads through Hub
- keep heavy demos, notebooks, robot stacks, and generated artifacts in the
  Golden source checkout
- treat the registered schema and serialization round-trip as the cross-version
  contract for Hub-distributed robot-facing types

Golden is not a second framework. It is the maintained reference examples layer for robot-facing examples and pack candidates on top of the core runtime.

## Local source proof

From a GoldenRetriever source checkout, run the same pack contract locally before publishing or depending on an index entry:

```bash
pixi run demo-golden-hub-pack
pixi run demo-pipeline-html-viz
```

The first command loads Golden's local `[tool.retriever.module]` manifest through
the runtime Hub loader, checks representative exports, verifies registry
visibility, and round-trips a lightweight action payload through the exported
Arrow helpers. This mirrors the release contract for Hub-distributed robot-facing types: schema compatibility plus serialization behavior. The second command validates a small closed-loop pipeline to IR
and writes an HTML graph artifact.

Typical output starts like this:

```text
Golden pack exports: WorldState, BeliefGraph, Skill, Plan, Trajectory, convert_to_arrow, convert_from_arrow
Registry WorldState: _retriever_hub...WorldState
Constructed WorldState: ['cup']
Arrow round-trip: Action OK
Retriever Hub reference: hub.use("openretriever/golden-retriever:WorldState")
Graph proof: run `pixi run demo-pipeline-html-viz` to validate and render an IR HTML artifact.
```


## After this page

Use this page as the bridge from runtime mechanics into the Golden examples path:

1. Run `pixi run demo-golden-hub-pack` from a GoldenRetriever source checkout.
2. Open the [Golden example catalog](https://retriever-space.pages.dev/examples/).
3. Run the mock-safe Golden ladder: Hub proof, perception detection, robosuite mock, and pipeline HTML visualization.
4. Treat only `pyproject.toml` manifest exports as Hub-loadable today; promoted demos remain source-checkout examples until exported, versioned, smoke-tested, and indexed.

## What belongs in Golden packs

Put a type or helper in a Golden pack when it is useful across robot examples but
not universal enough for the runtime standard library:

- world and belief state envelopes
- skill, plan, trajectory, and execution-status payloads
- Arrow conversions for robot-facing payloads
- domain examples that compose runtime standard types

Keep canonical, broadly reusable primitives in `retriever.types.*`. Golden packs
compose those types; they should not redefine them.

## Next step

Continue with [Hub packs and modules](/ecosystem/modules/) for the general reference shape,
or open the [Golden example catalog](https://retriever-space.pages.dev/examples/) for the
runnable robot-facing lanes and source-checkout module catalog.
