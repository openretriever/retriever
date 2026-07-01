---
title: "Cloudflare Pages Deployment"
---

# Cloudflare Pages Deployment

Use Cloudflare Pages when the docs or landing page should deploy automatically from GitHub and bind to a custom domain such as `docs.retriever.systems`.

## Recommended Domains

- `retriever.systems`: product / landing page.
- `paper.retriever.systems`: paper or research page if the apex becomes the product page.
- `docs.retriever.systems`: core runtime docs from this repository.
- `golden.retriever.systems`: GoldenRetriever companion examples/docs.

## Recommended Path For Core Docs

Use **GitHub Actions -> Cloudflare Pages Direct Upload** for the core docs.

Reason: this repo builds docs through Pixi, and GitHub Actions can pin the Pixi version exactly. That avoids relying on Cloudflare's build image having the right Pixi version for `pixi.lock`.

Cloudflare setup:

1. Create a Cloudflare Pages project, for example `retriever-docs`.
2. Add the custom domain `docs.retriever.systems` to that Pages project.
3. Add the DNS record in Cloudflare:

```text
Type: CNAME
Name: docs
Target: <cloudflare-pages-project>.pages.dev
Proxy: enabled
```

GitHub repo secrets needed for direct upload:

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

Workflow shape:

```yaml
name: Cloudflare Docs

on:
  push:
    branches: [main]
    paths:
      - docs/**
      - mkdocs.yml
      - pixi.toml
      - pixi.lock
      - .github/workflows/cloudflare-docs.yml
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.9.6
        with:
          pixi-version: v0.70.1
          cache: true
      - run: pixi run -e docs docs-build
      - run: npx wrangler pages deploy site --project-name retriever-docs --branch main
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
```

Keep the current GitHub Pages workflow as a fallback until Cloudflare is confirmed as the canonical docs host.

## Alternative: Cloudflare Pages Git Integration

Cloudflare Pages can also connect directly to GitHub and deploy on each push. Use this for the Astro landing or paper site, where the build is already standard Node/Astro.

For the current Astro site, use:

```text
Framework preset: Astro
Build command: npm run build
Build output directory: dist
Production branch: main
Custom domain: retriever.systems or paper.retriever.systems
```

If you use direct Cloudflare Git integration for the core docs anyway, set the build command to install Pixi first:

```bash
curl -fsSL https://pixi.sh/install.sh | bash && ~/.pixi/bin/pixi run -e docs docs-build
```

Build output directory:

```text
site
```

## Notes

- Keep docs and website deployments separate so docs changes do not block the landing page.
- Use Cloudflare preview deployments for pull requests and non-main branches.
- Cloudflare Pages Git integration deploys automatically on pushes to the configured branch.
- Direct-upload GitHub Actions deploys automatically too, but only after the Cloudflare secrets are configured.
