# Retriever Examples

This repo’s public example surface is centered on the core runtime.

## Canonical Examples

Start here:

- `examples/tutorial/` — the canonical tutorial curriculum for the runtime
- `examples/control_demo.py` — optional web dashboard control demo for runtime orchestration

If you want the shortest path:

```bash
pixi run python -m examples.tutorial.a_flow_fundamentals.01_basic_flow
pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution
pixi run python -m examples.tutorial.c_debug_and_replay.01_debug_stepper
```

Then try the control surface separately:

```bash
pixi run -e control demo-control
```

## Tutorial Tracks

The tutorial tree is organized by topic:

- `a_flow_fundamentals`
- `b_ir_and_execution`
- `c_debug_and_replay`
- `d_closed_loop_state_feedback`
- `e_resource_and_sync`
- `f_policy_backends`
- `g_operations_interfaces`
- `h_release_readiness`

See also:

- `docs/quickstart.md`
- `docs/tutorials/index.md`
- `docs/handbook.md`

## Older Surfaces

Some later tracks and specialized examples are intentionally more operational or domain-specific. Use the tutorial tracks and focused guides first, then return to those later surfaces once the runtime model is already clear.
