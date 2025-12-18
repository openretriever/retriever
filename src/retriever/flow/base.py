"""
Flow base class for declarative dataflow computation.

A Flow is a signal function that transforms inputs to outputs.
"""

from abc import ABC, abstractmethod
from typing import get_origin, get_args
from typing import TypeVar, Generic, Optional, Type
from retriever.core.error import FlowError, ErrCode

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
                        from retriever.core.flow.io import is_flow_io

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
