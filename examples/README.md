# Retriever Canonical Examples

This directory contains examples demonstrating the core capabilities of Retriever. Here are the **Canonical Examples** recommended for new users to try.

## 🚀 Quick Start

### 1. Interactive Vision
Real-time object detection with a web-based control flow. Adjust thresholds and visualize bounding boxes dynamically.
```bash
pixi run -e torch demo-vision
```
*Source: `examples/advanced/interactive_detection/`*

### 2. Mujoco Robotics Simulation
A closed-loop robot arm simulation (physics @ 200Hz, control @ 50Hz) visualized in **Rerun**. Perfect for testing robotics logic without hardware.
```bash
pixi run demo-mujoco
```
*Source: `examples/advanced/mujoco_manipulation/`*

### 3. Real-Time Detection & Replay
Two Powerful Rerun Demos:
1.  **Real-Time Detection**: Run OwlViT (Open Vocabulary Detection) + SAM (Segmentation) on a live webcam stream, visualized in Rerun.
    ```bash
    pixi run -e torch demo-webcam-rerun
    # Tip: Use queries like "person", "cup", "keyboard"
    ```
2.  **Record & Replay**: Record streams to `.mcap` and replay them with code-level debugging.
    ```bash
    python examples/advanced/webcam_rerun/record_replay.py replay
    ```
*Source: `examples/advanced/webcam_rerun/`*

---

## 📚 Tutorials

Check `examples/tutorial/` for step-by-step introductions to Flow, Runtime, and Scheduling.

---

## 📖 Full Demo Catalog

A comprehensive list of advanced canonical examples. Run these from the project root.

### 🚀 Vision & Perception

| Name | Command | Environment | Description |
|------|---------|-------------|-------------|
| **Interactive Vision** | `pixi run -e torch demo-vision` | `torch` | Real-time object detection with a web-based control flow (FastAPI + React). Adjust thresholds dynamically. |
| **Webcam Rerun** | `pixi run -e torch demo-webcam-rerun` | `torch` | **(Recommended)** OwlViT detection + SAM segmentation on live webcam, visualized in **Rerun**. |
| **VLA Inference** | `pixi run -e torch demo-vla` | `torch` | Efficient inference of VLA (Vision-Language-Action) models using `openpi`. |

### 🤖 Robotics & Simulation

| Name | Command | Environment | Description |
|------|---------|-------------|-------------|
| **Mujoco Manipulation** | `pixi run demo-mujoco` | `default` | Closed-loop robot arm simulation (Franka Emika) performing a pick-and-place task. Visualized in Rerun. |
| **Hierarchical VLA** | `pixi run -e torch demo-hierarchical-vla` | `torch` | Hierarchical planning: VLM (high-level planner) + VLA (low-level controller). |
| **Twist2 Simulation** | `pixi run -e twist2 demo-twist2` | `twist2` | Massive parallel simulation example using Twist2. |
| **Code as Policies** | `pixi run -e code-policies demo-code-policies` | `code-policies` | LLM generates Python code to solve robotic tasks (Ravens benchmark). |

### 🧠 LLM & Agents

| Name | Command | Environment | Description |
|------|---------|-------------|-------------|
| **VLM Gridworld** | `pixi run -e llm demo-vlm-gridworld` | `llm` | A VLM-based agent navigates a gridworld by "seeing" the map. |
| **LLM Streaming** | `pixi run -e llm demo-llm-streaming` | `llm` | LLM plays "20 Questions" with streaming responses via the runtime. |

### ⚙️ Core Runtime Features

| Name | Command | Environment | Description |
|------|---------|-------------|-------------|
| **Skill Switching** | `pixi run demo-skill-switching` | `default` | Demonstrates a "Router" pattern to switch between skills (Navigation vs Manipulation) without a behavior tree. |
| **Multirate Fusion** | `pixi run -e torch demo-multirate-fusion` | `torch` | Async sensor fusion: 100Hz proprioception + 10Hz heavy vision processing. |
| **Remote Connection** | `pixi run demo-remote` | `default` | Distributing a pipeline across multiple machines/processes using `deploy()`. |
| **Rerun Step Debug** | `pixi run demo-rerun-debug` | `default` | Step-by-step debugging walkthrough integrating Rerun for state inspection. |

### 🏎️ Performance

| Name | Command | Environment | Description |
|------|---------|-------------|-------------|
| **Binding Benchmark** | `pixi run -e bindings binding-benchmark` | `bindings` | Benchmark comparing Python, Rust, and C++ controller implementations. |
