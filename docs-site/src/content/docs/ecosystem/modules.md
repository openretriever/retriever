---
title: Hub Packs and Modules
---
A Hub module is a normal Python package that adds one thing: a `[tool.retriever.module]` manifest in its `pyproject.toml` declaring an export table. Consumers load a named export straight from the module's git repository — no PyPI wheel, no private source paths, no in-repo layout to reverse-engineer.

```python
from retriever import hub
from retriever.flow import Rate

LidarSlam = hub.use("your-org/lidar-slam:LidarSlamFlow")
slam = LidarSlam(resolution=0.05) @ Rate(hz=10)
```

`hub.use("org/name:Export")` returns the exported object itself — a Flow class here, but it can be any declared attribute: a type, a transform, a pipeline builder, a small utility.

## Reference format

```text
{org}/{name}[:{attribute}][@{version}]
```

```python
proxy         = hub.use("your-org/lidar-slam")                 # whole module
LidarSlamFlow = hub.use("your-org/lidar-slam:LidarSlamFlow")   # one export
pinned        = hub.use("your-org/lidar-slam:LidarSlamFlow@0.1.0")  # pinned tag
```

## What `hub.use` does

Given a ref, the loader:

1. Parses `{org}/{name}[:attribute][@version]`.
2. Looks up `{org}/{name}` in the Hub index to get the module's GitHub repo URL.
3. Resolves the version to a commit — the newest semver tag, or the tag matching `@version`.
4. Downloads that commit's tarball and caches it at `~/.retriever/hub/cache/{org}/{name}/{sha}`. A cached commit is reused; `hub.use(ref, refresh=True)` forces a re-fetch.
5. Reads `[tool.retriever.module]` from the repo's `pyproject.toml`, then enforces `min_retriever_version` and the project's declared dependencies against your environment.
6. Imports the declared package under a private, commit-scoped namespace — without touching `sys.path` — and returns the requested export.

Two environment variables tune this: `RETRIEVER_HUB_INDEX_URL` points at a different index, and `RETRIEVER_HUB_TOKEN` is sent as a bearer token so private repos resolve.

## Return contract

- `hub.use("org/name:Export")` returns the actual class, function, type, or value — not a wrapper.
- `hub.use("org/name")` returns a `ModuleProxy` over the declared export table. Attribute access reads the table, `dir(proxy)` lists the exports, and its repr names them:

```python
mod = hub.use("your-org/lidar-slam")
mod            # <HubModule 'your-org/lidar-slam' exports=['LidarSlamFlow', 'SE3Pose', ...]>
mod.LidarSlamFlow(resolution=0.05) @ Rate(hz=10)
```

A proxy exposes only declared exports. Reaching for an undeclared name raises `AttributeError` listing what is available, so the manifest — not the file tree — is the public surface.

## Version isolation

Each commit loads into its own namespace, so `@0.9.0` and `@1.0.0` of the same module coexist in one process without aliasing each other. Pin a ref per app when the schema matters.

> **IR boundary:** a serialized IR from hub-loaded code is not self-contained across machines. The target machine must already have the matching hub cache, or load the module through `hub.use(...)` first, before it can reconstruct those nodes from IR.

## Applied reference: GoldenRetriever

GoldenRetriever is the maintained example of a real Hub type pack. Its manifest exports robot-facing payloads through the same ref shape:

```python
from retriever import hub

WorldState = hub.use("openretriever/golden-retriever:WorldState")
```

Until the public index and repo are live, that networked call returns `HUB_MODULE_NOT_FOUND`. See [Golden Examples](/ecosystem/golden-packs/) for the source-checkout proof that loads the identical manifest through the real loader today, and [Publishing](/ecosystem/publishing/) to make your own repo hub-loadable.
