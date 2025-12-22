# Retriever Canonical Examples

This directory contains examples demonstrating the core capabilities of Retriever. Here are the **Canonical Examples** recommended for new users to try.

## 🚀 Quick Start (The "Wow" Demos)

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

### 3. Webcam Recording & Replay (New!)
Record a webcam stream to an `.mcap` file and replay it with full code-level debugging support. Visualized in **Rerun**.
```bash
# Live Record + View
pixi run -e torch demo-webcam-rerun

# Replay for Debugging
python examples/advanced/webcam_rerun/record_replay.py replay
```
*Source: `examples/advanced/webcam_rerun/`*

---

## 🏎️ Performance & Architecture

### 4. Native Acceleration (Rust/C++)
Compare Python controller performance against native Rust/C++ implementations using the `retriever` binding interface.
```bash
# Rust Controller
pixi run -e rust binding-controller-rust
```
*Source: `examples/advanced/native_controller/`*

---

## 🧠 Advanced Logic

### 5. Skill Switching
Demonstrates a complex "Router" pattern for switching between different robot skills (Navigation vs Manipulation) based on state, effectively replacing a behavior tree.
```bash
pixi run demo-skill-switching
```
*Source: `examples/advanced/skill_switching/`*

### 6. VLA Inference (OpenPI)
Demonstrates Vision-Language-Action model inference optimization using `openpi` and the `pi0.5` model.
```bash
pixi run -e torch demo-vla
```
*Source: `examples/advanced/vla_inference_optim/`*

---

## 📚 Tutorials

Check `examples/tutorial/` for step-by-step introductions to Flow, Runtime, and Scheduling.
