---
title: "Tutorials"
---

# Tutorials

Canonical tutorials are grouped into one-level topic tracks under `examples/tutorial/`.

## Start Here

1. Read the track index: [../tutorials/index.md](../tutorials/index.md)
2. Pick a track page:
- [Track A: Flow Fundamentals](../tutorials/track_a_flow_fundamentals.md)
- [Track B: IR and Execution](../tutorials/track_b_ir_and_execution.md)
- [Track C: Debug and Replay](../tutorials/track_c_debug_and_replay.md)
- [Track D: Closed-Loop, State, and Feedback](../tutorials/track_d_closed_loop_state_feedback.md)
- [Track E: Resource and Synchronization](../tutorials/track_e_resource_and_sync.md)
- [Track F: Policy Backends](../tutorials/track_f_policy_backends.md)
- [Track G: Operations and Interfaces](../tutorials/track_g_operations_interfaces.md)
- [Track H: Release Readiness](../tutorials/track_h_release_readiness.md)
3. Optional lecture-format notes:
- [Lecture Pack L01-L06](../tutorials/lectures/index.md)

## Fast P0 Sequence

```bash
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
pixi run python -m examples.tutorial.h_release_readiness.01_run_manifest_and_lineage demo
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
pixi run python -m examples.tutorial.d_closed_loop_state_feedback.03_operator_mode_and_authority_fsm
pixi run python -m examples.tutorial.h_release_readiness.02_release_readiness_walkthrough
```

## Related

- Expected output references:
  - `examples/tutorial/expected_outputs/024_trace_contract_basics.md`
  - `examples/tutorial/expected_outputs/025_run_manifest_and_lineage.md`
  - `examples/tutorial/expected_outputs/027_closed_loop_policy_backend_abstraction.md`
  - `examples/tutorial/expected_outputs/028_operator_mode_and_authority_fsm.md`
  - `examples/tutorial/expected_outputs/029_release_readiness_walkthrough.md`
- Advanced examples:
  - [Zero-Copy Guide](../guides/advanced_zero_copy.md)
