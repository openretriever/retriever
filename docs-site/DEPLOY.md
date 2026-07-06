# Deploying these docs

The docs site is deployed by **Cloudflare Pages' Git integration** — Cloudflare
watches this repository and builds/deploys on every push. There is **no deploy
token or secret stored in this repo**; the connection is held on Cloudflare's
side, so contributors (including public PRs) can never leak it.

## One-time setup (Cloudflare dashboard)

Workers & Pages → **Create application** → **Pages** → **Connect to Git** →
select `openretriever/retriever`, then set:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Root directory (advanced) | `docs-site` |
| Build command | `npm ci && npm run build` |
| Build output directory | `dist` |
| Node version | pinned by [`.node-version`](.node-version) (20) |

Pushes to `main` publish production; every other branch and pull request gets an
automatic **preview deployment** with its own URL — no secret required.

## What GitHub Actions still does

[`.github/workflows/docs.yml`](../.github/workflows/docs.yml) only **builds** the
site on push/PR as a breakage check. It does not deploy and needs no secret.

## Manual deploy (fallback)

From a machine with a Cloudflare API token in the environment:

```bash
npm ci && npm run build
npx wrangler pages deploy dist --project-name=<pages-project> --branch=<branch>
```
