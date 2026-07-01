# Retriever Examples

This repo’s public example surface is centered on the core runtime.

## Canonical Examples

Start here:

- `examples/tutorial/` — the canonical tutorial curriculum for the runtime
- `examples/control_demo.py` — optional web dashboard control demo for runtime orchestration

If you want the first tangible demo, start with live webcam color detection:

```bash
pixi run demo-webcam-detection
```

This runs `camera -> color detector -> display`. It asks for a live webcam and detects simple red/blue objects; use the tutorial module directly with `--camera-mode mock` if no camera is available.

Then use the pure-core sanity path to understand the API mechanics:

```bash
pixi run demo-basic-flow
pixi run demo-adapter-connection
pixi run demo-rt-execution
pixi run demo-stepper
```

Try the control surface separately:

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
