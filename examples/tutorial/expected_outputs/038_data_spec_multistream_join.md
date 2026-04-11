# Expected Output: TUT-038 Data Spec Multistream Join

## Run

```bash
pixi run python -m examples.tutorial.e_resource_and_sync.07_data_spec_multistream_join
```

## Expected Console Signals

- Exact join table shows only timestamp-aligned pairs.
- Latest-before and window joins show additional compatible pairs.
- Processing-time table shows `latest`, `hold`, and `window_mean` values.

## Expected Artifact

- `logs/tutorial_data_spec/tut038_multistream_join.json`
