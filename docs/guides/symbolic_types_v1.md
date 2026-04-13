# Symbolic Types v1

`retriever.types.symbolic` is the canonical package for compact object-centric
planning primitives.

Use it for:
- object and variable identity,
- predicates and atoms,
- symbolic state snapshots,
- task/action/option primitives,
- skill signatures that sit at the symbolic boundary.

Keep perception/media payloads, replay/export contracts, and model-specific
planner packets out of this family.

## Canonical imports

```python
from retriever.types.symbolic import (
    Action,
    GroundAtom,
    GroundedSkill,
    Object,
    ObjectType,
    Option,
    ParameterizedOption,
    Predicate,
    SkillSignature,
    State,
    Task,
    Variable,
)
```

## Package split

- `objects`
  - `ObjectType`, `Object`, `Variable`, `State`, `Predicate`, `LiftedAtom`, `GroundAtom`
- `options`
  - `Action`, `Option`, `ParameterizedOption`, `Task`
- `skills`
  - `SkillSignature`, `GroundedSkill`

## Boundary rule

Use `retriever.types.symbolic` for reusable logical/planning structure. Use
`retriever.types.language` for primitive text and grounded phrases, and convert
between the two through explicit adapters.

Examples:
- `GroundedPhrase -> GroundAtom` is an adapter boundary
- `PlanText -> Task` is a planner/domain adapter boundary
- full TAMP domain operators and workflow bundles should stay in Hub or domain
  packages first

## Composite Flow IO rule

Symbolic primitives should compose directly with other canonical families:

```python
from retriever.flow import Flow
from retriever.types.language import GroundedPhrase
from retriever.types.symbolic import GroundAtom

class GroundPhraseToAtom(Flow[GroundedPhrase, GroundAtom]):
    def step(self, phrase: GroundedPhrase) -> GroundAtom:
        ...
```

Use named `@io` envelopes only when the grouped boundary is itself a durable
public contract.
