# Expected Output: TUT-037 Spatial Type Boundaries

## Run

```bash
pixi run python -m examples.tutorial.g_operations_interfaces.05_spatial_type_boundaries
```

## Expected Console Signals

- Registry parity line confirms `PoseStamped` import equals `get_type("PoseStamped")`.
- Boundary walkthrough table shows `frame_id=base` and increasing `x` values.

## Expected Artifact

- `logs/tutorial_spatial_types/tut037_spatial_type_summary.json`
