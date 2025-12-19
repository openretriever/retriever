"""
Flow base class for declarative dataflow computation.

A Flow is a signal function that transforms inputs to outputs.
"""

from abc import ABC, abstractmethod
from typing import get_origin, get_args
from typing import TypeVar, Generic, Optional, Type
from retriever.error import FlowError, ErrCode

I = TypeVar('I')
O = TypeVar('O')


class Flow(ABC, Generic[I, O]):
    """
    Abstract base class for flows.

    A Flow transforms inputs of type I to outputs of type O.
    I and O must be @flow_io decorated dataclasses.
    """

    _input_type: Optional[Type] = None
    _output_type: Optional[Type] = None

    def __init_subclass__(cls, **kwargs):
        """Extract type parameters from Flow[I, O] at class definition time."""
        super().__init_subclass__(**kwargs)

        if hasattr(cls, '__orig_bases__'):
            for base in cls.__orig_bases__:
                if get_origin(base) is Flow:
                    args = get_args(base)
                    if len(args) >= 2:
                        # Only use concrete types
                        input_type = args[0] if not isinstance(args[0], TypeVar) else None
                        output_type = args[1] if not isinstance(args[1], TypeVar) else None

                        # Normalize type(None) to None
                        cls._input_type = None if input_type is type(None) else input_type
                        cls._output_type = None if output_type is type(None) else output_type

                        # Validate types are @flow_io decorated
                        from retriever.flow.io import is_flow_io

                        if input_type and input_type is not type(None) and not is_flow_io(input_type):
                            raise FlowError(
                                ErrCode.FLOW_TYPE_NOT_COMPATIBLE,
                                f"Flow input type must use @flow_io decorator, got {input_type}",
                            )

                        if output_type and output_type is not type(None) and not is_flow_io(output_type):
                            raise FlowError(
                                ErrCode.FLOW_TYPE_NOT_COMPATIBLE,
                                f"Flow output type must use @flow_io decorator, got {output_type}",
                            )
                    else:
                        raise FlowError(
                            ErrCode.FLOW_TYPE_MISSING,
                            f"Flow '{cls.__name__}' type parameters [I, O] missing"
                        )
                    break

    @property
    def input_type(self) -> Type[I]:
        """Get the input type I of this flow."""
        return self._input_type

    @property
    def output_type(self) -> Type[O]:
        """Get the output type O of this flow."""
        return self._output_type

    def init(self) -> None:
        """
        Initialize flow resources.

        Called once when flow process starts.
        Override to load models, open connections, etc.
        """
        pass

    def init_config(self) -> dict:
        """
        Return a JSON-serializable dict that can reconstruct this Flow.

        Why this exists:
        - In-process debugging (`Pipeline.step()`) runs the same Flow instances
          you constructed in Python, so constructor args work naturally.
        - Backend execution (multiprocessing/dora) reconstructs Flows from IR,
          so we need a way to serialize constructor arguments.

        Default behavior:
        - Returns `{}` (assumes the Flow is default-constructible).

        Override this if your Flow needs constructor args and you want it to run
        on backends:

            class MyFlow(Flow[In, Out]):
                def __init__(self, gain: float = 0.5):
                    self.gain = gain

                def init_config(self) -> dict:
                    return {"gain": self.gain}

        If your Flow cannot be constructed with `__init__(**init_config)`,
        also override `from_init_config(...)`.
        """
        return {}

    @classmethod
    def from_init_config(cls, config: dict) -> "Flow":
        """
        Construct a Flow instance from `init_config()`.

        Default behavior:
        - `cls()` if config is empty
        - `cls(**config)` otherwise
        """
        if config:
            return cls(**config)  # type: ignore[call-arg]
        return cls()  # type: ignore[call-arg]

    def finalize(self) -> None:
        """
        Cleanup flow resources.

        Called once when flow process stops.
        Override to close connections, cleanup, etc.
        """
        pass

    def reset(self) -> None:
        """
        Reset internal state (optional).

        Retriever's long-term direction is to support "gym-like" stateful flows.
        Today, most flows are stateless and can ignore this hook.
        """
        return None

    def step(self, input: I) -> O:
        """
        Single-step execution alias.

        This is an ergonomic alias for `run(...)` so user code can reserve the
        word "run" for backend execution (Pipeline/engine).
        """
        return self.run(input)

    def forward(self, input: I) -> O:
        """PyTorch-style alias for `step(...)`."""
        return self.step(input)

    @abstractmethod
    def run(self, input: I) -> O:
        """
        Execute flow computation.

        Called each time the flow's clock fires.

        Args:
            input: Input value of type I (@flow_io dataclass)

        Returns:
            Output value of type O (@flow_io dataclass)

        Example:
            def run(self, input: ProcessInput) -> ProcessOutput:
                output = ProcessOutput()

                match input._signals:
                    case []:
                        self.tick += 1
                    case ['command']:
                        output.response = self.execute(input.command)
                    case ['image', 'lidar', 'imu']:
                        output.fusion = self.fuse(input.image, input.lidar, input.imu)

                return output
        """
        pass

    def __getstate__(self):
        """
        Custom pickling to exclude common unpicklable components.
        
        This allows Flows to store threading.Lock, queue.Queue, etc. 
        as long as they are initialized in init() rather than __init__().
        """
        state = self.__dict__.copy()
        unpicklable_types = (
            'threading.Lock', 'threading.RLock', 'threading.Thread', 
            'queue.Queue', 'SimpleQueue', 'JoinableQueue',
            'dora.Node', 'FastAPI'
        )
        
        to_remove = []
        for k, v in state.items():
            t_str = str(type(v))
            if any(p in t_str for p in unpicklable_types):
                to_remove.append(k)
        
        for k in to_remove:
            state.pop(k)
            
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Runtime objects must be re-initialized in init()
        pass
