# Retriever Release Checklist

This repository is the public core runtime candidate for Retriever. The first public package release target is `retriever-core==0.0.1`.

## Required Validation

Run these before a public launch, tag, or package publish:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests -q
pixi run p1-reliability-gates
pixi run p0-release-readiness-full
pixi run -e docs docs-build
pixi run build
pixi run package-check
```

`.github/workflows/ci.yml` runs the same core tests, reliability gates, full P0 release-readiness smoke, docs build, and package build. Run `pixi run package-check` locally after `pixi run build` because the CI publish workflow enforces the metadata check before upload.

The pytest gate intentionally uses `tests/`, because `pyproject.toml` collects the maintained `test_*_rt.py` runtime-facing suite across the full tree.



## Built-Artifact Local Preview

Use this when reviewing exactly what the docs Pages project will receive:

```bash
/opt/homebrew/bin/pixi run -e docs docs-build
python3 -m http.server 8781 --bind 127.0.0.1 --directory docs-site/dist
```

Open `http://127.0.0.1:8781/`, `http://127.0.0.1:8781/ecosystem/`, and `http://127.0.0.1:8781/ecosystem/golden-packs/`. Ecosystem pages should describe Golden as the reference layer plus manifest-declared type pack, not as a second runtime.

## Post-Deploy Docs Content Check

After deploying core docs, verify that the live Starlight site and agent map use the current Golden terminology:

```bash
for url in \
  https://openretriever-docs.pages.dev/ecosystem/ \
  https://openretriever-docs.pages.dev/ecosystem/golden-packs/ \
  https://openretriever-docs.pages.dev/ecosystem/modules/ \
  https://openretriever-docs.pages.dev/llms.txt \
  https://openretriever-docs.pages.dev/robots.txt; do
  html=$(curl -fsSL "$url")
  printf '%s\n' "$url"
  legacy_subtitle='first applied robotics Hub'' module'
  ! printf '%s' "$html" | grep -q "$legacy_subtitle"
  legacy_module='GoldenRetriever'' module'
  ! printf '%s' "$html" | grep -q "$legacy_module"
done
curl -fsSL https://openretriever-docs.pages.dev/robots.txt | grep -q 'sitemap-index.xml'
```

Run `pixi run public-surface-check` after repository visibility and the required Pages/landing surfaces are live. Add `--custom-domains` after DNS cutover and `--package-index` after TestPyPI/PyPI publication; this content check is a narrower docs-deploy smoke.

## GitHub Settings

Before making the repository public:

- Set the default branch to `main`; verify with `pixi run public-surface-check` or `git ls-remote --symref git@github.com:openretriever/retriever.git HEAD`.
- Keep `release/mirror-alignment-20260621` as an audit/reference branch if useful.
- Confirm the repository URL is `https://github.com/openretriever/retriever`.
- Confirm the hosted docs URL is `https://openretriever-docs.pages.dev/`; after DNS cutover, also confirm `https://docs.openretriever.org/`.
- Build docs with `pixi run -e docs docs-build`; deploy `docs-site/dist/` through the configured static hosting target.

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

## Final External Surface Check

After repository visibility and the required hosted surfaces are live, run:

```bash
pixi run public-surface-check
```

After DNS cutover and package publication, run the stricter optional gates:

```bash
pixi run public-surface-check --custom-domains
pixi run public-surface-check --package-index
pixi run public-surface-check --all
```

The default network-facing check verifies repository metadata, required live website URLs, and required DNS. The optional flags add custom-domain and `retriever-core` package-index verification. Treat failures as release blockers or record them in maintainer-only launch notes before publishing.

## Companion Repositories

- Golden reference layer: `https://github.com/openretriever/golden-retriever`
- Project website: `https://openretriever.org/` (source: `https://github.com/openretriever/landing-site`)

Golden is the applied examples repository and applied type pack. After the real `retriever-core` distribution is published, update Golden's runtime dependency to `retriever-core` while continuing to import the runtime as `retriever`. Its robotics/planning payloads are exported through the Retriever Hub manifest (`hub.use("openretriever/golden-retriever:WorldState")` once public), so Golden should launch as a Hub-distributed pack catalog rather than a second public PyPI product.

## Launch-Order Dependencies

The public surfaces reference each other; publish in this order so no live
link or command dangles:

1. Make `openretriever/retriever` and `openretriever/golden-retriever`
   public. The current source-first install path depends on anonymous users
   being able to clone those repositories.
2. Keep the public preview source-first until `retriever-core==0.0.1`
   resolves from PyPI. The landing page and docs may mention the future
   `pip install retriever-core` target, but the working command path should
   remain source checkout plus Pixi until PyPI is live.
3. Update Golden to consume the published `retriever-core` runtime and
   verify its Hub-loadable applied type pack (`openretriever/golden-retriever`).
   Keep any Golden wheel as an optional future artifact, not a required public
   launch step.
4. Publish the public Retriever Hub index and any optional policy modules only after the runtime package and Golden reference layer are live. Keep those modules separate from the core runtime release.
5. Redeploy the docs site (includes `llms.txt`, Standard Types, Concepts and
   Lineage, and Hub pages) and the landing site, then run a link check.
6. DNS cutover for the docs domain, then update `site-links.js` in the
   landing repo from `.pages.dev` URLs to the final domain.

Agent-facing entry points (`AGENTS.md` at each repo root, `/llms.txt` on
the docs site) ship with the repos — keep them current with API changes.
