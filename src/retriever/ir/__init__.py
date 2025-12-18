"""
IR (Intermediate Representation) module - validation + execution compilation.

Transforms FlowContext to validated IR, and (optionally) plans a physical
execution graph (partitioning + placement).
"""

from retriever.ir.struct import (
    IRStruct,
    IRNode,
    IREdge,
    IREdgeSource,
    IREdgeDestination,
    IRTopology,
    IRMetadata,
    IROptimization,
)
from retriever.ir.validator import validate
from retriever.ir.execution import (
    ExecutionGraph,
    ExecutionPartition,
    ExecutionEdge,
    Placement,
)
from retriever.ir.compiler import build_execution, compile_execution
from retriever.ir.optimizer import optimize_ir
from retriever.ir.analysis import run_all_analyses, IRAnalysis
from retriever.ir.loader import IRLoader

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
