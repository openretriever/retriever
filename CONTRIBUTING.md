# Contributing

Retriever is the core runtime repository. Keep changes focused on typed flows, clocks, sync policies, IR, runtime backends, docs, and public tutorial examples.

## Setup

```bash
pixi install
pixi run python -m pytest tests -q
pixi run -e docs docs-build
```

Install development extras before running lint/type tooling:

```bash
pixi run python -m pip install -e '.[dev]'
pixi run ruff check .
pixi run black .
pixi run mypy src/retriever
```

## Pull Requests

Include:

- what changed and why;
- exact commands run;
- docs updates when public APIs, tasks, or setup changes;
- any compatibility notes for examples, backends, or Hub behavior.

Keep robot-specific integrations, heavyweight model stacks, datasets, and system demos in companion repositories unless the code is runtime-generic.
