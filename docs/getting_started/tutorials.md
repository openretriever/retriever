---
title: "Tutorials"
---

# Tutorials

Canonical tutorials are grouped into one-level topic tracks under `examples/tutorial/`.

## Start Here

0. Read the runtime quickstart first: [../quickstart.md](../quickstart.md)
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
- [Lecture Packs L01-L11](../tutorials/lectures/index.md)

## Fast P0 Sequence

```bash
pixi run p0-release-readiness
```

## Related

- Expected output references:
  - `examples/tutorial/expected_outputs/024_trace_contract_basics.md`
  - `examples/tutorial/expected_outputs/025_run_manifest_and_lineage.md`
  - `examples/tutorial/expected_outputs/027_closed_loop_policy_backend_abstraction.md`
  - `examples/tutorial/expected_outputs/028_operator_mode_and_authority_fsm.md`
  - `examples/tutorial/expected_outputs/037_spatial_type_boundaries.md`
  - `examples/tutorial/expected_outputs/038_data_multistream_join.md`
  - `examples/tutorial/expected_outputs/039_dataset_manifest_and_lerobot_mapping.md`
- Notebook-ready export:
  - [Notebook-Ready Export](../tutorials/notebook_ready.md)
  - `pixi run export-notebook-ready`
  - `pixi run check-notebook-ready`
- Advanced examples:
  - [Zero-Copy Guide](../guides/advanced_zero_copy.md)
  - [Spatial Types v1](../guides/robotics_typing.md)
  - [Data and EventStream v1](../guides/data_spec_eventstream.md)
