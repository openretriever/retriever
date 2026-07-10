# Design notes — Retriever (core) docs site

How this site should look and read. Read before touching
`src/styles/retriever.css` or a page's structure.

## North star

Two docs sites we want to feel like:

- **Claude Code Docs** (code.claude.com) — white, calm, generous whitespace,
  quiet active states, tabbed code, restrained accent.
- **OpenAI Developers** (developers.openai.com) — white, minimal, numbered
  setup steps, tabbed surfaces, near-monochrome with a single dark primary.

Core Retriever docs are **clean and light** — a precise technical reference.
This is deliberately distinct from GoldenRetriever's warm "golden paper" tone.
Shared discipline, different ground:

- **Core = white, precise, reference.**
- **Golden = warm, applied, exploratory.**

Keep core white. Do not import Golden's cream background.

## What those references teach (and we follow)

1. **Restraint is the whole aesthetic.** Mostly ink-on-white with lots of air.
   The accent (Retriever orange) appears in small doses — links, one active
   state, a small highlight — never as loud bars, gradients, or big fills.
   If a page has more than a couple of accent moments, pull back.
2. **Quiet active states.** The active sidebar item is a soft neutral pill (a
   faint gray/tinted background), not a bold colored bar. Look at Claude Code
   Docs' sidebar.
3. **Generous whitespace and a calm type scale.** Comfortable line-height,
   clear heading steps, prose measure ~65–72ch. Let spacing carry hierarchy.
4. **Tabbed code for multi-language / multi-surface** (Python | TypeScript, or
   App | CLI | Cloud). One clean copy affordance.
5. **Numbered steps for setup flows** (OpenAI's quickstart), not walls of prose.
6. **One primary action per view.** A single strong button; everything else
   ghost/text.

## Writing (Pixi discipline + no slop)

- Command-first: lead with the runnable command and its expected output.
- Concise, human prose. **Avoid AI-slop cadence** — the giveaways are
  parallel "X gives you A, B, and C; Y adds D, E, and F" constructions,
  empty tricolons, and sentences that restate the heading. Say the thing once,
  plainly.
- Honest positioning — see `/concepts/why-retriever/`.
- Keep expected-output blocks and the agent-first layer (`llms.txt`, `AGENTS.md`).

## Tokens & conventions (source of truth: `src/styles/retriever.css`)

- **Ground:** white / near-white in light; keep dark tasteful (not pure black).
- **Accent:** Retriever orange, used sparingly. Prefer `--sl-color-text-accent`
  for text and thin (1–2px) accent details over 4px bars and gradients.
- **Eyebrow:** monospace, uppercase, wide tracking, subtle accent rule.
- **Cards:** quiet — hairline border, minimal shadow, gentle hover; not floaty.
- **Tables:** monospace headers, comfortable padding, quiet row-hover; spotlight
  the Retriever column in comparison matrices.

## Guardrails

Keep the light ground. One accent hue. No webfonts (CSP/perf). No heavy
shadows or gradients. `retriever.css` is the only home for site-wide tokens.

Companion: GoldenRetriever's `docs-site/DESIGN.md` (warm variant, same
discipline). This pairing — clean core, warm Golden — is intentional.

## Paper-grounded content (source of truth for claims)

Docs claims must match the current project paper draft. Use this canonical language:

- **Thesis:** Retriever is a *programming model and runtime for closed-loop,
  asynchronous robot agents*, grounded in time-aware stream semantics.
- **Agent =** a graph of stateful *causal stream functions* (`Flow`s) on explicit
  *run clocks*; edges carry *synchronization policies* for deterministic input
  consumption.
- **Headline property — functional determinism:** given the same ordered,
  timestamped input history (including a fixed tie order), deterministic Flows
  and sync policies yield the same discrete-event output history. Live
  scheduling determines which history is recorded; replay and verification are
  defined over that captured history. Prefer this over vague "reproducible".
- **The problem (two mismatches), stated precisely:**
  1. *Physics vs. compute* — big models (VLMs) have variable latency; control
     needs deadlines. Blocking stalls; non-blocking gives stale decisions.
  2. *Determinism vs. asynchrony* — middleware (ROS) uses implicit callback
     ordering → schedule-dependent nondeterminism, hard to replay/verify.
- **Positioning:** PyTorch assumes discrete steps; ROS assumes loose message
  passing. Retriever is a behavior-level graph with explicit clocks/sync and
  functional determinism, for closed-loop agent composition. It *coexists with*
  (does not replace) transport middleware, compiles to an IR, and targets
  backends (e.g. Dora).
- **Do not overclaim.** Evidence = one real-robot case study + controlled
  studies of runtime overhead and deterministic replay. No broad superiority.

**Canonical hero example** (keep pages consistent with this shape):

```python
head_cam = CameraSource(id=0)    @ Rate(hz=30)
belief   = BeliefMemoryFlow()    @ Trigger("inspection_done")
planner  = VLMPlanFlow("gemini") @ Trigger("replan")
vla      = VLASkillFlow("pi05")  @ Rate(hz=2)
robot    = ControllerFlow(id=0)  @ Rate(hz=200)

pipe = Pipeline("closed-loop agent")
with pipe:
    head_cam.then(belief, sync=Latest()).then(planner, sync=Latest()).then(vla, sync=Latest())

pipe.step(dt=0.1)          # debug in-process
pipe.run(backend="dora")   # deploy async
```

**Per-page alignment targets:**
- `index` — thesis + functional determinism in the lede.
- `concepts/why-retriever` — the two mismatches + determinism + comparison table.
- `concepts/flow` — Flow = stateful causal stream function; `step()` is the unit.
- `concepts/time-and-sync` — clocks = *when*; sync policies = *which input record*.
- `concepts/runtime` — graph → IR → backends; local step is a debugger tick, while backends schedule wall-clock rates; record/replay.
- `tutorials/*` — command-first, expected output, the hero example's shape.
