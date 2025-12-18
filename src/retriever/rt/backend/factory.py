"""
Backend factory and registration system.

Provides registration mechanism for backend implementations.
"""

from typing import Dict, Type, List
import importlib.util
from retriever.core.rt.backend.interface import BackendFactory
from retriever.core.error import backend_error, ErrCode

import logging
logger = logging.getLogger(__name__)


# Global backend registry
_BACKEND_REGISTRY: Dict[str, Type[BackendFactory]] = {}


def register_backend(name: str):
    """
    Decorator to register a backend factory.

    Backends register themselves at module import time.

    Args:
        name: Backend name (e.g., 'multiprocessing', 'dora')

    Usage:
        @register_backend('multiprocessing')
        class MultiprocessingBackendFactory:
            @property
            def name(self) -> str:
                return 'multiprocessing'

            def create_engine(self, ir, config=None):
                return MultiprocessingEngine(ir, config)

    Raises:
        ValueError: If backend name already registered
    """
    def decorator(factory_class: Type[BackendFactory]) -> Type[BackendFactory]:
        # Validate it implements BackendFactory protocol
        if not hasattr(factory_class, 'create_engine'):
            raise ValueError(
                f"{factory_class.__name__} must implement create_engine() method"
            )

        if not hasattr(factory_class, 'name'):
            raise ValueError(
                f"{factory_class.__name__} must implement name property"
            )

        # Check for name collision
        if name in _BACKEND_REGISTRY:
            existing = _BACKEND_REGISTRY[name]
            raise ValueError(
                f"Backend '{name}' already registered to {existing.__name__}"
            )

        # Register backend
        _BACKEND_REGISTRY[name] = factory_class
        logger.debug(f"Registered backend: {name} → {factory_class.__name__}")

        return factory_class

    return decorator


def get_backend(name: str) -> Type[BackendFactory]:
    """
    Get backend factory by name.

    Args:
        name: Backend name

    Returns:
        BackendFactory class

    Raises:
        RTError: If backend not found

    Example:
        factory_class = get_backend('multiprocessing')
        factory = factory_class()
        engine = factory.create_engine(ir)
    """
    if name not in _BACKEND_REGISTRY:
        # Try a best-effort dynamic import in case an earlier lazy import failed
        if name == "dora":
            try:
                if importlib.util.find_spec("dora") and importlib.util.find_spec("pyarrow"):
                    import retriever.core.rt.backend.dora  # noqa: F401
            except Exception:
                # Swallow and fall through to the user-facing error
                pass

        if name not in _BACKEND_REGISTRY:
            available = list(_BACKEND_REGISTRY.keys())
            hint = ""
            if name == "dora":
                hint = " (install dora-rs, dora-rs-cli, pyarrow to enable)"
            raise backend_error(
                ErrCode.BACKEND_NOT_FOUND,
                f"Backend '{name}' not found{hint}. Available: {available}"
            )

    return _BACKEND_REGISTRY[name]


def list_backends() -> List[str]:
    """
    List all registered backend names.

    Returns:
        List of backend names

    Example:
        >>> list_backends()
        ['multiprocessing', 'dora']
    """
    return list(_BACKEND_REGISTRY.keys())


# Import backend implementations to trigger registration
# This ensures backends are registered when factory module is imported

def _register_builtin_backends():
    """
    Import built-in backends to trigger registration.

    Called automatically when factory module is imported.
    """
    try:
        # Import multiprocessing backend
        import retriever.core.rt.backend.multiprocessing  # noqa: F401
        logger.debug("Multiprocessing backend imported")
    except ImportError as e:
        logger.warning(f"Could not import multiprocessing backend: {e}")

    try:
        # Skip if optional dependencies are missing to avoid partial registration
        if importlib.util.find_spec("dora") is None or importlib.util.find_spec("pyarrow") is None:
            raise ImportError("Missing dependencies: dora, pyarrow")

        # Import dora backend (may not be available)
        import retriever.core.rt.backend.dora  # noqa: F401
        logger.debug("Dora backend imported")
    except ImportError as e:
        # Clean up partial registration if import failed after decorator ran
        _BACKEND_REGISTRY.pop("dora", None)
        logger.info(
            "Dora backend not available (install dora-rs, dora-rs-cli, pyarrow): %s",
            e,
        )


# Auto-register backends on module import
_register_builtin_backends()
