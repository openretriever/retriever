# tutorial (Canonical Runtime Examples)

Tutorials are organized as one-level ordered topic tracks under `examples/tutorial/`.
Each track uses local numbering (`01_`, `02_`, ...) within that folder.

## Tracks

- `a_flow_fundamentals/`
- `b_ir_and_execution/`
- `c_debug_and_replay/`
- `d_closed_loop_state_feedback/`
- `e_resource_and_sync/`
- `f_policy_backends/`
- `g_operations_interfaces/`
- `h_release_readiness/`

## P0 Release-Readiness Modules

- `c_debug_and_replay/06_trace_contract_basics.py`
- `h_release_readiness/01_run_manifest_and_lineage.py`
- `f_policy_backends/01_closed_loop_policy_backend_abstraction.py`
- `d_closed_loop_state_feedback/03_operator_mode_and_authority_fsm.py`
- `h_release_readiness/02_release_readiness_walkthrough.py`

## P1 Reliability Hardening Modules

- `b_ir_and_execution/09_backend_parity_benchmark.py`
- `c_debug_and_replay/07_incident_response_replay_drill.py`

## Advanced Extension Modules

- `e_resource_and_sync/06_functional_fanin_fanout.py`
- `d_closed_loop_state_feedback/13_deadline_aware_mode_switch.py`
- `c_debug_and_replay/08_mcap_session_inspection.py`

## P0 Runner

```bash
./scripts/run_p0_release_readiness.sh
pixi run p0-release-readiness
```

## Expected Outputs

- `expected_outputs/024_trace_contract_basics.md`
- `expected_outputs/025_run_manifest_and_lineage.md`
- `expected_outputs/027_closed_loop_policy_backend_abstraction.md`
- `expected_outputs/028_operator_mode_and_authority_fsm.md`
- `expected_outputs/034_functional_fanin_fanout.md`
- `expected_outputs/035_deadline_aware_mode_switch.md`
- `expected_outputs/036_mcap_session_inspection.md`
- `expected_outputs/032_backend_parity_benchmark.md`
- `expected_outputs/033_incident_response_replay_drill.md`

## Reliability Gates

```bash
pixi run p1-reliability-gates
pixi run verify-backend-parity
pixi run verify-incident-replay
```

## Notebook-Ready Export

```bash
pixi run demo-mcap-session-inspection
pixi run export-notebook-ready
pixi run check-notebook-ready
```
