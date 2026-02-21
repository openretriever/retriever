---
title: "L04 Building and Validating IR"
---

# L04 Building and Validating IR

## Metadata
- Lecture ID: L04
- Track: B (IR and Execution)
- Tier: 1-2
- Duration: 25 minutes
- Prerequisites: L01-L03

## Learning Objectives
1. Move from pipeline graph to validated IR.
2. Read IR node/edge/topology fields and explain their purpose.
3. Explain how execution build policies reduce executor count.

## Core Concept
- Mental model: validation converts authored graph into explicit runtime contract.
- Key pitfall: treating IR as debug noise instead of the execution source of truth.

## Live Demo Mapping
- Primary runnable files:
  - `examples/tutorial/b_ir_and_execution/01_context_graph.py`
  - `examples/tutorial/b_ir_and_execution/02_ir_validation.py`
- Optional extension: `examples/tutorial/b_ir_and_execution/03_execution_build.py`

## Runnable Commands
Run from repository root:

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.01_context_graph
pixi run python -m examples.tutorial.b_ir_and_execution.02_ir_validation
pixi run python -m examples.tutorial.b_ir_and_execution.03_execution_build
```

## What To Observe
- Graph output shows node list, edge list, sources, sinks, and cycle groups.
- Validation prints `Validation successful` and JSON IR with `nodes`, `edges`, `topology`.
- Execution build shows partition count and node reduction summary.

## Failure Drill
- Introduce a mismatched port map or type mismatch and rerun validation.
- Confirm failure happens before runtime and identify which contract check caught it.

## Exercise
- Required task: capture one IR JSON and annotate 3 fields that drive runtime behavior.
- Stretch task: compare conservative vs aggressive policy reduction and explain tradeoff.

## Evaluation Rubric
- Pass criteria: learner can explain why compile/validation stage prevents runtime ambiguity.
- Common failure signature: learner cannot map an IR edge back to source/destination flow ports.

## Follow-up
- Next lecture: `l05_runtime_backends_and_execution_lifecycle.md`
- Related tutorials: `b_ir_and_execution/04_rt_execution.py`
