"""
Flow I/O type system.

Provides @flow_io decorator that transforms dataclasses 
into Flow I/O types with signal helpers and port extraction.
"""

from dataclasses import fields, MISSING
from typing import get_args, get_origin
from typing import Optional, Any, Union

from retriever.core.error import FlowError, ErrCode


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


def flow_io(cls):
    """
    Decorator for Flow I/O dataclasses.

    Transforms a regular dataclass into a Flow I/O type by:
    1. Making all fields Optional[T]
    2. Setting default=None for fields without defaults
    3. Injecting signal helper methods

    Usage:
        @flow_io
        @dataclass
        class MyInput:
            field1: int
            field2: str

        # Becomes:
        class MyInput:
            field1: Optional[int] = None
            field2: Optional[str] = None
            # + signal helper methods

    Args:
        cls: Dataclass to transform

    Returns:
        Transformed dataclass with Optional fields and signal helpers
    """

    # Validate input is a dataclass
    if not hasattr(cls, '__dataclass_fields__'):
        raise FlowError(
            ErrCode.FLOW_IO_NOT_DATACLASS,
            f"@flow_io must be applied to a @dataclass.\n"
            f"Usage:\n"
            f"  @flow_io\n"
            f"  @dataclass\n"
            f"  class {cls.__name__}:\n"
        )

    # Store original types before Optional wrapping
    original_types = {
        f.name: _unwrap_optional(f.type)
        for f in fields(cls)
    }
    cls.__flow_io_original_types__ = original_types

    # Make all fields Optional in annotations
    new_annotations = {
        name: (typ if _is_optional(typ) else Optional[typ])
        for name, typ in cls.__annotations__.items()
    }
    cls.__annotations__ = new_annotations

    # Create a custom __init__ that applies field defaults or None
    def __init__(self, **kwargs):
        """Initialize with all fields using their defaults or None."""
        for field_name, field_obj in self.__dataclass_fields__.items():
            if field_name in kwargs:
                # User provided value
                continue
            elif field_obj.default is not MISSING:
                # Field has a default value
                setattr(self, field_name, field_obj.default)
            elif field_obj.default_factory is not MISSING:
                # Field has a default factory
                setattr(self, field_name, field_obj.default_factory())
            else:
                # No default, use None
                setattr(self, field_name, None)

        # Apply provided kwargs
        for key, value in kwargs.items():
            if key not in self.__dataclass_fields__:
                raise FlowError(
                    ErrCode.FLOW_IO_INIT_UNEXPECTED,
                    f"__init__() got an unexpected keyword argument '{key}'"
                )
            setattr(self, key, value)

    # Replace the original __init__ with our custom one
    cls.__init__ = __init__

    # Inject signal helper methods
    def _set_signal(self, field_name: str, value: Any) -> None:
        """Set field value at runtime."""
        if field_name not in self.__dataclass_fields__:
            raise FlowError(
                ErrCode.FLOW_IO_FIELD_NOT_FOUND,
                f"Field '{field_name}' does not exist in {self.__class__.__name__}. "
                f"Available fields: {list(self.__dataclass_fields__.keys())}"
            )
        setattr(self, field_name, value)

    def _get_signal(self, field_name: str) -> Any:
        """Get field value at runtime."""
        if field_name not in self.__dataclass_fields__:
            raise FlowError(
                ErrCode.FLOW_IO_FIELD_NOT_FOUND,
                f"Field '{field_name}' does not exist in {self.__class__.__name__}. "
                f"Available fields: {list(self.__dataclass_fields__.keys())}"
            )
        return getattr(self, field_name)

    def _has_signal(self, field_name: str) -> bool:
        """Check if field has a value (not None)."""
        if field_name not in self.__dataclass_fields__:
            raise FlowError(
                ErrCode.FLOW_IO_FIELD_NOT_FOUND,
                f"Field '{field_name}' does not exist in {self.__class__.__name__}. "
                f"Available fields: {list(self.__dataclass_fields__.keys())}"
            )
        return getattr(self, field_name) is not None

    def _has_field_name(self, field_name: str) -> bool:
        """Check if field name exists in dataclass."""
        return field_name in self.__dataclass_fields__

    def _get_field_type(self, field_name: str) -> type:
        """Get original (non-Optional) type of field."""
        if field_name not in self.__dataclass_fields__:
            raise FlowError(
                ErrCode.FLOW_IO_FIELD_NOT_FOUND,
                f"Field '{field_name}' does not exist in {self.__class__.__name__}. "
                f"Available fields: {list(self.__dataclass_fields__.keys())}"
            )
        return self.__flow_io_original_types__[field_name]

    @property
    def _signals(self) -> list:
        """List of field names with non-None values."""
        return [name for name in self.__dataclass_fields__
                if getattr(self, name) is not None]

    # Add methods to class
    cls._signals = _signals
    cls._set_signal = _set_signal
    cls._get_signal = _get_signal
    cls._has_signal = _has_signal
    cls._has_field_name = _has_field_name
    cls._get_field_type = _get_field_type


    # Mark class as FlowIO
    cls.__is_flow_io__ = True

    return cls


def is_flow_io(cls) -> bool:
    """Check if class is decorated with @flow_io."""
    return hasattr(cls, '__is_flow_io__') and cls.__is_flow_io__


def get_flow_io_types(cls) -> dict[str, type]:
    """Get original field types from a @flow_io decorated class."""
    if not is_flow_io(cls):
        raise FlowError(
            ErrCode.FLOW_IO_INVALID,
            f"Class '{cls.__name__}' is not decorated with @flow_io",
        )
    return cls.__flow_io_original_types__.copy()


def get_flow_io_fields(cls) -> list[str]:
    """Get field names from a @flow_io decorated class."""
    if not is_flow_io(cls):
        raise FlowError(
            ErrCode.FLOW_IO_INVALID,
            f"Class '{cls.__name__}' is not decorated with @flow_io",
        )
    return list(cls.__dataclass_fields__.keys())
