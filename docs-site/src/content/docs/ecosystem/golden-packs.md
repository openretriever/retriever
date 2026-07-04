---
title: Golden Packs
---

# Golden Packs

GoldenRetriever is the reference catalog for Hub-distributed applied robotics packs. The
runtime stays in `retriever-core`; Golden provides maintained examples, robot
payload types, and small proof paths that show how a pack is loaded, inspected,
and composed. This path intentionally avoids a separate Golden PyPI runtime package.

Use this page when you want the concrete extension story rather than a generic
Hub template.

## Load Golden exports through Hub

The intended public Golden refs use the same string-ref API as other Hub exports:

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
  contract for Hub-distributed applied types

Golden is not a second framework. It is the maintained pack and example catalog
for the core runtime.

## Local source proof

From a GoldenRetriever source checkout, run the same pack contract locally before publishing or depending on an index entry:

```bash
pixi run demo-golden-hub-pack
pixi run demo-pipeline-html-viz
```

The first command loads Golden's local `[tool.retriever.module]` manifest through
the runtime Hub loader, checks representative exports, verifies registry
visibility, and round-trips a lightweight action payload through the exported
Arrow helpers. This mirrors the release contract for Hub-distributed applied types: schema compatibility plus serialization behavior. The second command validates a small closed-loop pipeline to IR
and writes an HTML graph artifact.

Typical output starts like this:

```text
Golden Hub exports: WorldState, BeliefGraph, Skill, Plan, Trajectory, convert_to_arrow, convert_from_arrow
Registry WorldState: _retriever_hub...WorldState
Constructed WorldState: ['cup']
Arrow round-trip: Action OK
Intended Hub reference: hub.use("openretriever/golden-retriever:WorldState")
Graph proof: run `pixi run demo-pipeline-html-viz` to validate and render an IR HTML artifact.
```

## What belongs in Golden packs

Put a type or helper in a Golden pack when it is useful across robot examples but
not universal enough for the runtime standard library:

- world and belief state envelopes
- skill, plan, trajectory, and execution-status payloads
- Arrow conversions for applied robot payloads
- domain examples that compose runtime standard types

Keep canonical, broadly reusable primitives in `retriever.types.*`. Golden packs
compose those types; they should not redefine them.

## Next step

Continue with [Hub Modules](/ecosystem/modules/) for the general reference shape,
or open the [GoldenRetriever examples site](https://retriever-space.pages.dev/) for the
runnable applied lanes.
