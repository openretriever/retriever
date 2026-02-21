---
title: "Notebook-Ready Tutorial Export"
---

# Notebook-Ready Tutorial Export

This workflow converts tutorial markdown pages under `docs/tutorials/` into notebook-ready artifacts.

Outputs are written to `out/jupyter-notebook/`:

- `index.json` with per-page conversion summary
- `manifests/*.cells.json` containing explicit markdown/python/shell cell sequences
- `notebooks/*.ipynb` scaffold notebooks for immediate rendering

## Why This Exists

- Keep tutorial source-of-truth in markdown docs.
- Support future publication as Jupyter-based tutorial websites.
- Preserve runnable command snippets as explicit shell notebook cells.

## Commands

Export full notebook-ready bundle:

```bash
pixi run export-notebook-ready
```

Check conversion integrity without writing outputs:

```bash
pixi run check-notebook-ready
```

Inspect one generated notebook:

```bash
python -m json.tool out/jupyter-notebook/notebooks/tutorial_integrated_debug_to_release.ipynb > /dev/null
```

## Conversion Rules

- Regular markdown stays markdown cells.
- Fenced `python`/`py` blocks become code cells.
- Fenced `bash`/`sh`/`zsh`/`shell` blocks become `%%bash` code cells.
- Unknown fenced languages are preserved as markdown blocks.

## Typical Use In Content Iteration

1. Update tutorial docs (`docs/tutorials/*.md`).
2. Run `pixi run export-notebook-ready`.
3. Spot-check generated notebook(s).
4. Use `out/jupyter-notebook/` as input for downstream publishing pipelines.
