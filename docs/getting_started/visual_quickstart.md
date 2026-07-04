---
title: "Visual Quickstart"
---

# Visual Quickstart: Webcam Color Detection

Start here if you want to see Retriever do something immediately. First run the deterministic mock-frame smoke; then switch to the live webcam path with Rerun when available.

<div class="rt-command-grid rt-command-grid-single">
  <div class="rt-command-card"><span>Start here</span><strong>Mock camera → color detector → stdout</strong><small>Reliable first smoke for laptops, headless machines, and CI.</small><code>pixi run demo-webcam-detection-mock</code></div>
  <div class="rt-command-card"><span>Then go live</span><strong>Webcam → color detector → Rerun</strong><small>Show a red or blue object to the camera. Rerun opens a live viewer when the SDK is installed; otherwise the demo falls back to stdout.</small><code>pixi run demo-webcam-detection</code></div>
</div>

## What You Should See

- The mock command prints detector events to stdout.
- A camera Flow publishes frames at its own rate.
- A color detector Flow runs when frames arrive and emits bounding boxes for red/blue regions.
- A display/visualization path shows detections live in Rerun when available.
- If you specifically want mock frames with Rerun, run:

```bash
pixi run demo-webcam-detection-mock
pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception --backend in-process --camera-mode mock --visualize rerun --duration 10
```

## Why This Is The First Demo

The color-detection path is small but representative: it has sensor input, typed Flow outputs, asynchronous timing, visualization, and an immediate debugging story. The mock run proves the graph without hardware; the webcam run proves the live visual path. After this works, the same graph can be stepped, inspected, recorded, replayed, and moved to a backend.

## Rerun Visualization

Retriever uses Rerun as the lightweight live viewer for visual demos and as the native `.rrd` inspection path for recorded sessions.

| Use case | Command |
| --- | --- |
| Deterministic first smoke | `pixi run demo-webcam-detection-mock` |
| Live webcam with automatic Rerun/stdout fallback | `pixi run demo-webcam-detection` |
| Force live Rerun on multiprocessing backend | `pixi run demo-webcam-detection-mp-rerun` |
| Force mock frames with Rerun | `pixi run python -m examples.tutorial.b_ir_and_execution.06_dora_perception --backend in-process --camera-mode mock --visualize rerun --duration 10` |
| Record a portable perception replay | `pixi run demo-webcam-record` |

If Rerun cannot open a viewer on your machine, use `--visualize stdout` to keep the tutorial path running without a GUI.

## Continue

<div class="rt-doc-map">
  <a href="/quickstart/"><strong>Learn the API</strong><span>Define a tiny Flow graph and step it locally.</span></a>
  <a href="/tutorials/track_b_ir_and_execution/"><strong>Inspect the graph</strong><span>Generate IR and HTML graph artifacts.</span></a>
  <a href="/tutorials/track_c_debug_and_replay/"><strong>Debug and replay</strong><span>Use the stepper and record/replay workflow.</span></a>
  <a href="/guide_temporal/"><strong>Understand time</strong><span>Clocks, event streams, sync policies, and buffers.</span></a>
</div>
