
import logging
import pickle
import codecs
from typing import Any, Type, Optional, Union, Callable

try:
    import gymnasium as gym
except ImportError:
    try:
        import gym
    except ImportError:
        gym = None

from retriever.flow import Flow, io

logger = logging.getLogger(__name__)

@io
class GymIO:
    action: Any
    
@io
class GymObservation:
    obs: Any
    reward: float
    terminated: bool
    truncated: bool
    info: dict

class GymEnvFlow(Flow[GymIO, GymObservation]):
    """
    Top-level Flow class for wrapping Gym environments.
    """
    def __init__(self, env_spec: Any = None, _pickled_spec: Optional[str] = None):
        self._env_spec = env_spec
        
        if env_spec is None and _pickled_spec is not None:
             self._env_spec = pickle.loads(codecs.decode(_pickled_spec.encode(), "base64"))
             
    def init_config(self) -> dict:
        if self._env_spec is None:
            return {}
        pickled = codecs.encode(pickle.dumps(self._env_spec), "base64").decode()
        return {"_pickled_spec": pickled}

    def init(self):
        env_spec = self._env_spec
        self.env = None
        self.env_name = "Unknown"
        
        if env_spec is None:
             raise RuntimeError("GymEnvFlow has no env_spec properly initialized.")

        # Create Env (No Strings allowed here, checked in factory)
        if callable(env_spec) and not isinstance(env_spec, type):
             # Factory
            self.env = env_spec()
            self.env_name = "CustomFactoryEnv"
        else:
            # Instance
            self.env = env_spec
            self.env_name = getattr(env_spec, "unwrapped", env_spec).__class__.__name__

        logger.info(f"[{self.env_name}] Gym Wrapper initialized")
        self._obs, _ = self.env.reset()

    def run(self, input_data: GymIO) -> Optional[GymObservation]:
        if input_data.action is None:
            return None
            
        obs, reward, term, trunc, info = self.env.step(input_data.action)
        
        if term or trunc:
            obs, _ = self.env.reset()
            
        return GymObservation(
            obs=obs,
            reward=float(reward),
            terminated=term,
            truncated=trunc,
            info=info
        )

def from_gym(env_spec: Union[Any, Callable[[], Any]]) -> Flow[GymIO, GymObservation]:
    """
    Creates a Flow INSTANCE that wraps a Gym Environment.
    """
    if gym is None:
        raise ImportError("gym/gymnasium not installed. Cannot use from_gym.")
    
    if isinstance(env_spec, str):
        raise TypeError(
            f"from_gym(str) is not supported. Use from_gym(gym.make('{env_spec}')) or lambda."
        )
        
    return GymEnvFlow(env_spec=env_spec)
