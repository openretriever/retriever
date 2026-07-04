# Retriever Release Checklist

This repository is the public core runtime candidate for Retriever. The first public package release target is `retriever-core==0.0.1`.

## Required Validation

Run these before a public launch, tag, or package publish:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests -q
pixi run p0-release-readiness
pixi run -e docs docs-build
pixi run build
pixi run package-check
```

The same checks are wired in `.github/workflows/ci.yml`; the pytest gate intentionally uses `tests/`, because `pyproject.toml` collects the maintained `test_*_rt.py` runtime-facing suite across the full tree.

## GitHub Settings

Before making the repository public:

- Set the default branch to `main`.
- Keep `release/mirror-alignment-20260621` as an audit/reference branch if useful.
- Confirm the repository URL is `https://github.com/openretriever/retriever`.
- Confirm the hosted docs URL is `https://openretriever-docs.pages.dev/`.
- Build docs with `pixi run -e docs docs-build`; deploy `docs-site/dist/` through the configured Cloudflare Pages project.

## Package Publish

Before publishing to PyPI:

The PyPI project name `retriever` is already used by another project. Publish this runtime as distribution name `retriever-core`; the Python import remains `import retriever`.

- Confirm `pyproject.toml` metadata, version, license, URLs, optional extras, and distribution name `retriever-core`.
- Build locally with `pixi run build`.
- Inspect the wheel/sdist contents for generated or private files.
- Run `pixi run package-check` before publishing; `.github/workflows/publish.yml` enforces the same metadata check before upload.
- Configure PyPI/TestPyPI trusted publishers for `.github/workflows/publish.yml`, then publish manually with the workflow dispatch target.

Trusted publisher settings:

| Registry | Project | Owner | Repository | Workflow | Environment |
| --- | --- | --- | --- | --- | --- |
| TestPyPI | `retriever-core` | `openretriever` | `retriever` | `publish.yml` | `testpypi` |
| PyPI | `retriever-core` | `openretriever` | `retriever` | `publish.yml` | `pypi` |

Do not publish a package named `retriever`; that name belongs to another project.

## Companion Repositories

- Golden examples: `https://github.com/openretriever/golden-retriever`
- Project website: `https://openretriever.org/` (source: `https://github.com/openretriever/landing-site`)

Golden is the companion examples repository and applied type pack. After the real `retriever-core` distribution is published, update Golden's runtime dependency to `retriever-core` while continuing to import the runtime as `retriever`. Its robotics/planning payloads are exported through the Retriever Hub manifest (`hub.use("openretriever/golden-retriever:WorldState")` once public), so Golden should launch as a Hub-distributed pack catalog rather than a second public PyPI product.

## Launch-Order Dependencies

The public surfaces reference each other; publish in this order so no live
link or command dangles:

1. Make `openretriever/retriever` and `openretriever/golden-retriever`
   public. Every GitHub link on openretriever.org, the docs site, and the
   Golden site currently 404s for anonymous visitors.
2. Publish `retriever-core` to PyPI. `pip install retriever-core` is the
   first command on the landing page and in the docs — it must work the
   moment those pages are promoted.
3. Update Golden to consume the published `retriever-core` runtime and
   verify its Hub-loadable applied type pack (`openretriever/golden-retriever`).
   Keep any Golden wheel as an optional future artifact, not a required public
   launch step.
4. Create the public `openretriever/hub-index` repository (the Hub's
   default module index). Optional follow-up: publish the
   `openretriever/pi05-policy` hub module designed in the Golden repo
   (`examples/advanced/openpi_policy/README.md`).
5. Redeploy the docs site (includes `llms.txt` and the Standard Types /
   Concepts and Lineage pages) and the landing site, then run a link check.
6. DNS cutover for the docs domain, then update `site-links.js` in the
   landing repo from `.pages.dev` URLs to the final domain.

Agent-facing entry points (`AGENTS.md` at each repo root, `/llms.txt` on
the docs site) ship with the repos — keep them current with API changes.
