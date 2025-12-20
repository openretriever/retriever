
from typing import Any, Callable, Union

class Wrapper:
    """
    Unified Factory for creating Flows from existing objects.
    
    Usage:
        flow = Wrapper(MyModule())
        flow = Wrapper(gym.make("CartPole-v1"))
        flow = Wrapper(lambda: gym.make("CartPole-v1"))
    """
    def __new__(cls, obj: Any, **kwargs) -> Any:
        # 1. Check for PyTorch Module
        is_torch = False
        try:
            import torch.nn as nn
            if isinstance(obj, nn.Module):
                is_torch = True
        except ImportError:
            pass
            
        if is_torch:
            from retriever.lib.torch import from_torch
            return from_torch(obj)
            
        # 2. Check for Gym (Env instance or Callable)
        is_gym = False
        
        # STRICT: Dictate that string is NOT allowed 
        if isinstance(obj, str):
            raise TypeError(
                f"Wrapper(str) is not supported to avoid ambiguity. "
                f"Please use `Wrapper(gym.make('{obj}'))` or `Wrapper(lambda: gym.make('{obj}'))`."
            )
            
        if callable(obj) and not isinstance(obj, type):
            # Factory function likely
            is_gym = True
        elif hasattr(obj, "step") and hasattr(obj, "reset"):
            # Duck typing for Env
            is_gym = True
            
        if is_gym:
            from retriever.lib.gym import from_gym
            return from_gym(obj)
            
        raise ValueError(
            f"Wrapper could not identify type of {type(obj)}. "
            f"Supported: nn.Module, gym.Env, Callable[[], gym.Env]."
        )
