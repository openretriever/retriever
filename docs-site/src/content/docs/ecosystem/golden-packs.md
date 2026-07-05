---
title: Golden Examples
---
GoldenRetriever is the maintained reference examples layer for robot-facing examples, reusable payload packs, and Hub-pack candidates. The
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
  contract for Hub-distributed robot-facing payloads

Golden is not a second framework. It is the maintained reference examples layer for robot-facing examples and pack candidates on top of the core runtime.

## Local source proof

Run this only after `pixi run demo-webcam-detection-mock` succeeds in the core Retriever checkout. Golden is a separate source checkout; run the same pack contract there before publishing or depending on an index entry:

```bash
git clone https://github.com/openretriever/golden-retriever.git
cd golden-retriever
pixi install
pixi run demo-golden-hub-pack
pixi run demo-pipeline-html-viz
```

The first command loads Golden's local `[tool.retriever.module]` manifest through
the runtime Hub loader, checks representative exports, verifies registry
visibility, and round-trips a lightweight action payload through the exported
Arrow helpers. This mirrors the release contract for Hub-distributed robot-facing payloads: schema compatibility plus serialization behavior. The second command validates a small closed-loop pipeline to IR
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

1. Run the checkout block above from a GoldenRetriever source checkout.
2. Open the [first Golden proof](https://retriever-space.pages.dev/examples/golden-hub-proof/), then browse the [Golden example catalog](https://retriever-space.pages.dev/examples/).
3. Run the mock-safe Golden ladder: first proof, perception detection, robosuite mock, and pipeline HTML visualization.
4. Treat only manifest-declared exports as Hub-loadable today; promoted demos remain source-checkout examples until exported, versioned, smoke-tested, and indexed.

## What belongs in Golden packs

Put a payload or helper in a Golden pack when it is useful across robot examples but
not universal enough for the runtime standard library:

- world and belief state envelopes
- skill, plan, trajectory, and execution-status payloads
- Arrow conversions for robot-facing payloads
- domain examples that compose runtime standard types

Keep canonical, broadly reusable primitives in `retriever.types.*`. Golden packs
compose those types; they should not redefine them.

## Next step

Continue with [Hub packs and modules](/ecosystem/modules/) for the general reference shape,
or open the [first Golden proof](https://retriever-space.pages.dev/examples/golden-hub-proof/), or browse the [Golden example catalog](https://retriever-space.pages.dev/examples/) for the
runnable robot-facing lanes and source-checkout module catalog.
