---
title: "Tutorial Tracks"
---

# Tutorial Tracks

Retriever tutorials are organized as a learning path, not a dump of examples. Run the first lane end-to-end, then branch into the track that matches what you are building.

<div class="rt-learning-panel">
  <h2>Recommended first hour</h2>
  <ol>
    <li><code>pixi run demo-webcam-detection</code> — see a real timed graph.</li>
    <li><code>pixi run demo-basic-flow</code> — learn the smallest API.</li>
    <li><code>pixi run demo-rt-execution</code> — run through the runtime path.</li>
    <li><code>pixi run demo-stepper</code> — debug the same model in-process.</li>
    <li><code>pixi run demo-webcam-record</code> — record and replay an observed run.</li>
  </ol>
</div>

## Tracks

<div class="rt-doc-map rt-track-map">
  <a href="track_a_flow_fundamentals/"><strong>A. Flow Fundamentals</strong><span>Typed flows, clocks, adapters, and pipeline ergonomics.</span></a>
  <a href="track_b_ir_and_execution/"><strong>B. IR and Execution</strong><span>Validation, IR, execution graphs, and backend runs.</span></a>
  <a href="track_c_debug_and_replay/"><strong>C. Debug and Replay</strong><span>Stepper-first debugging, traces, MCAP, and replay drills.</span></a>
  <a href="track_d_closed_loop_state_feedback/"><strong>D. Closed Loop State</strong><span>Stateful flows, feedback, authority, and replanning.</span></a>
  <a href="track_e_resource_and_sync/"><strong>E. Resource and Sync</strong><span>Multi-rate streams, synchronization, fan-in/fan-out, and joins.</span></a>
  <a href="track_f_policy_backends/"><strong>F. Policy Backends</strong><span>Swapping policy backends behind one graph contract.</span></a>
  <a href="track_g_operations_interfaces/"><strong>G. Operations Interfaces</strong><span>Registries, composition, typed boundaries, and integration surfaces.</span></a>
  <a href="track_h_release_readiness/"><strong>H. Release Readiness</strong><span>Manifests, evidence, datasets, and acceptance gates.</span></a>
</div>

## How To Choose

| If you want to... | Start with |
| --- | --- |
| Learn the programming model from scratch | [Track A: Flow Fundamentals](track_a_flow_fundamentals.md) |
| Run the same graph on a backend | [Track B: IR and Execution](track_b_ir_and_execution.md) |
| Debug a failing robot run | [Track C: Debug and Replay](track_c_debug_and_replay.md) |
| Build feedback/stateful behavior | [Track D: Closed Loop State](track_d_closed_loop_state_feedback.md) |
| Handle multi-rate data handoff | [Track E: Resource and Sync](track_e_resource_and_sync.md) |
| Abstract over a policy/model backend | [Track F: Policy Backends](track_f_policy_backends.md) |
| Publish reusable components | [Track G: Operations Interfaces](track_g_operations_interfaces.md) |
| Prepare a public release | [Track H: Release Readiness](track_h_release_readiness.md) |

## Deep Dives

- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)
- [Stepper, Debugger, and MCAP Replay](walkthrough_stepper_debug_and_replay.md)
- [Core Release Path](walkthrough_core_release_path.md)
- [Lecture Packs L01-L11](lectures/index.md)
