# Design notes — Retriever (core) docs site

Look-and-feel reference for this Starlight site. Read before changing
`src/styles/retriever.css` or a page's visual structure.

## Identity: keep it clean and light

The core runtime docs stay on a **clean, light (white/near-white) ground** — a
precise, technical reference feel. This is **deliberately distinct** from the
GoldenRetriever site, which uses a warmer "golden paper" tone. Two surfaces,
two moods that still feel related through shared type and the orange accent:

- **Core = white, precise, reference.**
- **Golden = warm, applied, exploratory.**

Do **not** copy Golden's cream background here.

## What we borrow (principles, not colors)

We admire **Claude/Anthropic** (calm, editorial restraint) and **Pixi**
(concise, command-first, honest positioning) — borrow their *discipline*, not
their palettes:

1. **Restraint.** One accent (Retriever orange). Calm shadows. Hierarchy and
   spacing over effects.
2. **Command-first, concise (Pixi).** Lead with the runnable command + expected
   output; pointed benefit phrases over paragraphs.
3. **Honest positioning (Pixi).** Compare fairly — see `/concepts/why-retriever/`.
4. **Technical-editorial type.** Monospace for eyebrows/labels and table
   headers; clean sans for prose.
5. **Keep** expected-output blocks and the agent-first layer (`llms.txt`,
   `AGENTS.md`).

> Also align with the operator's previously-referenced docs — **confirm which
> before a palette change.** When in doubt, keep the current light palette.

## Conventions (color-agnostic)

- **Eyebrow:** monospace, uppercase, wide tracking, subtle accent rule.
- **Cards:** light surfaces on the white ground; gentle hover (accent border +
  small lift). Keep shadows soft.
- **Tables:** monospace headers, comfortable padding, quiet row-hover; spotlight
  the Retriever column in comparison matrices.
- **CTAs:** one primary accent, the rest ghost.

## Guardrails

Keep the light ground. No second accent hue, no webfonts (CSP/perf), no heavy
effects. Prose measure ~60–68ch. `retriever.css` is the only home for
site-wide visual tokens.

Companion: GoldenRetriever's `docs-site/DESIGN.md` documents the *warm* variant.
Shared language, different grounds — that contrast is intentional.
