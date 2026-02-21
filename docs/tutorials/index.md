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

- [Lecture Packs L01-L11](lectures/index.md)

## Read This First

- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)

## Additional Deep-Dives

- [Stepper, Debugger, and MCAP Replay](walkthrough_stepper_debug_and_replay.md)
- [Core Release Path](walkthrough_core_release_path.md)
- [Notebook-Ready Export](notebook_ready.md)

## P0 Release-Readiness Sequence

```bash
pixi run p0-release-readiness
```

Equivalent step-by-step commands:

```bash
pixi run demo-trace-contract
pixi run demo-manifest-lineage
pixi run demo-policy-backends
pixi run demo-authority-fsm
```

Expected outputs for P0:
- `examples/tutorial/expected_outputs/024_trace_contract_basics.md`
- `examples/tutorial/expected_outputs/025_run_manifest_and_lineage.md`
- `examples/tutorial/expected_outputs/027_closed_loop_policy_backend_abstraction.md`
- `examples/tutorial/expected_outputs/028_operator_mode_and_authority_fsm.md`

## P1 Reliability Extensions

```bash
pixi run p1-reliability-gates
pixi run verify-backend-parity
pixi run verify-incident-replay
```

Expected output for P1:
- `examples/tutorial/expected_outputs/032_backend_parity_benchmark.md`
- `examples/tutorial/expected_outputs/033_incident_response_replay_drill.md`

## Advanced Tutorial Extensions

- `examples/tutorial/expected_outputs/034_functional_fanin_fanout.md`
- `examples/tutorial/expected_outputs/035_deadline_aware_mode_switch.md`
- `examples/tutorial/expected_outputs/036_mcap_session_inspection.md`

## Notebook-Ready Artifacts

```bash
pixi run export-notebook-ready
pixi run check-notebook-ready
```
