<div align="center">

<a href="https://openretriever.org/"><img width="200" height="auto" src="assets/retriever-illustrative.jpeg" alt="Retriever logo"></a>

<br>

<a href="https://openretriever.org/"><img src="assets/retriever-wordmark.svg" alt="Retriever" width="300"></a>

### Programming Closed-Loop Modular Robot Agents

<p>A Python programming model and runtime for robot agents whose perception, planning, and control run at different rates. You write down how often each part runs and how it handles data that arrives out of sync, so the timing lives in the graph instead of in hand-written glue code — and recorded input traces can be replayed through the same graph.</p>

<p>
  <a href="https://retriever.build/"><img alt="Docs" src="https://img.shields.io/badge/Docs-retriever.build-0f766e?style=for-the-badge"></a>
  <a href="https://openretriever.org/"><img alt="Website" src="https://img.shields.io/badge/Website-openretriever.org-111827?style=for-the-badge"></a>
  <a href="https://discord.gg/V79H7TwwNg"><img alt="Discord" src="https://img.shields.io/badge/Discord-join-5865F2?style=for-the-badge&logo=discord&logoColor=white"></a>
  <br>
  <a href="https://golden.retriever.build/examples/"><img alt="GoldenRetriever examples" src="https://img.shields.io/badge/GoldenRetriever-examples-f97316?style=for-the-badge"></a>
  <a href="https://retriever.build/ecosystem/"><img alt="Hub packs" src="https://img.shields.io/badge/Retriever_Hub-packs-9333ea?style=for-the-badge"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-3b82f6?style=for-the-badge"></a>
</p>

</div>

---

Robot systems rarely run as one neat synchronous loop: cameras, estimators, planners, VLMs, VLAs, and controllers all update at different rates. **Retriever** lets you declare how often each `Flow` runs and how each edge samples data — so the timing lives in the graph, not in glue code. Step the graph in-process to debug it, then run the same graph on a backend; record the consumed input trace when you need an exact replay.

## See it run

One line, on any laptop with a webcam:

```bash
pip install "retriever-core[demo]" rerun-sdk
retriever demo webcam --visualize rerun
```

This pulls the [`openretriever/webcam-demo`](https://github.com/openretriever/webcam-demo) Hub pack (no clone) and drives a live `Camera → ColorDetector → Rerun` closed loop with bounding-box overlays. Full walkthrough: **[retriever.build](https://retriever.build/)**.

## Install

```bash
python -m pip install retriever-core     # runtime + `retriever` CLI; imports as `retriever`
```

Python 3.11+. For the bundled demos, renderers, and tests, use a source checkout: `git clone https://github.com/openretriever/retriever && cd retriever && retriever install`.

## Quickstart

```python
from retriever import Flow, Latest, Pipeline, Rate, Trigger, io


@io
class Number:
    value: int


@io
class Doubled:
    value: int


class Source(Flow[None, Number]):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def step(self, _):
        self.count += 1
        return Number(value=self.count)


class Double(Flow[Number, Doubled]):
    def step(self, input: Number) -> Doubled:
        return Doubled(value=input.value * 2)


pipe = Pipeline("quickstart")
with pipe:
    source = Source() @ Rate(hz=2)          # runs at 2 Hz
    double = Double() @ Trigger("value")    # wakes on each Number
    source.then(double, sync=Latest())      # edge samples the latest value

pipe.run(backend="multiprocessing", duration=1.0)   # deploy
# result = pipe.step(dt=0.1)                         # ...or step in-process to debug + replay
```

`@io` typed message · `Flow[I, O]` node logic · `flow @ clock` when it runs · `.then(…, sync=…)` how the edge samples · `pipe.run()` to deploy, `pipe.step()` to debug and replay.

## Learn more

| Guide | What's there |
| --- | --- |
| **[Docs home](https://retriever.build/)** | install, visual quickstart, tutorials |
| **[Concepts](https://retriever.build/concepts/)** | Flow, clocks, sync policies, IR, record/replay |
| **[Retriever Hub](https://retriever.build/ecosystem/)** | load packs by name from any repo — no clone |
| **[GoldenRetriever](https://golden.retriever.build/examples/)** | applied robot examples: perception, memory, language, sim |
| **[Discord](https://discord.gg/V79H7TwwNg)** | questions, help, and community |

<details>
<summary><b>In-process stepping, record &amp; replay</b></summary>

Retriever has two execution modes on purpose. Backend execution is for realistic scheduling and deployment; in-process stepping is for debugging logic, replaying incidents, and making timing bugs inspectable with normal Python tools.

```python
# Backend execution — realistic scheduling, process boundaries, deployment
pipe.run(backend="multiprocessing", duration=3.0)
pipe.run(backend="dora", duration=3.0)

# In-process debugging — step the graph, inspect, checkpoint, replay
result = pipe.step(dt=0.1)
print(result.executed)
pipe.close_stepper()
```

Given the same ordered timestamped input history — including a fixed order for equal timestamps — deterministic Flows produce the same discrete-event output trace. Live backend timing decides which history is captured; replay drives the graph from that captured history. See [Runtime](https://retriever.build/concepts/runtime/) for the precise contract and [Debug and Visualize](https://retriever.build/tutorials/debug-and-visualize/) for the workflow.

</details>

<details>
<summary><b>Ecosystem boundary</b></summary>

- **Core runtime** — this repo, published as `retriever-core`, imported as `retriever`. Stays focused on the runtime.
- **[GoldenRetriever](https://golden.retriever.build/examples/)** — the applied examples + Hub-pack layer (robot payloads, simulator/visualization lanes). Built on the runtime, not a second one.
- **Retriever Hub** — the manifest + index protocol that turns any repo into a loadable pack of Flows, types, and pipelines.
- **[openretriever.org](https://openretriever.org/)** — the project home.

</details>

<details>
<summary><b>Contributing &amp; development</b></summary>

Contributor tasks run through the same `retriever` command from a source checkout:

```bash
retriever install                     # set up the environment
retriever run test                    # full test suite
retriever run p0-release-readiness
retriever run public-surface-check    # external launch check
```

The source checkout uses [Pixi](https://pixi.sh) as its environment/task backend, and `retriever run <task>` wraps it. `main` is canonical — a fresh clone and ordinary `git pull` fast-forward. See [docs/contributing.md](docs/contributing.md).

</details>

## Community &amp; license

Questions and help: **[Discord](https://discord.gg/V79H7TwwNg)**. Licensed under Apache-2.0 — see [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
