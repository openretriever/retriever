# Expected Output: TUT-040 Language Grounding Composition

## Run

```bash
pixi run python -m examples.tutorial.g_operations_interfaces.07_language_grounding_composition
```

## Expected Console Signals

- The table shows three grounded expressions.
- `the red object` resolves to `red`.
- `the blue object` resolves to `blue`.
- `the left target` resolves using the buffered detection snapshot and prints the left-most label for that step.

## Expected Artifact

- `logs/tutorial_language_grounding/tut040_language_grounding_summary.json`
