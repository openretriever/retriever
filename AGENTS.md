# AGENTS.md — Retriever runtime, for coding agents

This file is the entry point for AI coding agents (and humans who read like
them). It states exact commands, the minimal correct API, and the pitfalls
that cost the most time. Everything here is verified against this repo; if
you find drift, fix the drift, not the reader.

## What this repo is

`retriever-core` (import name: `retriever`) is a typed dataflow runtime for
closed-loop robot systems. You author a graph of typed **Flows** connected by
timestamped ports, attach **clocks** (`Rate`, `Trigger`, ...), choose a
**sync policy** per edge (`Latest()`, `Hold()`, `Window()`, `Events()`),
then either single-step it deterministically in-process (`pipe.step()`) or
run it on a backend (`multiprocessing`, `dora`, `in-process`).

- Python: **3.11+** (syntax uses `X | None`; 3.9/3.10 will fail at import).
- License: Apache-2.0. Docs: <https://openretriever-docs.pages.dev/>.

## Documentation goals (keep these when editing anything)

1. A newcomer gets one run working before reading any theory.
2. Key concepts (Flow, clock, sync policy, step vs run) stay explainable in
   under a minute each.
3. **AI agents are first-class readers.** Prefer exact commands over prose,
   complete runnable snippets over fragments, stated expected output over
   implication, and stable file paths over "see above".
4. Concepts link to their lineage (FRP, synchronous dataflow) with real
   references: `docs/concepts_lineage.md`.

## Commands (verified)

```bash
# Environment + any task, from repo root (installs on first use):
pixi run test                       # pytest; collects tests/**/test_*_rt.py
pixi run demo-basic-flow            # smallest runnable pipeline
pixi run demo-webcam-detection      # visual quickstart (webcam; mock mode documented in docs)
pixi run -e docs docs-build         # build the Starlight docs site
pixi run build                      # build the wheel

# Plain venv alternative:
python -m pip install -e . && python -m pytest tests -q
```

If `dora` reports stale coordinator/schema errors: `pkill -9 dora` and rerun.

## Final launch check

For release maintainers, after GitHub default branch, custom DNS, and PyPI/TestPyPI are live:

```bash
pixi run public-surface-check
```

This is intentionally external and is expected to fail before launch cutover is complete.

## Minimal correct usage (runs as-is)

```python
from dataclasses import dataclass
from retriever.flow import Flow, Pipeline, Rate, Latest, io

@io
@dataclass
class V:
    value: int

class Src(Flow[None, V]):
    def step(self, _):            # override step(), NOT run()
        return V(value=1)

class Add(Flow[V, V]):
    def step(self, i: V) -> V:
        return V(value=(i.value or 0) + 1)

pipe = Pipeline("demo")
src = Src() @ Rate(hz=20)          # clock attaches with @
add = Add() @ Rate(hz=20)
pipe.connect(src, add, sync=Latest())   # sync= is MANDATORY on every edge

res = pipe.step(dt=0.1)            # deterministic in-process debugging
pipe.close_stepper()
pipe.run(backend="multiprocessing", duration=1.0, blocking=True)
```

## Pitfalls that actually bite

- `connect(..., sync=...)` is required unless a global default is set via
  `retriever.init(default_sync=Latest())`. Omitting it raises `FlowError`.
- Override `Flow.step()`. `run()` on a Flow subclass is deprecated (it still
  works, with a `DeprecationWarning`).
- The IO decorator is `@io` (exported from `retriever.flow`). `@flow_io`
  does not exist in this repo.
- `Tick(hz=...)` behaves exactly like `Rate(hz=...)`; it exists to signal an
  input-less source.
- Self-connections (`pipe.connect(a, a, ...)`) are rejected; keep state in
  instance attributes or route feedback through another node (`a >> b >> a`,
  which is supported).
- `on_lag` canonical values: `warn` (default), `drop`, `error`, `catch_up`
  (aliases panic/raise/strict → error).
- `pipe.run(record=...)` switches to the in-process backend for
  deterministic recording. Replay with `pipe.replay(node, path=...)`.
- The multiprocessing backend uses its own `fork` context
  (`src/retriever/rt/backend/multiprocessing/mp_context.py`); it does not
  touch, and is not affected by, the host's global start method.

## Where things live

| Area | Path |
| --- | --- |
| Authoring (Flow, Pipeline, clocks, adapters, io) | `src/retriever/flow/` |
| Validation + IR | `src/retriever/ir/` |
| Execution, backends, stepper | `src/retriever/rt/` |
| Recording / replay | `src/retriever/recording.py` |
| Hub (load Flows from git repos) | `src/retriever/hub/`, docs in `docs/ecosystem/publishing.md` |
| Error codes (all `FlowError`/`IRError`/`HubError` codes) | `src/retriever/error.py` |
| Runtime tests (the ones CI runs) | `tests/**/test_*_rt.py` |
| Canonical examples | `examples/tutorial/` |
| Deployed public docs (Starlight, source of truth) | `docs-site/` → openretriever-docs.pages.dev |
| MkDocs content, maintained in parallel during the Starlight migration | `docs/` |

## Editing rules for this repo

- Tests live next to the behavior they pin: add `test_*_rt.py` under
  `tests/core/` or the change will not be collected.
- The deployed public docs are Starlight under `docs-site/`; edit there first.
  If a concept is also covered by the parallel MkDocs content in `docs/`,
  update both so they do not drift during the migration.
- No prints in library code; use module loggers.
- Module import must stay side-effect-free (no global state mutation, no
  device/GPU/socket access at import time).
