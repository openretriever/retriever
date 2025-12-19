# 00_refact (Canonical Runtime Examples)

This folder contains the **canonical, maintained** examples for the **refactored Retriever runtime**.

If you only want a working demo, start here. These examples match `docs/handbook.md`.

Note: `00_refact` is not a valid Python identifier, so examples that import code from this folder use `importlib`.
Running modules via `python -m ...` works fine.

## Quick Start

```bash
# Dora perception demo (camera → detection → display)
pixi run demo-dora

# Service request/response demo (Dora recommended)
pixi run demo-request-dora
```

## Tutorial index (canonical)

Everything in this folder is runnable via:

```bash
pixi run python -m examples.tutorial.<module_name>
```

### Flow + clocks + adapters → IR

- `000_basic_flow.py`: Flow basics and `@flow_io`
- `001_clock_types.py`: `Rate`, `Trigger`, `Hybrid`, `Tick`
- `002_adapter_connection.py`: `Latest`/`Hold`/`Window`/`Events` + field mapping
- `003_context_graph.py`: graph construction and inspection
- `004_ir_validation.py`: validate + inspect IR

### Execution (mp + dora)

- `005_execution_build.py`: build an `ExecutionGraph` from IR
- `006_rt_execution.py`: run a pipeline on the multiprocessing backend
- `007_full_pipeline.py`: a more complex pipeline wiring example
- `008_dora_simple.py`: minimal dora backend run
- `009_dora_perception.py`: perception demo (real camera → detection → display)
- `010_request_response.py`: service call + request/response wiring

### Debugging + record/replay (in-process)

- `011_debug_stepper.py`: minimal `Pipeline.step()` breakpoint demo
- `012_debug_perception_stepper.py`: debug perception with deterministic synthetic frames
- `013_debug_perception_stepper_real_camera.py`: debug perception with a real camera (still in-process)
- `014_record_replay_perception.py`: record once (camera), replay later (no hardware)

### Runtime internals demos

- `015_buffer_engine_demo.py`: select runtime buffer engine via `backend_config`
- `016_closed_loop_env.py`: closed-loop (cyclic) env/controller pipeline (mp or dora)
- `017_pipeline_ergonomics.py`: explicit vs `with pipe:` vs `retriever.connect(...)`
- `018_registry_basics.py`: type/flow/pipeline registries (PyTorch-ish discovery)

## Recommended progression

```bash
# Pipeline ergonomics: explicit vs `with pipe:` vs `retriever.connect(...)`
pixi run python -m examples.tutorial.017_pipeline_ergonomics --mode context --exec step

# Debugging: stepper + breakpoints inside Flow.run()
pixi run python -m examples.tutorial.011_debug_stepper --fail-at 3

# Debug perception with stepper (synthetic frames, deterministic)
pixi run python -m examples.tutorial.012_debug_perception_stepper

# Debug perception with stepper (real camera; optional window)
pixi run python -m examples.tutorial.013_debug_perception_stepper_real_camera --steps 10 --sleep 0.05

# Record once from camera, replay later (no hardware)
pixi run python -m examples.tutorial.014_record_replay_perception record --out logs/perception_recording.pkl.gz --steps 10 --dt 0.05
pixi run python -m examples.tutorial.014_record_replay_perception replay --recording logs/perception_recording.pkl.gz --steps 10 --dt 0.05

# Closed-loop env/controller pipeline (multiprocess or dora)
pixi run python -m examples.tutorial.016_closed_loop_env --env toy --backend multiprocessing --hz 10 --duration 3
```

## Other files in this folder

Files `000_*` → `006_*` are smaller “concept-to-IR-to-runtime” walkthroughs and may be reorganized over time.
