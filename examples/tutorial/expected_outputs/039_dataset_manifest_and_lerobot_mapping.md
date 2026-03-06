# Expected Output: TUT-039 Dataset Manifest and LeRobot Mapping

## Run

```bash
pixi run python -m examples.tutorial.h_release_readiness.03_dataset_manifest_and_lerobot_mapping
```

## Expected Console Signals

- Dataset manifest summary prints dataset id, episode count, and event count.
- LeRobot preview table lists frame indices per stream.

## Expected Artifacts

- `logs/tutorial_dataset/tut039_dataset_manifest.json`
- `logs/tutorial_dataset/tut039_lerobot_records.json`
