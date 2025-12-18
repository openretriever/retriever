"""
Declarative service layer for inter-flow RPC.

Yield-based model:
- @handle_service: marks method as service provider
- @call_service: declares service dependencies on a Flow class
- ServiceCall: yield from Flow.run() to make service call
"""

import inspect
from typing import Callable, TypeVar, Any, Optional, Type, get_type_hints
from dataclasses import dataclass, is_dataclass

F = TypeVar('F')


@dataclass(frozen=True)
class ServiceCall:
    """
    Yield from Flow.run() to make a service call.

    Usage:
        response = yield ServiceCall(Provider.method, request)
    """
    service_method: 'ServiceMethod'
    request: Any
    timeout: float = 5.0


@dataclass
class ServiceDescriptor:
    """Metadata for a service method, used by IR for routing."""
    method_name: str
    request_type: Type
    response_type: Type
    flow_class: Optional[Type] = None

    @property
    def service_id(self) -> str:
        return f"{self.flow_class.__name__}.{self.method_name}"


def parse_service_id(srv_id: str) -> tuple[str, str]:
    """Parse service ID into (class_name, method_name)."""
    class_name, method_name = srv_id.rsplit('.', 1)
    return class_name, method_name


def is_service_port(port_name: str) -> bool:
    """Check if port is a service port (request/response)."""
    return port_name.startswith('_request') or port_name.startswith('_response')


class ServiceMethod:
    """
    Descriptor wrapper for @handle_service methods.
    Uses __set_name__ to capture the owning Flow class.
    """

    def __init__(self, func: Callable, descriptor: ServiceDescriptor):
        self._func = func
        self._descriptor = descriptor

    def __set_name__(self, owner: Type, _name: str):
        self._descriptor.flow_class = owner

        # Collect handler in owner class
        if not hasattr(owner, '__flow_service_handlers__'):
            owner.__flow_service_handlers__ = []
        owner.__flow_service_handlers__.append(self)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self._func.__get__(obj, objtype)

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    @property
    def descriptor(self) -> ServiceDescriptor:
        return self._descriptor


def handle_service(func: Callable) -> ServiceMethod:
    """
    Mark method as a service handler.

    Signature: (self, request: Dataclass) -> Dataclass
    """
    from retriever.error import FlowError, ErrCode

    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    if len(params) < 2:
        raise FlowError(
            ErrCode.FLOW_SERVICE_INVALID_SIGNATURE,
            f"{func.__name__}: expected (self, request: Dataclass) -> Dataclass"
        )

    # Resolve annotations to concrete types (supports `from __future__ import annotations`).
    try:
        hints = get_type_hints(func, globalns=getattr(func, "__globals__", None))
    except Exception:
        hints = {}

    request_type = hints.get(params[1].name, params[1].annotation)
    response_type = hints.get("return", sig.return_annotation)

    if request_type == inspect.Parameter.empty:
        raise FlowError(
            ErrCode.FLOW_SERVICE_INVALID_SIGNATURE,
            f"{func.__name__}: request parameter must have type hint"
        )

    if response_type == inspect.Signature.empty:
        raise FlowError(
            ErrCode.FLOW_SERVICE_INVALID_SIGNATURE,
            f"{func.__name__}: return type must have type hint"
        )

    if not is_dataclass(request_type):
        raise FlowError(
            ErrCode.FLOW_SERVICE_INVALID_SIGNATURE,
            f"{func.__name__}: request type {getattr(request_type, '__name__', request_type)!r} must be dataclass"
        )

    if not is_dataclass(response_type):
        raise FlowError(
            ErrCode.FLOW_SERVICE_INVALID_SIGNATURE,
            f"{func.__name__}: response type {getattr(response_type, '__name__', response_type)!r} must be dataclass"
        )

    descriptor = ServiceDescriptor(
        method_name=func.__name__,
        request_type=request_type,
        response_type=response_type,
    )

    return ServiceMethod(func, descriptor)


def call_service(*service_methods: ServiceMethod) -> Callable[[Type[F]], Type[F]]:
    """
    Class decorator declaring service dependencies.

    Enables IR to build direct routing instead of broadcast.
    """
    from retriever.error import FlowError, ErrCode

    def decorator(flow_class: Type[F]) -> Type[F]:
        flow_class.__flow_service_callers__ = []
        for srv in service_methods:
            if not isinstance(srv, ServiceMethod):
                raise FlowError(
                    ErrCode.FLOW_SERVICE_INVALID,
                    f"{flow_class.__name__}: {srv} is not a @handle_service method"
                )
            flow_class.__flow_service_callers__.append(srv)

        return flow_class

    return decorator
