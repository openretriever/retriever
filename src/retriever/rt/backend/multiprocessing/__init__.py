"""
Multiprocessing backend for retriever runtime.

Implements execution engine using Python's multiprocessing module.
"""

from retriever.core.rt.backend.factory import register_backend
from retriever.core.rt.backend.interface import BackendFactory, ExecutionEngine
from retriever.core.ir.struct import IRStruct
from typing import Dict, Any, Optional


@register_backend('multiprocessing')
class MPBackendFactory(BackendFactory):
    """Factory for multiprocessing backend."""

    @property
    def name(self) -> str:
        """Backend name."""
        return 'multiprocessing'

    @property
    def description(self) -> str:
        """Backend description."""
        return "Multiprocessing backend for local execution"

    def validate_dependencies(self) -> bool:
        """Validate backend dependencies."""
        # Multiprocessing is built-in, always available
        return True

    def create_engine(
        self,
        ir: IRStruct,
        config: Optional[Dict[str, Any]] = None,
    ) -> ExecutionEngine:
        from retriever.core.rt.backend.multiprocessing.engine import MPEngine
        return MPEngine(ir, config)


__all__ = ['MPBackendFactory']
