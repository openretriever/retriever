# B IR and Execution

## Tutorials

- `01_context_graph.py`
- `02_ir_validation.py`
- `03_execution_build.py`
- `04_rt_execution.py`
- `05_dora_simple.py`
- `06_dora_perception.py`
- `07_request_response.py`
- `08_detection_window_stats.py`

## What To Expect

- Inspect IR structure and runtime topology.
- Run pipelines across multiprocessing and Dora backends.
- Validate perception/execution behavior end-to-end.

## Run

```bash
pixi run python -m examples.tutorial.b_ir_and_execution.01_context_graph
pixi run python -m examples.tutorial.b_ir_and_execution.02_ir_validation
pixi run python -m examples.tutorial.b_ir_and_execution.03_execution_build
pixi run python -m examples.tutorial.b_ir_and_execution.04_rt_execution
pixi run python -m examples.tutorial.b_ir_and_execution.05_dora_simple
pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception
pixi run python -m examples.tutorial.b_ir_and_execution.07_request_response
pixi run python -m examples.tutorial.b_ir_and_execution.08_detection_window_stats --backend multiprocessing --duration 3
```
