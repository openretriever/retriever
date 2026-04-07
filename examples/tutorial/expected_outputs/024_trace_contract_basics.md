# Expected Output: TUT-024 Trace Contract Basics

## Run
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.06_trace_contract_basics
```

## Expected Console Highlights
- `Trace Envelope Field Sample` is printed with fields such as:
  - `schema_version`
  - `run_id`
  - `edge_id`
  - `timestamp_emit_s`
  - `timestamp_consume_s`
  - `latency_ms`
  - `queue_depth`
- `Top-3 Latency Edges` table appears.
- `Per-Edge Latency + Queue Snapshot` table appears.
- `Bottleneck Diagnosis` points to the first edge crossing threshold.
- Includes one intentional lag diagnosis at policy stage.

## Expected Artifacts
- `logs/tutorial_trace/tut024_trace_envelopes.jsonl`
- `logs/tutorial_trace/tut024_trace_report.json`
