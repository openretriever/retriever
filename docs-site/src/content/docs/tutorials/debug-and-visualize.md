---
title: Debug and Visualize
---

# Debug and Visualize

Retriever should be easy to inspect before you run a robot backend.

## Render a graph

```bash
pixi run docs-tutorial-perception-html
```

This writes an HTML artifact with nodes, ports, clocks, and sync policies.

## Step locally

```bash
pixi run demo-stepper
pixi run demo-perception-stepper
```

The stepper path is useful because it keeps debugging inside ordinary Python.

## Record and replay

```bash
pixi run demo-webcam-record
pixi run demo-webcam-replay-rrd
```

A recorded run gives you a stable artifact for debugging, regression tests, and sharing evidence.
