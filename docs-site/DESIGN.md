# Design notes — Retriever docs site

The look-and-feel reference for this Starlight site. Read before changing
`src/styles/retriever.css` or a page's visual structure. This site and the
GoldenRetriever docs site share **one design language**, inspired by
**Claude/Anthropic** (warm, calm, editorial) and **Pixi** (concise,
command-first, honest positioning). Keep them consistent.

## Principles

1. **Warm paper, never stark white.** Page ground is a soft warm cream in light,
   a warm charcoal (not flat black) in dark — like Claude's sites. Surfaces
   (cards, nav) sit a shade lighter so they lift gently.
2. **Restraint.** One accent (Retriever orange/gold). Calm, layered shadows.
   Spacing and hierarchy over effects.
3. **Technical-editorial type.** Monospace for eyebrows/labels and table headers
   (ties identity to the code subject); clean sans for prose.
4. **Command-first, concise (Pixi).** Lead with the runnable command + expected
   output; pointed benefit phrases over paragraphs.
5. **Honest positioning (Pixi).** Compare fairly (see `/concepts/why-retriever/`),
   never hype.
6. **Keep what Pixi omits:** expected-output blocks and the agent-first layer
   (`llms.txt`, `AGENTS.md`).

## Shared tokens (target — align `src/styles/retriever.css` to these)

| Token | Light | Dark |
| --- | --- | --- |
| page ground | `#f7f3ea` warm cream | `#1a1712` warm charcoal |
| surfaces (cards/nav) | `#fffdf7` | `#221d16` |
| accent | `#f97316` | `#fb923c` |
| text-accent | `#c2410c` | `#fdba74` |

Check every change in light **and** dark.

## Component conventions

- **Eyebrow:** monospace, uppercase, wide tracking, 2px accent rule beneath.
- **Cards:** accent top-edge at rest; hover lifts 3px + accent border + soft
  shadow.
- **Tables:** monospace headers, comfortable padding, quiet accent row-hover;
  for a comparison matrix, spotlight the Retriever column.
- **Shadows:** layered, restrained, warm-tinted.
- **CTAs:** one primary (filled/tinted accent), rest ghost pills.

## Writing patterns (Pixi)

Mental-model bridge up top ("if you know PyTorch…"); quickstart = one
copy-paste block; comparison matrix for positioning; commands paired with
expected output.

## Guardrails

No second accent hue, no webfonts (CSP/perf), no heavy effects. Prose measure
~60–68ch; tables/cards may span full width. `retriever.css` is the only home
for site-wide visual tokens.

Companion: GoldenRetriever's `docs-site/DESIGN.md` (same language). This is the
canonical design reference for both.
