# Flow Typing Standard for Retriever Hub (v2)

## Purpose

Define the public typing contract for flows shared through Retriever Hub so that
composition behaves consistently across stepper, multiprocessing, and dora.

## Supported Signature Forms

All of these are valid in v2:

- `Flow[(A, B), C]`
- `Flow[tuple[A, B], C]`
- `Flow[A, (C, D)]`
- `Flow[(A, B), (C, D)]`

`(A, B)` and `tuple[A, B]` are equivalent after normalization.

## Core Rules

1. Generic element types must be Flow IO compatible (`@io` / `@flow_io`) when defined locally.
2. Composite tuple generics cannot mix `None` with concrete types (for example `(A, None)` is invalid).
3. Unqualified field access is allowed only when unique across a composite view.
4. Ambiguous unqualified read/write/has must raise `FLOW_AMBIGUOUS_FIELD`.
5. Qualified access is always valid for collisions:
   - `inp.A.arg1`
   - `inp._set_signal("B.arg1", v)`

## Collision and Aliasing

When class names collide in a composite signature, aliases are deterministic by declaration order:

- `Name__1`
- `Name__2`

Qualified routing and ports use these aliases.

## Lifecycle Contract

Runtime initialization order is:

1. instantiate from IR init config
2. call `__lazy_init__()` if present
3. call `init()`

This applies across stepper, multiprocessing, and dora execution paths.

## Validator Policy

Default validator mode:

- allows tuple-literal and tuple-output signatures
- enforces local IO compatibility and tuple/None constraints

Strict mode (`--strict-single-io`):

- rejects composite tuple input/output signatures
- enforces single-envelope contracts for teams that require them

## Versioning

Typing contract version: `hub.flow-typing.v2`.
