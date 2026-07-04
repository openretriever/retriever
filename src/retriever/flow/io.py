"""
Flow I/O type system.

Provides `@io` for declaring Flow I/O types with signal helpers
and port extraction.
"""

import sys
from dataclasses import MISSING, dataclass, fields
from typing import Any, Optional, Union, get_args, get_origin

from retriever.error import ErrCode, FlowError


def _is_optional(field_type) -> bool:
    """Check if a type annotation is Optional[X]"""
    origin = get_origin(field_type)
    if origin is Union: # Union[X, None]
        args = get_args(field_type)
        return len(args) == 2 and type(None) in args
    return False


def _unwrap_optional(field_type):
    """Extract X from Optional[X]"""
    if _is_optional(field_type):
        args = get_args(field_type)
        # Return the non-None type
        return next(arg for arg in args if arg is not type(None))
    return field_type

def io(cls=None, *, frozen: bool = True):
    """
    Decorator for Flow input/output types.

    Behavior:
    1. If class is not a dataclass, converts it to one.
    2. Makes all fields Optional[T] by default.
    3. Injects signal helper methods (_get_signal, etc).

    Usage:
        @io
        class Observation:
            rgb: np.ndarray
            timestamp: float

        # Becomes a dataclass-like IO envelope with:
        #   rgb: Optional[np.ndarray] = None
        #   timestamp: Optional[float] = None
        #   + signal helpers

    Notes:
        - `@io` already applies dataclass conversion when needed.
        - Passing an existing dataclass through `io(MyType)` is still supported.
        - `frozen` is accepted for API compatibility, but IO envelopes remain
          runtime-mutable via the injected helper methods.
    """
    def wrap(cls):
        # 1. Auto-apply dataclass if needed
        if not hasattr(cls, '__dataclass_fields__'):
            # Note: We force frozen=False initially to allow __init__ to set fields,
            # but users should treat IO objects as immutable events.
            # (The runtime implementation of dataclasses makes 'frozen' hard to combine
            # with our custom __init__ that handles Optional fields broadly).
            cls = dataclass(cls, frozen=False)

        # 2. Store original types
        if not hasattr(cls, '__flow_io_original_types__'):
            original_types = {
                f.name: _unwrap_optional(f.type)
                for f in fields(cls)
            }
            cls.__flow_io_original_types__ = original_types

        # 3. Make fields Optional in annotations
        if hasattr(cls, '__annotations__'):
            new_annotations = {
                name: (typ if _is_optional(typ) else Optional[typ])
                for name, typ in cls.__annotations__.items()
            }
            cls.__annotations__ = new_annotations

        # 4. Inject custom init that handles None defaults
        _inject_custom_init(cls)

        # 5. Inject signal helpers
        _inject_signal_helpers(cls)

        # Mark as IO type
        cls.__is_flow_io__ = True
        return cls

    if cls is None:
        return wrap
    return wrap(cls)


def _inject_custom_init(cls):
    """Inject __init__ that allows partial initialization."""

    def __init__(self, *args, **kwargs):
        # Map positional args to field names
        field_names = list(self.__dataclass_fields__.keys())
        if len(args) > len(field_names):
            raise TypeError(f"__init__() takes {len(field_names)} positional arguments but {len(args)} were given")
        
        for i, val in enumerate(args):
            kwargs[field_names[i]] = val

        # Set fields: provided -> default -> None
        for name, field in self.__dataclass_fields__.items():
            if name in kwargs:
                val = kwargs[name]
            elif field.default is not MISSING:
                val = field.default
            elif field.default_factory is not MISSING:
                val = field.default_factory()
            else:
                val = None
            
            object.__setattr__(self, name, val)

    cls.__init__ = __init__


def _inject_signal_helpers(cls):
    """Inject helpers for runtime signal access."""
    
    def _set_signal(self, field_name: str, value: Any) -> None:
        if field_name not in self.__dataclass_fields__:
            raise FlowError(ErrCode.FLOW_IO_FIELD_NOT_FOUND, f"Field '{field_name}' not found")
        object.__setattr__(self, field_name, value)

    def _get_signal(self, field_name: str) -> Any:
        if field_name not in self.__dataclass_fields__:
            raise FlowError(ErrCode.FLOW_IO_FIELD_NOT_FOUND, f"Field '{field_name}' not found")
        return getattr(self, field_name)

    def _has_signal(self, field_name: str) -> bool:
        if field_name not in self.__dataclass_fields__:
            raise FlowError(ErrCode.FLOW_IO_FIELD_NOT_FOUND, f"Field '{field_name}' not found")
        return getattr(self, field_name, None) is not None

    def _fields(self) -> list:
        return [n for n in self.__dataclass_fields__ if getattr(self, n) is not None]
    
    cls._set_signal = _set_signal
    cls._get_signal = _get_signal
    cls._has_signal = _has_signal
    cls._signals = property(_fields)



def is_flow_io(cls) -> bool:
    """Check if class is decorated with `@io`."""
    return hasattr(cls, '__is_flow_io__') and cls.__is_flow_io__


def get_flow_io_types(cls) -> dict[str, type]:
    """Get original field types from an `@io`-decorated class."""
    if not is_flow_io(cls):
        raise FlowError(
            ErrCode.FLOW_IO_INVALID,
            f"Class '{cls.__name__}' is not decorated with @io",
        )
    return cls.__flow_io_original_types__.copy()


def get_flow_io_fields(cls) -> list[str]:
    """Get field names from an `@io`-decorated class."""
    if not is_flow_io(cls):
        raise FlowError(
            ErrCode.FLOW_IO_INVALID,
            f"Class '{cls.__name__}' is not decorated with @io",
        )
    return list(cls.__dataclass_fields__.keys())


def compose(name: str, *, frozen: bool = True, **field_types: type):
    """
    Dynamically create a named ``@io`` type from a mapping of field names to types.

    Equivalent to writing::

        @io
        @dataclass
        class <name>:
            field1: Type1
            field2: Type2

    Example::

        SE3Pose = compose("SE3Pose", position=Vector3, orientation=Quaternion)
        Twist   = compose("Twist",   linear=Vector3,   angular=Vector3)
    """
    annotations = dict(field_types)
    cls = type(name, (), {"__annotations__": annotations})
    # Attribute the class to the caller's module (namedtuple-style) so repr,
    # pickling, and registries report where it was defined, not this factory.
    try:
        cls.__module__ = sys._getframe(1).f_globals.get("__name__", __name__)
    except (AttributeError, ValueError):
        pass
    cls = dataclass(cls, frozen=frozen)
    return io(cls)


def select(source: type, *fields: str, name: str | None = None):
    """
    Create a subset ``@io`` type projecting specific fields from an existing ``@io`` type.

    Field types are taken from ``source.__flow_io_original_types__`` (unwrapped,
    so the resulting type behaves exactly like any ``compose()``-created type).

    Example::

        PosOnly = select(SE3Pose, "position", name="PosOnly")
    """
    if not is_flow_io(source):
        raise FlowError(
            ErrCode.FLOW_IO_INVALID,
            f"select() source '{source.__name__}' must be decorated with @io",
        )
    original = source.__flow_io_original_types__
    missing = [f for f in fields if f not in original]
    if missing:
        raise FlowError(
            ErrCode.FLOW_IO_FIELD_NOT_FOUND,
            f"Fields {missing} not found in '{source.__name__}'",
        )
    dataclass_params = getattr(source, "__dataclass_params__", None)
    frozen = bool(getattr(dataclass_params, "frozen", True))
    cls = compose(name or f"{source.__name__}Subset", frozen=frozen, **{f: original[f] for f in fields})
    # compose() attributed the class to this module; re-stamp with our caller.
    try:
        cls.__module__ = sys._getframe(1).f_globals.get("__name__", cls.__module__)
    except (AttributeError, ValueError):
        pass
    return cls
