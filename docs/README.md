---
title: "Retriever Documentation"
---

# Retriever Documentation

> Public docs note: the hosted docs front door is built from `docs-site/`.
> This `docs/` tree is retained as source-local reference material, release maintenance notes, and deeper handbooks.


Retriever is a Python runtime for closed-loop robot systems whose perception, reasoning, and control can run together with explicit time, typed handoff, graph inspection, and replay.

These docs are organized around adoption first: run a small graph, understand Flows and time, debug the graph, then move toward backends, registries, and reusable ecosystem packages.

## Start Here

- [docs/quickstart.md](quickstart.md) — 5-minute runtime mental model and first runnable graph.
- [docs/handbook.md](handbook.md) — canonical install, authoring, running, debugging, recording, and typing guide.
- [docs/tutorials/index.md](tutorials/index.md) — runnable tutorial tracks using `pixi` tasks.

If you only read one operational page, read `docs/handbook.md`.

## Main Guides

- `docs/getting_started/install.md` — Pixi, pip/uv, dora CLI notes, and troubleshooting.
- `docs/guide_flow.md` — `@io`, `Flow`, clocks, sync policies, and `Pipeline` wiring.
- `docs/guide_runtime.md` — validation, IR, execution graph, and backend execution.
- `docs/architecture.md` — supported runtime architecture and boundary decisions.
- `docs/guides/debugging.md` — `Pipeline.step(...)`, replay, and backend debugging.

## Type And Data References

- `docs/guides/flow_typing_standard.md`
- `docs/guides/data_eventstream_v1.md`
- `docs/guides/spatial_types_v1.md`
- `docs/guides/perception_types_v1.md`
- `docs/guides/language_types_v1.md`
- `docs/guides/symbolic_types_v1.md`
- `docs/guides/type_composition_v1.md`

## Ecosystem And Release References

- `docs/hub.md` — reusable module loading and publishing patterns.
- `docs/contributing.md` — development workflow and QA.
- `docs/API.md` — API reference.
- `THIRD_PARTY_NOTICES.md` — bundled third-party JavaScript notices.

Keep public docs concise, repo-relative, and free of private project paths or staging-branch language.
