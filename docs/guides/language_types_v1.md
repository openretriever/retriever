# Language Types v1

`retriever.types.language` is the canonical package for primitive text,
grounding, and plan-text payloads.

Use it for:
- short scene/object captions,
- prompts and referring expressions,
- grounded phrases tied to a resolved referent label,
- lightweight plan text made of ordered primitive steps.

Keep model-specific request/response packets and larger planner bundles out of
core. Those belong in Hub or domain packages first.

## Canonical imports

```python
from retriever.types.language import (
    Caption,
    GroundedPhrase,
    PlanStepText,
    PlanText,
    Prompt,
    ReferringExpression,
    TextSpan,
)
```

Pinned import when you want an explicit version boundary:

```python
from retriever.types.language.v1 import Caption
```

## Primitive set

- `TextSpan`: half-open character span
- `Caption`: short descriptive text with optional confidence/source
- `Prompt`: user-authored or system-authored prompt text kept at the primitive text layer, not a full model transport packet
- `ReferringExpression`: natural-language reference to an entity
- `GroundedPhrase`: resolved language phrase with optional referent label and frame index
- `PlanStepText`: one primitive language plan step
- `PlanText`: ordered tuple of `PlanStepText`

## Relationship to other type families

- `retriever.types`: shared schema/stream identity primitives
- `retriever.types.spatial`: geometry and stamped robotics payloads
- `retriever.types.perception`: images, detections, masks, point clouds, and encoded video
- `retriever.types.data`: event/stream/dataset contracts
- `retriever.types.symbolic`: object-centric planning structures

Use `retriever.types.language` for primitive text and grounding outputs. Use
`retriever.types.symbolic` for logical planning/state. Do not merge them into a
single broad `semantic` bucket.

## Composite Flow IO rule

Prefer shared primitives plus structural composition:

```python
from retriever.flow import Flow
from retriever.types.language import GroundedPhrase, ReferringExpression
from retriever.types.perception import DetectionBatch

class GroundRefFlow(Flow[(ReferringExpression, DetectionBatch), GroundedPhrase]):
    def step(self, inp):
        ...
```

Likewise for plan text:

```python
from retriever.flow import Flow
from retriever.types.language import Caption, PlanText

class CaptionPlanFlow(Flow[Caption, PlanText]):
    def step(self, caption: Caption) -> PlanText:
        ...
```

Use a named `@io` envelope only when the grouped boundary itself is a stable,
reused contract.

## What stays out of core

Keep these out of `retriever.types.language` for now:
- model-specific VLM request/response payloads,
- dialogue/runtime metadata packets,
- chain-of-thought-like intermediate traces,
- larger domain plans such as TAMP or task-specific planner bundles.

Those belong in Hub or domain packages first.


## Transformation rules

Treat `retriever.types.language` as a primitive text/grounding layer. Common
transformations should be expressed explicitly in flows or adapters:

- `ReferringExpression + DetectionBatch -> GroundedPhrase`
- `Caption -> PlanStepText` or `PlanText`
- `Prompt -> model-specific request packet` is a Hub/domain adapter boundary, not a core type
- `GroundedPhrase -> symbolic or task-specific objects` is also an adapter boundary

Keep chain-of-thought traces, dialogue state, and full planner/model bundles out
of core.

## Runnable examples

Mirror tests cover the canonical surface directly:

```bash
pixi run pytest -q tests/core/test_language_type_surface_rt.py
```

At the core-repo level, this surface is currently grounded by the canonical language type tests and the composition examples in this guide.
