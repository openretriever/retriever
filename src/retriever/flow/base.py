"""
Flow base class for declarative dataflow computation.

A Flow is a signal function that transforms inputs to outputs.
"""

from abc import ABC, abstractmethod
import warnings
from typing import get_origin, get_args
from typing import Any, ClassVar, Tuple, TypeVar, Generic, Optional, Type, TYPE_CHECKING
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
    I and O must be `@io`-decorated types.
    """

    _input_types: Tuple[Type, ...] = ()
    _output_types: Tuple[Type, ...] = ()
    _input_type: Optional[Type] = None  # Legacy/Singular accessor
    _output_type: Optional[Type] = None # Legacy/Singular accessor
    _main_thread: bool = False  # If True, run in main thread (for GUI flows)
    _is_composite_input: bool = False
    _rr_instance = None  # Cached Rerun instance

    # Rate configuration (optional, used by DefaultRate/AdaptiveRate clocks)
    # Set this to a FlowRateConfig instance to configure rate behavior
    rate_config: ClassVar[Optional['FlowRateConfig']] = None

    @classmethod
    def __class_getitem__(cls, params):
        """
        Normalize tuple-literal generic parameters before Generic validates them.

        Python 3.9 rejects `Flow[(A, B), C]` at the Generic layer unless the
        raw tuple literal is first converted into `tuple[A, B]`.
        """
        if not isinstance(params, tuple):
            params = (params,)

        def _normalize(arg):
            if isinstance(arg, tuple):
                items = tuple(type(None) if item is None else item for item in arg)
                return tuple.__class_getitem__(items)
            return arg

        return super().__class_getitem__(tuple(_normalize(arg) for arg in params))

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

            tuple_args = None
            # Support Flow[(A, B), C] parenthesized tuple-literal syntax.
            if isinstance(arg, tuple):
                tuple_args = arg
            # Support Flow[tuple[A, B], C] typing tuple syntax.
            elif get_origin(arg) is tuple:
                tuple_args = get_args(arg)

            if tuple_args is not None:
                extracted = []
                for item in tuple_args:
                    if isinstance(item, TypeVar):
                        continue
                    if item is type(None) or item is None:
                        raise FlowError(
                            ErrCode.FLOW_TYPE_INVALID,
                            "Mixed tuple signatures with None elements are invalid",
                        )
                    extracted.append(item)
                return tuple(extracted)

            return (arg,)

        cls._input_types = _extract_types(args[0])
        cls._is_composite_input = (len(cls._input_types) > 1)
        cls._output_types = _extract_types(args[1])
        
        # Set legacy single-type fields (first type or None)
        cls._input_type = cls._input_types[0] if cls._input_types else None
        cls._output_type = cls._output_types[0] if cls._output_types else None

        # Validate @io decoration
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

    @property
    def rr(self):
        """
        Get Rerun instance, auto-connecting via gRPC if needed.
        
        Usage in Flow.step():
            if self.rr:
                self.rr.log("metrics/latency", rr.Scalars([value]))
        
        Returns None if Rerun is not available.
        """
        if self._rr_instance is None:
            try:
                import os
                import rerun as _rr
                from retriever.config import get_global_config
                from retriever.lib.rerun import _connect_rerun
                config = get_global_config()
                app_id = os.environ.get("RERUN_APP_ID") or config.get("app_id", "retriever")
                connect_addr = os.environ.get("RERUN_CONNECT_ADDR") or config.get(
                    "rerun_connect_addr", "127.0.0.1:9876"
                )
                recording_id = os.environ.get("RERUN_RECORDING_ID")
                # Init with spawn=False (subprocess connects to main viewer)
                _rr.init(app_id, spawn=False, recording_id=recording_id)
                _connect_rerun(_rr, connect_addr)
                self._rr_instance = _rr
            except Exception as e:
                import logging
                logging.getLogger(__name__).info(f"Rerun not initialized: {e}")
                self._rr_instance = False  # Sentinel to avoid retrying
        return self._rr_instance if self._rr_instance else None

    def init(self) -> None:
        """
        Deprecated alias for `reset()`.

        Runtime startup now calls `reset()` directly. This alias remains so older
        flows and external callers that still invoke `init()` continue to work.
        """
        warnings.warn(
            f"{type(self).__name__}.init() is deprecated. Override reset() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.reset()

    def __lazy_init__(self) -> None:
        """
        Optional runtime-local initialization hook.

        Use this for process-local helpers derived from already-serialized config
        before `init()` acquires heavyweight resources. Keep `__init__()` limited
        to lightweight, serializable authoring-time configuration.
        """
        return None

    def init_config(self) -> dict:
        """
        Return a JSON-serializable dict that can reconstruct this Flow.

        Why this exists:
        - In-process debugging (`Pipeline.step()`) runs the same Flow instances
          you constructed in Python, so constructor args work naturally.
        - Backend execution (multiprocessing/dora) reconstructs Flows from IR,
          so we need a way to serialize constructor arguments.
        - Local resources (devices, sockets, SDK clients, file handles) should
          not live in this config. Serialize descriptors/paths/ids instead, and
          reacquire the resource in `init()` / `__lazy_init__()`.

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

    def viz_metadata(self) -> Optional[dict[str, Any]]:
        """
        Return optional JSON-serializable metadata for IR visualization only.

        This is intentionally non-semantic: execution backends must not depend
        on it. Use it to enrich HTML/ASCII views for composite or specialized
        nodes without affecting runtime behavior.
        """
        return None

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
        Reset or initialize internal runtime state.

        This is the primary lifecycle hook to override for flow-local state and
        runtime resources. It is called:
        - once when runtime execution starts
        - again when `Pipeline.reset()` is requested

        Backwards compatibility:
        - If a subclass overrides `init()` but not `reset()`, `reset()` will call
          that legacy `init()` implementation and emit a deprecation warning.
        """
        if self._uses_deprecated_init():
            warnings.warn(
                f"{type(self).__name__} overrides init() instead of reset(). "
                "Override reset() instead; init() is deprecated.",
                DeprecationWarning,
                stacklevel=3,
            )
            self.init()
        return None

    def step(self, input: I) -> O:
        """
        Execute one step of flow computation.

        This is the primary method to override in Flow subclasses.
        Called each time the flow's clock fires.

        Args:
            input: Input value of type I (`@io` type)

        Returns:
            Output value of type O (`@io` type)

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

    def _uses_deprecated_init(self) -> bool:
        """Check if subclass overrides init() but not reset()."""
        reset_cls = None
        init_cls = None
        for cls in type(self).__mro__:
            if "reset" in cls.__dict__ and reset_cls is None:
                reset_cls = cls
            if "init" in cls.__dict__ and init_cls is None:
                init_cls = cls
            if reset_cls and init_cls:
                break
        return init_cls is not Flow and reset_cls is Flow

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
        Deprecated alias for step().

        Runtime execution now calls `step()` directly. This alias remains for
        backwards compatibility with older flows and direct call sites.
        """
        warnings.warn(
            f"{type(self).__name__}.run() is deprecated. Call or override step() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
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
        # Runtime objects must be re-initialized in reset().
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
