# tutorial

This directory is the runnable source tree for Retriever tutorials.

If you are learning Retriever, start with `docs/tutorials/index.md`.
This README is a source map, not the main learning front door.

## Recommended Short Path

Run these first:

- `a_flow_fundamentals/01_basic_flow.py`
- `a_flow_fundamentals/03_adapter_connection.py`
- `b_ir_and_execution/04_rt_execution.py`
- `c_debug_and_replay/01_debug_stepper.py`
- `c_debug_and_replay/04_record_replay_perception.py`
- `g_operations_interfaces/06_composable_pipelines.py`

## Track Map

- `a_flow_fundamentals/`: authoring, clocks, adapters, ergonomics
- `b_ir_and_execution/`: IR inspection, execution graphs, backends
- `c_debug_and_replay/`: stepper, traces, `.rrd` / `.mcap`, replay
- `d_closed_loop_state_feedback/`: stateful flows, feedback, authority, replanning
- `e_resource_and_sync/`: synchronization, fan-in/fan-out, event joins
- `f_policy_backends/`: backend swapping behind one graph contract
- `g_operations_interfaces/`: registries, composition, typed boundaries
- `h_release_readiness/`: manifests, evidence, dataset export contracts

## Notes

- Track numbering is local to each folder.
- Keep non-hardware and mock-safe paths first when teaching new users.
- Expected outputs live under `expected_outputs/`.
