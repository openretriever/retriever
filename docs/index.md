---
title: "Overview"
slug: "intro"
---

<div class="rt-hero">
  <img src="assets/retriever-illustrative.jpeg" alt="Retriever logo" class="rt-hero-logo" />
  <p class="rt-eyebrow">OpenRetriever runtime docs</p>
  <h1>Build robot agents with explicit time.</h1>
  <p class="rt-lede">Retriever is a Python framework for closed-loop robot systems whose perception, reasoning, and control run together at different rates.</p>
  <div class="rt-action-grid">
    <a class="rt-action-card" href="/quickstart/">
      <span class="rt-action-icon">▶</span>
      <strong>Get started</strong>
      <small>Run the first graph and learn the mental model.</small>
    </a>
    <a class="rt-action-card" href="/getting_started/install/">
      <span class="rt-action-icon">↓</span>
      <strong>Install Retriever</strong>
      <small>Pixi, pip/uv, backend, and camera setup.</small>
    </a>
    <a class="rt-action-card" href="/examples/">
      <span class="rt-action-icon">▣</span>
      <strong>Example gallery</strong>
      <small>Core tutorials first, Golden examples next.</small>
    </a>
  </div>
</div>

Robots do not usually fit into one clean loop. Cameras stream, robot state updates faster than policies, VLM/VLA calls have variable latency, planners can block, operators intervene, and logs must be replayable. Retriever makes those timing and handoff decisions part of the program instead of hiding them in callbacks, queues, and sleeps.

## Learn Retriever In Order

<div class="rt-path-grid">
  <a class="rt-path-step" href="/quickstart/">
    <span>01</span>
    <strong>Run one graph</strong>
    <p>Start with the webcam demo or the smallest pure-Python flow.</p>
    <code>pixi run demo-webcam-detection</code>
  </a>
  <a class="rt-path-step" href="/guide_flow/">
    <span>02</span>
    <strong>Understand the objects</strong>
    <p>Learn the four building blocks: Flow, Clock, Sync Policy, and Pipeline.</p>
    <code>Flow @ Rate → Pipeline.connect</code>
  </a>
  <a class="rt-path-step" href="/tutorials/">
    <span>03</span>
    <strong>Debug before backends</strong>
    <p>Use the in-process stepper before multiprocessing or dora execution.</p>
    <code>pipe.step(dt=0.1)</code>
  </a>
  <a class="rt-path-step" href="/examples/">
    <span>04</span>
    <strong>Move toward robots</strong>
    <p>Record/replay data, connect perception examples, then continue in GoldenRetriever.</p>
    <code>pixi run demo-webcam-record</code>
  </a>
</div>

## The Core Model

<div class="rt-concept-grid">
  <a class="rt-concept-card" href="/guide_flow/">
    <h3>Flow</h3>
    <p>A typed Python class with a <code>step(...)</code> method and local state. It is the unit of robot computation.</p>
  </a>
  <a class="rt-concept-card" href="/guide_temporal/">
    <h3>Clock</h3>
    <p>Each Flow declares when it runs. There is no global robot timestep across the graph.</p>
  </a>
  <a class="rt-concept-card" href="/guide_temporal/">
    <h3>Sync Policy</h3>
    <p>Each edge declares how upstream events are sampled before the downstream Flow runs.</p>
  </a>
  <a class="rt-concept-card" href="/guide_runtime/">
    <h3>Pipeline</h3>
    <p>The graph surface that validates typed connections, builds IR, and runs on execution backends.</p>
  </a>
</div>

## First Commands

=== "Visual path"

    ```bash
    pixi run demo-webcam-detection
    pixi run demo-webcam-stepper
    pixi run demo-webcam-record
    ```

=== "Core API path"

    ```bash
    pixi run demo-basic-flow
    pixi run demo-adapter-connection
    pixi run demo-rt-execution
    pixi run demo-stepper
    ```

=== "Advanced examples"

    ```bash
    pixi run demo-data-multistream-join
    pixi run demo-language-grounding
    # Then continue in GoldenRetriever for perception, memory, language, and robotics examples.
    ```

## Why This Matters

A robot stack becomes hard to maintain when timing is implicit. A callback grabs the latest camera frame, a thread caches a model output, a controller silently holds an old command, and a replay no longer matches the original run. Retriever puts those decisions in the graph so the same system can be inspected, stepped, replayed, and moved across execution backends.

## Documentation Map

<div class="rt-doc-map">
  <a href="/quickstart/"><strong>Quickstart</strong><span>Shortest runnable introduction.</span></a>
  <a href="/handbook/"><strong>Handbook</strong><span>Canonical runtime guide.</span></a>
  <a href="/tutorials/"><strong>Tutorial Tracks</strong><span>Step-by-step curriculum.</span></a>
  <a href="/architecture/"><strong>Architecture</strong><span>Runtime layers and boundaries.</span></a>
  <a href="/hub/"><strong>Hub</strong><span>Reusable module patterns.</span></a>
  <a href="/API/"><strong>API Reference</strong><span>Public surface map.</span></a>
</div>
