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

## P0 Runner

```bash
./scripts/run_p0_release_readiness.sh
```

## Expected Outputs

- `expected_outputs/024_trace_contract_basics.md`
- `expected_outputs/025_run_manifest_and_lineage.md`
- `expected_outputs/027_closed_loop_policy_backend_abstraction.md`
- `expected_outputs/028_operator_mode_and_authority_fsm.md`
- `expected_outputs/029_release_readiness_walkthrough.md`
