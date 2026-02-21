---
title: "Integrated Tutorial: Debug to Release"
---

# Integrated Tutorial: Debug to Release

This is the single beginner-friendly tutorial for Retriever’s core workflow.  
It is designed as a real walk-through, not just a command list.

You will learn the concepts and then execute them in order:
1. stepper-first debugging
2. debugging inside `Flow.run()`
3. MCAP record + replay
4. backend abstraction and parity gates
5. incident replay consistency
6. final release `GO/NO-GO` evidence

## Who This Is For
- You are new to Retriever.
- You want one guided path from local debugging to release confidence.
- You want to understand what each interface does and when to use it.

## Part 1: Concept Model (Plain Language)

Retriever has 5 core interfaces you should know:

1. `Flow` interface
- A `Flow` is a typed transformation: input -> output.
- You implement logic in `Flow.run(...)`.
- This is where most logic bugs live.

2. `Pipeline` interface
- A `Pipeline` wires multiple flows into a graph.
- You connect flow outputs to downstream inputs with adapters/sync rules.
- This is where graph and integration bugs live.

3. Clocking interface (`Rate`, `Trigger`, `Hybrid`)
- Clocks decide *when* each flow runs.
- `Rate`: periodic.
- `Trigger`: on field arrival.
- Wrong clocking often looks like lag, dropped updates, or stale behavior.

4. Runtime interface (`step()` vs `run(...)`)
- `step()` runs in-process (great for breakpoints).
- `run(backend=...)` executes with runtime backends like multiprocessing/dora.
- Rule of thumb: fix logic with `step()`, validate deployment behavior with backend runtime.

5. Evidence interface (artifacts in `logs/`)
- Tutorials write JSON/CSV/MD artifacts.
- These artifacts are the release evidence for parity, incidents, and go/no-go.

## Part 2: Interface Walkthrough (Where Things Are)

From repo root (`retriever/`):

- Tutorial code:
  - `examples/tutorial/`
- Tutorial docs:
  - `docs/tutorials/`
- Runtime artifacts:
  - `logs/`
- Command entrypoint:
  - `pixi.toml` tasks + `pixi run ...`

Useful pattern:
```bash
pixi run python -m <module_path>
```

## Part 3: Hands-On Journey

## Step 0: Quick fundamentals (optional but recommended)

Run these once to understand baseline authoring surfaces:
```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
pixi run python -m examples.tutorial.a_flow_fundamentals.02_clock_types
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
```

What to learn:
- how typed I/O fields appear
- how clocks bind to flows
- how connections/adapters map fields

## Step 1: Stepper-first debugging

### 1A) Run deterministic in-process stepping
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
```

Look for:
- deterministic step output
- no child-process debugging complexity

### 1B) Trigger controlled failure
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5 --fail-at 3
```

Look for:
- failure at exact configured step
- immediate location for diagnosis

### 1C) Debug inside `Flow.run()`
In your editor:
1. open `examples/tutorial/c_debug_and_replay/01_debug_stepper.py`
2. place breakpoint in `DebugFlow.run(...)`
3. re-run 1A/1B

Goal:
- inspect typed values before/after transformation
- confirm state/logic correctness before backend validation

## Step 2: Record and Replay (MCAP workflow)

### 2A) Record
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.mcap --steps 10
```

Artifact:
- `logs/perception.mcap`

Why:
- capture a session once for repeatable replay

### 2B) Replay
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
```

Look for:
- consistent repeat behavior
- fast iteration without live sensor variance

## Step 3: Runtime/contract validation

### 3A) Policy backend abstraction (`TUT-027`)
```bash
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
```

Look for:
- rows for `openpi_pi05`, `lerobot`, `mock`
- same graph contract while backend implementation changes

Artifact:
- `logs/tutorial_policy/tut027_backend_metrics.csv`

### 3B) Backend parity hard gate (`TUT-032`)
```bash
pixi run verify-backend-parity
```

Look for:
- task exits successfully
- parity report says pass

Artifacts:
- `logs/tutorial_parity/tut032_backend_parity.json`
- `logs/tutorial_parity/tut032_backend_parity_checks.csv`

## Step 4: Incident response drill (`TUT-033`)

```bash
pixi run verify-incident-replay
```

Look for:
- incident root cause candidate exists
- replay signature equals live signature

Artifacts:
- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`

## Step 5: Final release walkthrough (`TUT-029`)

```bash
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

Look for:
- gate table with pass/fail reason
- final explicit `GO` or `NO-GO`

Artifacts:
- `logs/tutorial_release_readiness/tut029_release_checklist.md`
- `logs/tutorial_release_readiness/tut029_release_summary.json`

## Part 4: One Copy/Paste Block

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.mcap --steps 10
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
pixi run verify-backend-parity
pixi run verify-incident-replay
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

## Part 5: How To Read Key Outputs

1. Parity report (`tut032_backend_parity.json`)
- check `parity.overall_pass`
- verify both backend counts are > 0

2. Incident report (`tut033_incident_report.json`)
- check `overall_pass`
- check `diagnosis_signature.live == diagnosis_signature.replay`

3. Release summary (`tut029_release_summary.json`)
- check final decision and blocking gates

## Part 6: Failure Triage

- Fails in stepper phase: fix flow logic/state first.
- Fails in MCAP/replay phase: fix capture/replay assumptions and input handling.
- Fails parity: investigate backend runtime drift/contract mismatch.
- Fails incident replay: investigate diagnosis logic or determinism.
- Fails release walkthrough: fix missing evidence/docs alignment.

## Completion Criteria

You are done when:
1. all steps above run successfully
2. required artifacts exist
3. release walkthrough returns evidence-backed `GO`
