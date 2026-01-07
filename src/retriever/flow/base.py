"""
Flow base class for declarative dataflow computation.

A Flow is a signal function that transforms inputs to outputs.
"""

from abc import ABC, abstractmethod
from typing import get_origin, get_args
from typing import ClassVar, Tuple, TypeVar, Generic, Optional, Type, TYPE_CHECKING
from retriever.error import FlowError, ErrCode

if TYPE_CHECKING:
    from retriever.flow.config import FlowRateConfig

I = TypeVar("I")
O = TypeVar("O")
T = TypeVar("T")


class Flow(ABC, Generic[I, O]):
    """
    Abstract base class for flows.

    A Flow transforms inputs of type I to outputs of type O.
    I and O must be @flow_io decorated dataclasses.
    """

    _input_types: Tuple[Type, ...] = ()
    _output_types: Tuple[Type, ...] = ()
    _input_type: Optional[Type] = None  # Legacy/Singular accessor
    _output_type: Optional[Type] = None # Legacy/Singular accessor
    _main_thread: bool = False  # If True, run in main thread (for GUI flows)
    _is_composite_input: bool = False

    # Rate configuration (optional, used by DefaultRate/AdaptiveRate clocks)
    # Set this to a FlowRateConfig instance to configure rate behavior
    rate_config: ClassVar[Optional['FlowRateConfig']] = None

    def __init_subclass__(cls, **kwargs):
        """Extract type parameters from Flow[I, O] at class definition time."""
        super().__init_subclass__(**kwargs)

        # Skip validation for abstract intermediate classes
        if ABC in cls.__bases__:
            return

        # Find Flow[I, O] in bases
        flow_base = cls._find_flow_base()
        if flow_base is None:
            raise FlowError(
                ErrCode.FLOW_TYPE_MISSING,
                f"Flow '{cls.__name__}' must specify type parameters: "
                f"class {cls.__name__}(Flow[InputType, OutputType])",
            )

        args = get_args(flow_base)
        if len(args) < 2:
            raise FlowError(
                ErrCode.FLOW_TYPE_MISSING,
                f"Flow '{cls.__name__}' type parameters [I, O] missing",
            )

        # Helper to extract one or multiple types
        def _extract_types(arg) -> Tuple[Type, ...]:
            if isinstance(arg, TypeVar):
                return ()
            if arg is type(None):
                return ()
            # Handle Tuple[A, B]
            if get_origin(arg) is tuple:
                return get_args(arg)
            return (arg,)

        cls._input_types = _extract_types(args[0])
        cls._is_composite_input = (len(cls._input_types) > 1)
        cls._output_types = _extract_types(args[1])
        
        # Set legacy single-type fields (first type or None)
        cls._input_type = cls._input_types[0] if cls._input_types else None
        cls._output_type = cls._output_types[0] if cls._output_types else None

        # Validate @flow_io decoration
        cls._validate_flow_io_types(cls._input_types, cls._output_types)

    @classmethod
    def _find_flow_base(cls):
        """Find Flow[I, O] in __orig_bases__, or None if not found."""
        if not hasattr(cls, "__orig_bases__"):
            return None
        for base in cls.__orig_bases__:
            if get_origin(base) is Flow:
                return base
        return None

    @classmethod
    def _validate_flow_io_types(cls, input_types: Tuple[Type, ...], output_types: Tuple[Type, ...]):
        """Validate that input/output types use @io decorator."""
        from retriever.flow.io import is_flow_io

        for typ in input_types:
            if typ is not type(None) and not is_flow_io(typ):
                raise FlowError(
                    ErrCode.FLOW_TYPE_NOT_COMPATIBLE,
                    f"Flow input type must use @io decorator, got {typ}",
                )

        for typ in output_types:
            if typ is not type(None) and not is_flow_io(typ):
                raise FlowError(
                    ErrCode.FLOW_TYPE_NOT_COMPATIBLE,
                    f"Flow output type must use @io decorator, got {typ}",
                )

    @property
    def input_type(self) -> Type[I]:
        """
        Get the input type I of this flow.
        If multiple inputs (tuple), returns the first one (Warning: Legacy).
        Use `input_types` for full list.
        """
        return self._input_type

    @property
    def output_type(self) -> Type[O]:
        """
        Get the output type O of this flow.
        If multiple outputs, returns the first one.
        Use `output_types` for full list.
        """
        return self._output_type
        
    @property
    def input_types(self) -> Tuple[Type, ...]:
        """Get all input types (for composition)."""
        return self._input_types

    @property
    def output_types(self) -> Tuple[Type, ...]:
        """Get all output types (for composition)."""
        return self._output_types

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
        Execute one step of flow computation.

        This is the primary method to override in Flow subclasses.
        Called each time the flow's clock fires.

        Args:
            input: Input value of type I (@flow_io dataclass)

        Returns:
            Output value of type O (@flow_io dataclass)

        Example:
            def step(self, input: ProcessInput) -> ProcessOutput:
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
        # Check if subclass overrides run() but not step() - backwards compat
        if self._uses_deprecated_run():
            import warnings
            warnings.warn(
                f"{type(self).__name__} overrides run() instead of step(). "
                "Override step() instead; run() is deprecated.",
                DeprecationWarning,
                stacklevel=3
            )
            return self.run(input)  # type: ignore[misc]
        raise NotImplementedError(
            f"{type(self).__name__} must implement step()"
        )

    def _uses_deprecated_run(self) -> bool:
        """Check if subclass overrides run() but not step()."""
        # Get the class that defines each method
        step_cls = None
        run_cls = None
        for cls in type(self).__mro__:
            if 'step' in cls.__dict__ and step_cls is None:
                step_cls = cls
            if 'run' in cls.__dict__ and run_cls is None:
                run_cls = cls
            if step_cls and run_cls:
                break
        # Deprecated if run is overridden by subclass but step is not
        return run_cls is not Flow and step_cls is Flow

    def run(self, input: I) -> O:
        """
        Alias for step().

        Deprecated: Override step() in subclasses instead.
        """
        return self.step(input)

    def forward(self, input: I) -> O:
        """PyTorch-style alias for `step(...)`."""
        return self.step(input)

    def __call__(self, input: I) -> O:
        """
        Direct signal function execution: `output = flow(input)`.

        This enables using Flow instances as callable signal functions:
            detector = Detector(threshold=50.0)
            result = detector(sensor_input)  # Calls step() directly

        Note: This is for direct execution without clock/pipeline wiring.
        For pipeline wiring, use `flow @ Rate(...)` to create a FlowHandle.
        """
        return self.step(input)

    def __rshift__(self, other):
        """
        Support flow composition: A >> B
        """
        from retriever.flow.pipeline import Pipeline

        return Pipeline.from_flow(self) >> other

    def __and__(self, other):
        """
        Support parallel composition: A & B
        """
        from retriever.flow.pipeline import Pipeline

        return Pipeline.from_flow(self) & other

    def __getstate__(self):
        """
        Custom pickling to exclude common unpicklable components.

        This allows Flows to store threading.Lock, queue.Queue, etc.
        as long as they are initialized in init() rather than __init__().
        """
        state = self.__dict__.copy()
        unpicklable_types = (
            "threading.Lock",
            "threading.RLock",
            "threading.Thread",
            "queue.Queue",
            "SimpleQueue",
            "JoinableQueue",
            "dora.Node",
            "FastAPI",
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


def gui_flow(cls: T) -> T:
    """
    Mark a flow to run in main thread (for GUI frameworks).

    Example:
        @gui_flow
        class MujocoViewerFlow(Flow[State, None]):
            ...
    """
    cls._main_thread = True
    return cls
