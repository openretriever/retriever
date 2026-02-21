---
title: "Tutorial Tracks"
---

# Tutorial Tracks

Canonical tutorials are organized in one-level topic tracks under `examples/tutorial/`.

## Tracks

- [A: Flow Fundamentals](track_a_flow_fundamentals.md)
- [B: IR and Execution](track_b_ir_and_execution.md)
- [C: Debug and Replay](track_c_debug_and_replay.md)
- [D: Closed-Loop, State, and Feedback](track_d_closed_loop_state_feedback.md)
- [E: Resource and Synchronization](track_e_resource_and_sync.md)
- [F: Policy Backends](track_f_policy_backends.md)
- [G: Operations and Interfaces](track_g_operations_interfaces.md)
- [H: Release Readiness](track_h_release_readiness.md)

## Lecture Pack

- [L01-L06 Foundations](lectures/index.md)

## P0 Release-Readiness Sequence

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

Expected outputs for P0:
- `examples/tutorial/expected_outputs/024_trace_contract_basics.md`
- `examples/tutorial/expected_outputs/025_run_manifest_and_lineage.md`
- `examples/tutorial/expected_outputs/027_closed_loop_policy_backend_abstraction.md`
- `examples/tutorial/expected_outputs/028_operator_mode_and_authority_fsm.md`
- `examples/tutorial/expected_outputs/029_release_readiness_walkthrough.md`
