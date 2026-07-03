---
title: "Track G: Operations and Interfaces"
---

# Track G: Operations and Interfaces

Focus: registries, reusable pipelines, typed boundaries, and operational control surfaces.

<div class="rt-learning-panel">
  <h2>Recommended Path</h2>
  <p>Start with typed boundaries and direct composition. Registry and wrapper surfaces are useful once the primitive graph model is familiar.</p>
</div>

<div class="rt-command-grid">
  <div class="rt-command-card"><span>01</span><strong>Spatial boundaries</strong><small>Carry frame, time, and source metadata through typed payloads.</small><code>pixi run demo-spatial-boundaries</code></div>
  <div class="rt-command-card"><span>02</span><strong>Language grounding</strong><small>Compose text-triggered grounding with the latest scene snapshot.</small><code>pixi run demo-language-grounding</code></div>
  <div class="rt-command-card"><span>03</span><strong>Composable pipelines</strong><small>Wrap one registered pipeline as a reusable Flow.</small><code>pixi run demo-composable-pipelines</code></div>
  <div class="rt-command-card"><span>04</span><strong>Render composition</strong><small>Generate a local HTML view of the composed pipeline.</small><code>pixi run docs-tutorial-composable-html</code></div>
</div>

??? note "More operational modules"
    | Goal | Command |
    | --- | --- |
    | Registry basics | `pixi run demo-registry-basics` |
    | Registry ecosystem | `pixi run demo-registry-ecosystem` |
    | Peripheral interface | `pixi run demo-peripheral` |

    `03_unified_wrapper` is intentionally not in the default Pixi tutorial surface. It needs `gymnasium` and `torch` in your own environment.

## What To Observe

- Registries expose reusable runtime surfaces without changing the Flow model.
- Composed pipelines can still be inspected and extended as live graphs.
- Typed boundaries keep frame/time/source metadata explicit across perception, language, and control.
