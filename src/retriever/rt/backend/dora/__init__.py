"""
Dora backend for retriever runtime.

Provides dora-rs based execution using Apache Arrow for zero-copy IPC.

Usage:
    from retriever.rt.executor import execute_ir

    # Execute with dora backend
    execute_ir(ir, backend='dora', duration=10.0)

Features:
    - Zero-copy IPC via Apache Arrow
    - Supports all clock types (Rate, Trigger, Hybrid)
    - Supports all adapters (Latest, Hold, Window)
    - Compatible with existing IRStruct

Requirements:
    - dora-rs: Python bindings for dora runtime
    - dora-rs-cli: CLI tool for dora management
    - pyarrow: Apache Arrow for serialization

Installation:
    pip install dora-rs dora-rs-cli pyarrow
"""

import logging
from typing import Dict, Any, Optional

from retriever.rt.backend.factory import BackendFactory, register_backend
from retriever.ir.struct import IRStruct

logger = logging.getLogger(__name__)


@register_backend('dora')
class DoraBackendFactory(BackendFactory):
    """
    Factory for creating dora execution engines.

    Implements BackendFactory interface for dora-rs backend.
    """

    @property
    def name(self) -> str:
        """Backend name."""
        return "dora"

    @property
    def description(self) -> str:
        """Backend description."""
        return "Dora-rs backend with Apache Arrow zero-copy IPC"

    def validate_dependencies(self) -> bool:
        """
        Check if dora-rs and dependencies are installed.

        Returns:
            True if all dependencies available, False otherwise
        """
        try:
            import dora
            import pyarrow

            # Check dora-rs CLI
            import shutil
            if not shutil.which("dora"):
                logger.error(
                    "dora CLI not found. Install with: pip install dora-rs-cli"
                )
                return False

            logger.debug(
                f"Dora backend dependencies validated: "
                f"dora-rs={getattr(dora, '__version__', 'unknown')}, "
                f"pyarrow={pyarrow.__version__}"
            )
            return True

        except ImportError as e:
            logger.error(
                f"Dora backend missing dependencies: {e}\n"
                "Install with: pip install dora-rs dora-rs-cli pyarrow"
            )
            return False

    def create_engine(
        self,
        ir: IRStruct,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Create DoraEngine from IR.

        Args:
            ir: Validated IRStruct
            config: Backend-specific configuration:
                    - 'keep_yaml': Don't delete YAML after stop (default: False)
                    - 'yaml_dir': Custom directory for YAML (default: tempdir)
                    - 'dora_timeout': Timeout for dora commands (default: 10s)
                    - 'init_delay': Delay after dora start before spawning executors (default: 1.0s)
                    - 'join_timeout': Timeout when waiting for executors (default: 5.0s)
                    - 'buffer_engine': Buffer engine kind for per-port sampling ('python' | 'native', default: 'python')
                    - 'native_overrides': Optional node path overrides to run some nodes as native dora nodes
                      instead of Python executors. See `docs/temp_notes/2025-12-17_native_acceleration_plan.md`.

        Returns:
            DoraEngine instance

        Raises:
            ImportError: If dora-rs or pyarrow not installed
        """
        # Import here to avoid requiring dora at module load time
        from retriever.rt.backend.dora.engine import DoraEngine

        return DoraEngine(ir, config)

__all__ = [
    'DoraBackendFactory',
]
