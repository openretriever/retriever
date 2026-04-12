"""
Unified Wrapper Tutorial (Simplified)
=====================================
Demonstrates lightweight wrapping without hiding the pipeline surface:
1. `Wrapper` turns Gym/Torch objects into `Flow`s.
2. `Pipeline.connect(..., sync=Latest())` keeps graph construction explicit.
3. `pipe.run(...)`, `pipe.reset_stepper()`, and `pipe.step(...)` stay the
   primary execution/debugging surface.

API Design:
- Wrappers: Create Flows from objects.
- Connect: Declarative wiring on an explicit pipeline.
- Run: Execute or step that pipeline directly.

Run:
    pixi run python -m examples.tutorial.g_operations_interfaces.03_unified_wrapper

Dependencies:
    This tutorial requires `gymnasium` and `torch`, which are not part of the
    lightweight default demo surface.
"""

import argparse
import logging

import gymnasium as gym
import torch
import torch.nn as nn

# Standard imports (assuming retriever is installed)
from retriever.flow import Latest, Pipeline, Rate
from retriever.lib import Wrapper

logging.basicConfig(level=logging.INFO)

# ============================================================================
# 1. DEFINE A SIMPLE MODULE
# ============================================================================
class LinearPolicy(nn.Module):
    def __init__(self):
        super().__init__()
        # CartPole Obs=4, Action=2 (Discrete)
        self.net = nn.Linear(4, 2)
        
    def forward(self, obs):
        logits = self.net(obs)
        action = torch.argmax(logits, dim=-1)
        return action.item()

# ============================================================================
# 2. HELPER FACTORY
# ============================================================================
# Factory function must be picklable (top-level) for multiprocessing/dora
def make_env():
    return gym.make("CartPole-v1")

# ============================================================================
# 3. MAIN SCRIPT
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="multiprocessing", choices=["dora", "multiprocessing"])
    parser.add_argument("--duration", type=float, default=5.0)
    args = parser.parse_args()
    
    # ------------------------------------------------------------------------
    # A. WRAP OBJECTS
    # ------------------------------------------------------------------------
    print("Creating wrapped flows...")
    
    # Gym: Wrapper(Factory Function)
    env = Wrapper(make_env) @ Rate(30)
    
    # Torch: Wrapper(Instance)
    agent = Wrapper(LinearPolicy()) @ Rate(30)
    
    # ------------------------------------------------------------------------
    # B. CONNECT (EXPLICIT PIPELINE)
    # ------------------------------------------------------------------------
    pipe = Pipeline("unified_wrapper_demo")
    pipe.connect(env, agent, map={"obs": "inp"}, sync=Latest())
    pipe.connect(agent, env, map={"inp": "action"}, sync=Latest())
        
    # ------------------------------------------------------------------------
    # C. RUN (GLOBAL)
    # ------------------------------------------------------------------------
    print("Starting Unified Wrapper Demo...")
    try:
        pipe.run(backend=args.backend, duration=args.duration)
    except KeyboardInterrupt:
        pass
        
    # ------------------------------------------------------------------------
    # D. MANUAL STEPPING (INTERACTIVE DEBUGGING)
    # ------------------------------------------------------------------------
    # `Pipeline.step()` runs the graph in the current process, independent of the
    # worker backend used by `run()`.

    print("\nResetting for Manual Stepping Demo...")
    pipe.reset_stepper()

    print("Stepping manually for 5 steps...")
    for i in range(5):
        pipe.step(dt=0.1)
        print(f"  Step {i+1} complete.")


if __name__ == "__main__":
    main()
