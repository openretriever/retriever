---
title: "Tutorial Path"
---

# Tutorial Path

Retriever tutorials are organized as a guided path, not a registry of files. Start with the visual graph, learn the four objects, then move into debugging, replay, synchronization, and release evidence.

<div class="rt-learning-panel">
  <h2>Recommended first hour</h2>
  <ol>
    <li><code>pixi run demo-webcam-detection</code> — webcam color detection with Rerun/stdout visualization.</li>
    <li><code>pixi run demo-basic-flow</code> — learn the smallest Flow API.</li>
    <li><code>pixi run demo-rt-execution</code> — run through validation and runtime execution.</li>
    <li><code>pixi run demo-stepper</code> — debug the same model in-process.</li>
    <li><code>pixi run docs-tutorial-perception-html</code> — render the graph you are building.</li>
  </ol>
</div>

<figure class="rt-figure-card rt-figure-wide">
  <img src="../assets/figures/02_flow_sync.png" alt="Flow synchronization diagram." />
  <figcaption>The tutorial path keeps this mental model visible: Flows are synchronous Python objects; clocks and sync policies make multi-rate execution explicit.</figcaption>
</figure>

## Tracks

<div class="rt-doc-map rt-track-map">
  <a href="track_a_flow_fundamentals/"><strong>A. Flow Fundamentals</strong><span>Typed Flows, clocks, sync policies, and pipeline ergonomics.</span></a>
  <a href="track_b_ir_and_execution/"><strong>B. IR and Execution</strong><span>Validation, IR, visualization, execution graphs, and backend runs.</span></a>
  <a href="track_c_debug_and_replay/"><strong>C. Debug and Replay</strong><span>Stepper-first debugging, graph artifacts, traces, MCAP, and replay drills.</span></a>
  <a href="track_d_closed_loop_state_feedback/"><strong>D. Closed Loop State</strong><span>Stateful Flows, feedback, authority, and replanning.</span></a>
  <a href="track_e_resource_and_sync/"><strong>E. Resource and Sync</strong><span>Multi-rate streams, synchronization, fan-in/fan-out, and joins.</span></a>
  <a href="track_f_policy_backends/"><strong>F. Policy Backends</strong><span>Swap model/policy backends behind one graph contract.</span></a>
  <a href="track_g_operations_interfaces/"><strong>G. Operations Interfaces</strong><span>Registries, composition, typed boundaries, and integration surfaces.</span></a>
  <a href="track_h_release_readiness/"><strong>H. Evidence and Manifests</strong><span>Run manifests, datasets, and acceptance evidence.</span></a>
</div>

## How To Choose

| If you want to... | Start with |
| --- | --- |
| Learn the programming model from scratch | [Track A: Flow Fundamentals](track_a_flow_fundamentals.md) |
| Inspect or visualize a graph | [Track B: IR and Execution](track_b_ir_and_execution.md) |
| Debug a failing robot run | [Track C: Debug and Replay](track_c_debug_and_replay.md) |
| Build feedback/stateful behavior | [Track D: Closed Loop State](track_d_closed_loop_state_feedback.md) |
| Handle multi-rate data handoff | [Track E: Resource and Sync](track_e_resource_and_sync.md) |
| Abstract over a policy/model backend | [Track F: Policy Backends](track_f_policy_backends.md) |
| Publish reusable components | [Track G: Operations Interfaces](track_g_operations_interfaces.md) |
| Capture run evidence and dataset lineage | [Track H: Evidence and Manifests](track_h_release_readiness.md) |

## Deep Dives

- [Integrated Tutorial: Debug to Release](tutorial_integrated_debug_to_release.md)
- [Stepper, Debugger, and MCAP Replay](walkthrough_stepper_debug_and_replay.md)
- [Core Release Path](walkthrough_core_release_path.md)
- [Lecture Packs L01-L11](lectures/index.md)
