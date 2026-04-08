---
title: "Integrated Tutorial: Debug to Release"
---

# Integrated Tutorial: Debug to Release

This page is the "read it once, then use it forever" tutorial for Retriever.

It is written as a single narrative because the workflow matters more than any single API:

1. You write flow logic.
2. You debug it in-process (so breakpoints work).
3. You record a short session (so you can reproduce bugs and share evidence).
4. You validate that behavior holds on real backends.
5. You turn the artifacts into a release decision (GO / NO-GO).

Along the way you will see the actual interfaces you will use in real projects:
`Flow.step(...)`, `Pipeline.connect(...)`, clocks (`Rate`, `Trigger`), adapters (`Latest`, `Hold`, `Window`),
and the stepper-first tools around recording and replay.

## Setup (One-Time) and How to Run These Examples

All commands below assume you are in the `retriever/` repo root.
These tutorials run via `pixi` and write evidence under `logs/`.

If this is your first time in the repo, install the environment once:

```bash
pixi install
```

Throughout the tutorial you will see commands like:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
```

That means: run a Python module inside the pinned environment.

## The Interface Map (Where Things Live)

If you only remember four locations, remember these:

- `examples/tutorial/` is the runnable code that demonstrates the public API.
- `docs/tutorials/` is the explanation layer (this page lives there).
- `pixi.toml` is the source of truth for "known good" task commands.
- `logs/` is where artifacts land. Treat it as your scratchpad and evidence folder.

Most tutorial modules print a short summary and also write a machine-readable artifact (JSON/CSV/MCAP)
so you can use the output in CI, attach it to bug reports, or compare runs.

## The Mental Model (Just Enough to Be Dangerous)

Retriever is a graph of typed transformations.

A `Flow` is the smallest unit. It takes a typed input object and returns a typed output object.
Those types are not decoration; they are the contract used by clocks, adapters, and validation.
Use `@io` directly; do not stack it with `@dataclass`.

```python
from retriever.flow import Flow, io


@io
class In:
    value: int

@io
class Out:
    result: int

class Double(Flow[In, Out]):
    def step(self, input: In) -> Out:
        return Out(result=input.value * 2)
```

A `Pipeline` is how you wire flows into a graph, and how you choose how the graph runs.
Two pieces of vocabulary show up everywhere:

- Clocks decide when a node runs. `Rate(hz=20)` is "run every step", `Trigger("image")` is "run on arrival of field image".
- Adapters decide what gets sampled from queues. `Latest()` is the default, `Hold()` and `Window()` are for multi-rate graphs.

Finally, there is a practical rule that drives the rest of this article:

If you want to use a debugger, start with in-process stepping.
Backends like `multiprocessing` and `dora` run flows in worker processes, so your editor breakpoint inside `Flow.step()`
often will not hit unless you attach to the worker.

## Part 1: Debug Logic With the Stepper (Breakpoints That Actually Hit)

We will start with the smallest pipeline that still has the real shape: a source, a transformation, and a sink.

Open `examples/tutorial/c_debug_and_replay/01_debug_stepper.py` and find this line in `DebugFlow.step(...)`:

```python
x = input.value  # put a breakpoint here
```

Now run the example for a few steps:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5
```

What you should see is a repeated step boundary and a sink print, roughly like:

```text
=== step 0 ===
[Sink] got value=2
...
```

When your breakpoint is set on `x = input.value`, you can inspect:

- The typed input (`Value(value=...)`).
- The returned output (also `Value(...)` in this toy example).
- Any per-flow state (for example, `Counter.count`).

Now practice the "break on failure" loop. This simulates what it feels like to debug a real incident: something fails at
a specific step and you want to inspect state right before it happens.

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper --steps 5 --fail-at 3
```

The important learning here is not the toy error. It is that `Pipeline.step()` runs in your current process, so
breakpoints and "break on exception" work the way you expect.

## Part 2: Trace Contracts (When You Need to Prove Where Time Went)

After logic is correct, the next class of bug is "it works, but it is late, bursty, or stuck".
For that you need a trace contract: a small, regular record of what moved through the graph and when.

Run the trace contract tutorial:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
```

This produces two artifacts:

- `logs/tutorial_trace/tut024_trace_envelopes.jsonl` (one trace envelope per edge event)
- `logs/tutorial_trace/tut024_trace_report.json` (summary and first-bottleneck guess)

If you open the report JSON, you will see an explicit "edge id", latency, and queue depth snapshots.
That is what you want in practice: something you can hand to another person and say "the first bottleneck was here".

## Part 3: Record a Session (MCAP) So You Can Reproduce and Share

Stepping makes debugging easy, but it only helps if you can reproduce the input conditions.
Recording turns a one-off failure into a repeatable artifact.

In Retriever, MCAP is used as a compact "flight recorder" format: it can be viewed in tools like Rerun, and it is
convenient to store in `logs/` or attach to an issue.

Record a short perception session:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception record --out logs/perception.rrd --replay-out logs/perception.mcap --steps 10
```

Notes:

- This tutorial tries to use a real camera and falls back to a synthetic stream if none is available.
- The concrete thing you care about is that you now have:
  - `logs/perception.rrd` for Rerun inspection
  - `logs/perception.mcap` as a mirrored interchange artifact

If you want to view the recording immediately, you can use the library helper:

```bash
pixi run python -c "import retriever; retriever.view('logs/perception.rrd')"
```

If you want to load it programmatically (for example, to build a notebook later), you can iterate the step stream:

```python
from retriever.lib.mcap import MCAPReader

with MCAPReader("logs/perception.mcap") as reader:
    first = next(iter(reader))

print("step keys:", sorted(first.keys()))
print("outputs keys (prefix):", list(first.get("outputs", {}).keys())[:3])
```

## Part 4: Replay (Iterate on Logic Without Touching Hardware)

Replay is the bridge between "debuggable" and "reproducible": you run the same session repeatedly while you change code.

Run the replay mode:

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.04_record_replay_perception replay --recording logs/perception.rrd --steps 10 --visualize cv2
```

This replay is intentionally in-process. That is the point: it keeps the "set a breakpoint in `Flow.step()`" workflow
alive even when the original input came from hardware.

Replay accepts either `.rrd` or `.mcap`.
If you prefer a headless run, use `--visualize stdout`.
If you want to stream live to Rerun while replaying, use `--visualize rerun`.
If you want both the cv2 window and Rerun, use `--visualize both`.

## Part 5: Turn Runs Into Evidence (Run Manifests and Lineage)

At this point you can:

- debug logic with stepping
- record inputs to a file
- replay deterministically while you iterate

The next step is release engineering: you need to answer "what exactly ran, and what artifacts were produced?"
That is what a run manifest is for.

Run the manifest and lineage walkthrough:

```bash
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
```

This writes a small bundle under `logs/tutorial_manifest/`:

- `logs/tutorial_manifest/artifacts/<run_id>.mcap` (the recording)
- `logs/tutorial_manifest/manifests/<run_id>.manifest.json` (machine-readable metadata)
- `logs/tutorial_manifest/manifests/tut025_demo_compare.json` (a compare summary)

A manifest is meant to be boring and inspectable: it includes a run id, a config hash, artifact paths and hashes,
and a literal replay command you can copy/paste.

## Part 6: Authority and Intervention Semantics (The Operator Contract)

In real systems you often need to switch authority between autonomy, shared control, and direct operator control.
Those transitions should not be "best effort"; they should be enforced and logged, because they are part of your safety
and incident response story.

Run the authority FSM tutorial:

```bash
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm
```

This prints a transition table and writes:

```text
logs/tutorial_authority/tut028_authority_log.json
```

Notice two things in the output:

1. An invalid transition is intentionally blocked (so you can see what enforcement looks like).
2. Intervention intervals are marked with explicit `intervention_start` and `intervention_end` markers.

Those markers are the minimum you need to answer "when did an operator intervene?" in a replay or postmortem.

## Part 7: Policy Backends (Swap Implementation Without Changing the Graph)

Once you have a stable graph, you will eventually want to change the implementation behind one node.
For example: you might start with a mock policy, then move to a learned policy, or run a hardware-specific policy on the robot.

The contract you want is: the graph topology stays the same, and only the backend implementation changes.

Run the policy backend abstraction tutorial:

```bash
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
```

It prints a graph fingerprint (so you can verify topology stability) and writes a small metrics table:

```text
logs/tutorial_policy/tut027_backend_metrics.csv
```

That CSV is intentionally simple: it is the kind of thing you can diff in a PR, chart, or use as evidence for a gate.

## Part 8: Hard Gates (Parity and Incident Replay)

Everything above is developer workflow. The next two steps are release workflow: hard, automatable gates.

Backend parity gate means: run the same representative pipeline on multiple backends and verify that the results match
for a deterministic prefix (within timing tolerances).

```bash
pixi run verify-backend-parity
```

This writes:

- `logs/tutorial_parity/tut032_backend_parity.json`
- `logs/tutorial_parity/tut032_backend_parity_checks.csv`

Incident replay gate means: an incident drill is only "real" if the replay confirms the diagnosis.
The drill intentionally injects a failure, computes a diagnosis signature, and then verifies that the same signature
appears under replay.

```bash
pixi run verify-incident-replay
```

This writes:

- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`

If you are building public-facing tooling, these two gates are the first ones to make CI-required.

## Shortcut Tasks (Same Flow, Fewer Commands)

If you want the same flow via named tasks:

```bash
pixi run p0-release-readiness
pixi run p1-reliability-gates
pixi run verify-backend-parity
pixi run verify-incident-replay
```

## Where You Are After This Page

If you worked through the tutorial in order, you now have a complete, end-to-end loop:

- You can step through `Flow.step()` with a breakpoint and inspect typed payloads.
- You can record and replay sessions so bugs are reproducible.
- You can generate evidence artifacts under `logs/` that can be checked automatically.
- You can run parity and incident gates and treat failures as release blockers.

That is the core Retriever workflow, end to end.
