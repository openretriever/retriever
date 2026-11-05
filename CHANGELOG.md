# Changelog

Pre-1.0: `retriever-core` is changing rapidly, so detailed per-release notes
are deferred for now — see the commit history for what changed between
releases.

## Unreleased

- Support Rerun SDK versions `>=0.23.4,<0.43` for recording and visualization.
  Keep direct RRD replay when the legacy dataframe API is available. Newer SDKs
  report their version, the RRD path, and recovery steps instead of dropping the
  reader API. RRD payload writing and the existing replay CLI default remain.
- Preserve numpy dtype and shape, empty arrays, bytes, tuples, and nested values
  in MCAP through an explicit lossless codec schema. Escape literal marker keys
  so ordinary mappings remain data. Continue reading older
  array payloads. MCAP readback does not require Rerun.
- Add recording checks for SDK 0.23.4 and 0.42.0. MCAP mirrors remain explicit;
  recording and replay never create or infer a sibling artifact.

## [0.0.1] — 2026-07-09

Initial public release of `retriever-core`: the Retriever programming model and
runtime — `Flow`, `Pipeline`, `@io` typed messages, clocks (`Rate` / `Trigger` /
`Hybrid`), sync policies (`Latest` / `Window` / …), IR + topology, the in-process
stepper plus multiprocessing and dora backends, record/replay, and the
`retriever` CLI. Imports as `retriever`.

[0.0.1]: https://pypi.org/project/retriever-core/0.0.1/
