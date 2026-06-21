# Retriever Release Checklist

This repository is the public core runtime candidate for Retriever.

## Required Validation

Run these before a public launch, tag, or package publish:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/core -q
pixi run p0-release-readiness
pixi run -e docs docs-build
pixi run build
```

The same checks are wired in `.github/workflows/ci.yml`.

## GitHub Settings

Before making the repository public:

- Set the default branch to `main`.
- Keep `release/mirror-alignment-20260621` as an audit/reference branch if useful.
- Enable GitHub Pages with source `GitHub Actions` so `.github/workflows/docs.yml` can deploy `site/`.
- Confirm the repository URL is `https://github.com/openretriever/retriever`.

## Package Publish

Before publishing to PyPI:

- Confirm `pyproject.toml` metadata, version, license, URLs, and optional extras.
- Build locally with `pixi run build`.
- Inspect the wheel/sdist contents for generated or private files.
- Prefer PyPI trusted publishing from GitHub Actions once the public release workflow is added.

## Companion Repositories

- Golden examples: `https://github.com/openretriever/golden-retriever`
- Project website: `https://github.com/linfeng-z/retriever-project-website-astro`

Golden currently depends on the temporary `debug-retriever` package. After the real `retriever` package is published, update Golden to depend on the public runtime package.
