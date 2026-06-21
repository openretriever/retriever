---
title: "Retriever Website Story"
---

# Retriever Website Story

This page is a public-safe copy bank for the Retriever website and blog. It should stay concise, non-private, and reusable outside the repository.

## Hero

**Retriever: closed-loop robot agents with explicit time**

Retriever is a programming framework for building robot systems whose perception, reasoning, and control can run together easily, even when every component has its own timing.

## One-Paragraph Summary

Modern robot systems are no longer one policy in one loop. A useful robot may combine cameras, state estimation, VLMs, VLAs, symbolic checks, memory, task planning, safety monitors, operators, low-level controllers, and replay logs. These pieces run at different rates and fail in different ways. Retriever turns that mess into an explicit typed graph: each module is a Flow, each Flow has a clock, and each edge declares how data is sampled before the next step runs.

## Problem Framing

Robotics code often starts simple and becomes a pile of callbacks, queues, timers, sleeps, and launch files. That works until the system has to answer basic questions:

- Which camera frame did the policy actually use?
- Did the planner run on fresh state or stale state?
- Can the same incident be replayed deterministically?
- Can a slow model and a fast controller coexist without ad hoc glue code?
- Can the same graph run locally during debugging and on a distributed runtime later?

Retriever makes those questions first-class in the program.

## Design Principles

1. **Composition first**: robot systems should be assembled from reusable components, not rewritten as one monolith.
2. **Time is explicit**: clocks and edge sampling policies are part of the graph, not hidden inside callbacks.
3. **Closed loops are normal**: the graph can be cyclic, so controllers, planners, monitors, and environments can influence each other.
4. **Debugging is a runtime feature**: the same graph can run in-process for breakpoints or on a backend for realistic execution.
5. **Typed boundaries scale collaboration**: shared payload types make components easier to test, publish, and reuse.
6. **Ecosystem beats one repo**: the core runtime should stay small while robot integrations, models, datasets, and examples grow as companion packages.

## Concept Ladder

### Flow

A Flow is a Python class with local state and a `step(...)` method. It is the unit of robot computation: camera reader, detector, planner, controller, monitor, logger, or policy wrapper.

### Clock

A clock says when a Flow runs. Some Flows run periodically. Some run when a new event arrives. Some combine both.

### Sync Policy

A sync policy says how an edge samples upstream data before a downstream Flow runs. This makes data handoff explicit and replayable.

### Pipeline

A Pipeline wires Flows into a graph, validates the graph, and runs it on a backend.

### IR

The IR is the backend-agnostic representation of the graph. It is the boundary between authoring and execution.

## Blog Angles

### 1. Why robots need explicit time

Start with the intuition that robot systems are multi-rate by default. Explain why callback timing, implicit latest-message behavior, and hidden queues make failures hard to debug. Introduce Retriever as a way to put timing into the graph.

### 2. From `env.step()` to closed-loop systems

A single `env.step(action)` loop is useful for learning, but deployed robot systems include perception, planning, memory, monitoring, operators, and logs. Retriever keeps the simplicity of step functions while allowing the graph to be cyclic and asynchronous at the system level.

### 3. A PyTorch-like module graph for robot runtime

Use the analogy carefully: PyTorch made model components composable; Retriever aims to make robot runtime components composable. The extra ingredient is explicit time.

### 4. Debugging robot incidents with replayable graphs

Show the difference between a backend run and in-process stepping. The key message: debugging should not require rewriting the system.

### 5. Building an ecosystem of robot components

Explain why adoption depends on more than the core software. A useful ecosystem needs clear docs, stable shared types, examples, publishing conventions, plugin surfaces, and companion packages.

## Website Section Outline

1. Hero: what Retriever is and who it helps.
2. Motivation: robot systems are multi-rate, partially observable, and closed-loop.
3. Core idea: Flow + Clock + Sync Policy + Pipeline.
4. Visual example: camera, VLA, controller, monitor, replay log.
5. Runtime: in-process debug, multiprocessing, dora backend.
6. Ecosystem: shared types, Hub, plugins, examples, companion packages.
7. Docs path: quickstart, handbook, tutorials, architecture.
8. License and contribution: Apache-2.0, small core, public-safe docs.

## Tone Guide

Use general-audience language first, then precise terms. Prefer "each module runs on its own schedule" before "local clocks". Prefer "how data crosses an edge" before "sync policy". Introduce formal names only after the reader understands the problem.
