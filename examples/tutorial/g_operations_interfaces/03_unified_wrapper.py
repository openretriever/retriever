"""
Unified Wrapper Tutorial (Simplified)
=====================================
Demonstrates the High-Level API without boilerplate:
1. `Wrapper` Factory Class for Gym and Torch.
2. `retriever.connect` (Implicit Default Pipeline).
3. `retriever.run` (Global Execution).

API Design:
- Wrappers: Create Flows from objects.
- Connect: Declarative wiring.
- Run: Execute the default pipeline.

Run:
    pixi run python examples/tutorial/g_operations_interfaces/03_unified_wrapper.py
"""

import argparse
import logging
import gymnasium as gym
import torch
import torch.nn as nn

# Standard imports (assuming retriever is installed)
import retriever
from retriever.flow import Rate
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
    parser.add_argument("--backend", default="dora", choices=["dora", "multiprocessing"])
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
    # B. CONNECT (IMPLICIT DEFAULT PIPELINE)
    # ------------------------------------------------------------------------
    # No `with Pipeline()` needed!
    retriever.connect(env, agent, map={"obs": "inp"})
    retriever.connect(agent, env, map={"inp": "action"})
        
    # ------------------------------------------------------------------------
    # C. RUN (GLOBAL)
    # ------------------------------------------------------------------------
    print("Starting Unified Wrapper Demo (Global Run)...")
    try:
        retriever.run(backend=args.backend, duration=args.duration)
    except KeyboardInterrupt:
        pass
        
    # ------------------------------------------------------------------------
    # D. MANUAL STEPPING (INTERACTIVE DEBUGGING)
    # ------------------------------------------------------------------------
    # 'step()' runs the graph in the CURRENT process (simulating parallelism).
    # It is independent of the 'backend' used in 'run()'.
    
    print("\nResetting for Manual Stepping Demo...")
    retriever.reset()
    
    print("Stepping manually for 5 steps...")
    for i in range(5):
        retriever.step(dt=0.1)
        print(f"  Step {i+1} complete.")


if __name__ == "__main__":
    main()
