# Release Readiness

This repository is the public core-runtime candidate for Retriever. It preserves the Retriever project history while keeping the current tree focused on the runtime, type surfaces, tutorial examples, and public documentation.

## Tree Policy

The release tree should stay close to the current core runtime implementation while applying public-release hygiene on top:

- keep `src/retriever` as the core package,
- keep runnable tutorial examples under `examples/tutorial`,
- keep public docs under `docs`,
- keep optional integrations behind documented extras,
- exclude private notes, generated reports, large datasets, external vendored research repos, robot credentials, local logs, and system-specific companion stacks.

System-level robot integrations, simulator packages, datasets, and heavier model demos should live in companion repositories. They can depend on this core package instead of being bundled into it.

## History Policy

The public repository should preserve useful Retriever history with public author identities. Cleanup commits may remove deleted legacy assets from the current tree, but they should avoid rewriting or flattening later core-runtime commits unless there is a concrete privacy, licensing, or repository-size reason.

## Verified Provenance Snapshot

As of 2026-06-21, the prepared public core repository had this verified provenance baseline. Later docs-only release notes may advance `HEAD` without changing the tree-policy conclusions below:

- provenance baseline: `d8b16666b8229f9f51f10f00ca5cb5f174cc1ec9`, pushed to `openretriever/main` and `openretriever/release/mirror-alignment-20260621` at verification time,
- preserved release history length at that baseline: 728 commits,
- first preserved commit: `f018771` from 2023-10-20, `initial commit: add readme and ignore`,
- public author identities currently present: `Linfeng Zhao <zlf0625@gmail.com>`, `Haoyan Lin <haoyan.lin@sopia.edu>`, and `Toby <tobyxdd@gmail.com>`,
- development mirror reference: commit `ac4948ad03533cf9b6ffc71f8ca38a15f88f04b2` on `merge/feature-aggregate-v1`,
- legacy history source: the original Retriever checkout, used read-only because its working tree contained local edits and deleted vendored assets during release preparation.

A bounded tracked-tree comparison against the mirror, excluding `pixi.lock`, `docs/reports/`, and `docs/temp_notes/`, showed:

- 369 tracked release files versus 1236 tracked mirror files,
- release-only files are public metadata/docs such as `.github/`, `CONTRIBUTING.md`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, `docs/release_readiness.md`, `docs/website_story.md`, and `mkdocs.yml`,
- mirror-only files are primarily excluded public-release bulk: `data/`, `external/`, the old website tree, generated distribution artifacts, and companion Golden/tutorial files,
- common content differences are docs/metadata plus the five source files listed in [Current Intentional Release Differences](#current-intentional-release-differences).

## Public Metadata

Before publishing, verify these surfaces are current:

- `pyproject.toml` package name, description, author, URLs, optional extras, and license metadata,
- `README.md` install, first commands, and documentation map,
- `mkdocs.yml` site URL, repo URL, nav, theme, and hosted docs paths,
- `LICENSE` and `THIRD_PARTY_NOTICES.md`,
- `.gitignore` exclusions for generated/local/private artifacts.
- GitHub issue and PR templates for bug reports, docs issues, feature requests, and public-release checks.

## Public Push Target

The intended public remote for this prepared core-runtime repository is:

```bash
git@github.com:openretriever/retriever.git
```

Keep the remote named `openretriever` locally when possible, and verify it before pushing:

```bash
git remote -v
```

The companion landing page should treat this repository as the runtime code surface. Link docs to `https://openretriever.github.io/retriever/` and keep larger robot examples in separate companion repositories.

## Acceptance Checks

Run these from the repository root before publishing:

```bash
python -m pytest tests/core -q
python -m mkdocs build --strict
python -m build
```

If using Pixi, prefer the packaged tasks when available:

```bash
pixi run test
pixi run p0-release-readiness
pixi run -e docs docs-build
pixi run build
```

## Current Intentional Release Differences

The public candidate should track the current core runtime tree closely. Any source-level difference from the development mirror should be small, intentional, and documented here. Current intentional deltas are:

- `src/retriever/hub/_index.py`: default Hub index points at the public `openretriever/hub-index` location.
- `src/retriever/__init__.py`: `retriever.hub` is loaded lazily so plain `import retriever` keeps optional Hub imports light.
- `src/retriever/types/__init__.py`: domain type packages are loaded lazily while preserving the public `retriever.types.<domain>` surface.
- `src/retriever/flow/__init__.py`: `Linear` and `Chunking` are exported from `retriever.flow` for public sync-adapter discoverability.
- `src/retriever/rt/backend/dora/__init__.py`: public docs avoid references to excluded private/temp design notes.

Other release-only differences should stay in metadata and docs rather than changing runtime behavior:

- public URLs point at `openretriever`,
- docs avoid private project history and local paths,
- release docs include public website/packaging guidance.
