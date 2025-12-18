"""
IR (Intermediate Representation) module - validation + execution compilation.

Transforms FlowContext to validated IR, and (optionally) plans a physical
execution graph (partitioning + placement).
"""

from retriever.core.ir.struct import (
    IRStruct,
    IRNode,
    IREdge,
    IREdgeSource,
    IREdgeDestination,
    IRTopology,
    IRMetadata,
    IROptimization,
)
from retriever.core.ir.validator import validate
from retriever.core.ir.execution import (
    ExecutionGraph,
    ExecutionPartition,
    ExecutionEdge,
    Placement,
)
from retriever.core.ir.compiler import build_execution, compile_execution
from retriever.core.ir.optimizer import optimize_ir
from retriever.core.ir.analysis import run_all_analyses, IRAnalysis
from retriever.core.ir.loader import IRLoader

__all__ = [
    # IR Structure
    'IRStruct',
    'IRNode',
    'IREdge',
    'IREdgeSource',
    'IREdgeDestination',
    'IRTopology',
    'IRMetadata',
    'IROptimization',

    # Execution compilation
    'ExecutionGraph',
    'ExecutionPartition',
    'ExecutionEdge',
    'Placement',
    # Preferred name (compile_execution remains as compatibility alias)
    'build_execution',
    'compile_execution',

    # Validation & (legacy) optimization
    'validate',
    'optimize_ir',

    # Analysis
    'run_all_analyses',
    'IRAnalysis',

    # Loader
    'IRLoader',
]
