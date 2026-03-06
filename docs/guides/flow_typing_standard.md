# Flow Typing Contract for Retriever

## Purpose

This page defines the current flow typing contract for Retriever runtime code,
plugins, and shared examples.

Use this page for:
- `Flow[...]` signature forms,
- composite input/output routing semantics,
- lifecycle ordering across stepper, multiprocessing, and dora.

Related guides:
- `docs/guides/robotics_typing.md`
- `docs/guides/data_spec_eventstream.md`
- `docs/guides/robotics_typing_carryback_status.md`

## Supported Signature Forms

All of these are valid:

- `Flow[(A, B), C]`
- `Flow[tuple[A, B], C]`
- `Flow[A, (C, D)]`
- `Flow[(A, B), (C, D)]`

`(A, B)` and `tuple[A, B]` are normalized to the same internal contract.

## Core Rules

1. Generic element types must be flow-I/O compatible.
2. Composite tuple generics cannot mix `None` with concrete types.
3. Unqualified field access is allowed only when unique across a composite view.
4. Ambiguous unqualified read, write, and `has` access must raise.
5. Qualified access is always valid for collisions.

Examples:
- `inp.value`
- `inp.A.value`
- `inp._get_signal("B.value")`
- `inp._set_signal("A.value", v)`

## Collision and Aliasing

When class names collide in a composite signature, aliases are deterministic by declaration order:

- `Name__1`
- `Name__2`

Qualified routing and published ports use these aliases.

## Lifecycle Contract

Runtime initialization order is:

1. instantiate from IR init config
2. call `__lazy_init__()` if present
3. call `init()`

This applies across:
- in-process stepper,
- multiprocessing backend,
- dora backend.

## Validator Policy

Default validator mode:
- allows tuple-literal and tuple-output signatures,
- enforces local I/O compatibility and tuple/`None` constraints.

Strict mode (`--strict-single-io`):
- rejects composite tuple input/output signatures,
- enforces single-envelope contracts for teams that require them.

## Adjacent Layers

The flow typing contract is not the same thing as the domain typing layers:

- `retriever.robotics_typing`
  - robotics boundary dataclasses and validation helpers
- `retriever.data_spec`
  - event/data/export contracts for collection, replay, and dataset manifests

Use the flow typing contract to describe how flows compose.
Use robotics typing and data spec to describe what the payloads mean.
