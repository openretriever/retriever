---
title: "Track F: Policy Backends"
---

# Track F: Policy Backends

Focus: one graph contract with multiple policy implementations.

This is a specialized track. It makes more sense after the basics in Tracks D and G are already clear.

## Module

```bash
pixi run python -m examples.tutorial.f_policy_backends.01_closed_loop_policy_backend_abstraction
```

## What To Observe

- Graph topology remains unchanged while the policy implementation changes.
- Backend-specific latency and chunking differences live behind one typed boundary.
