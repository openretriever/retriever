# Expected Output: TUT-033 Incident Response Replay Drill

## Run
```bash
pixi run python -m examples.tutorial.c_debug_and_replay.07_incident_response_replay_drill
```

## Expected Console Highlights
- Incident drill summary table comparing baseline vs incident vs replay p95/max latency.
- Drill checks table including:
  - `incident_detected`
  - `policy_path_flagged`
  - `replay_signature_match`
  - `policy_peak_regression_detected`
- Final `PASS` or `FAIL` drill result.

## Expected Artifacts
- `logs/tutorial_incident/tut033_incident_trace.jsonl`
- `logs/tutorial_incident/tut033_replay_trace.jsonl`
- `logs/tutorial_incident/tut033_incident_report.json`
- `logs/tutorial_incident/tut033_incident_checklist.md`
