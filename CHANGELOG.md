# Changelog

Pre-1.0: `retriever-core` is changing rapidly, so detailed per-release notes
are deferred for now — see the commit history for what changed between
releases.

## Unreleased

- Correct the previously untested recording extra floor to `rerun-sdk>=0.23.4`.
  With SDK 0.21.0, the current logging and pipeline regression tests against
  main source report 4 failed and 24 passed: the unchanged logger calls
  `rr.Scalars`, which that SDK does not provide. This corrects the declared
  support range; no scalar compatibility port is included.
- Support Rerun SDK versions `>=0.23.4,<0.43` for recording and visualization.
  Keep direct RRD replay when the legacy dataframe API is available. Newer SDKs
  report their version, the RRD path, and recovery steps instead of dropping the
  reader API. RRD payload writing and the existing replay CLI default remain.
- Keep the legacy MCAP encoding by default. Add explicit opt-in lossless MCAP
  output through `RecordConfig(mcap_lossless=True)` or `MCAPWriter(lossless=True)`.
  The opt-in codec retains arrays, bytes, tuples and nested values. Older readers
  reject these opted-in files instead of misreading them. Continue reading old
  MCAP files; RRD encoding and mirror defaults do not change.
- Add recording checks for SDK 0.23.4 and 0.42.0. MCAP mirrors remain explicit;
  recording and replay never create or infer a sibling artifact.

## [0.0.1] — 2026-07-09

Initial public release of `retriever-core`: the Retriever programming model and
runtime — `Flow`, `Pipeline`, `@io` typed messages, clocks (`Rate` / `Trigger` /
`Hybrid`), sync policies (`Latest` / `Window` / …), IR + topology, the in-process
stepper plus multiprocessing and dora backends, record/replay, and the
`retriever` CLI. Imports as `retriever`.

[0.0.1]: https://pypi.org/project/retriever-core/0.0.1/
