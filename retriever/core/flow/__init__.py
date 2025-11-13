"""
Flow module - Declarative dataflow computation framework.

Provides base classes and utilities for building dataflow pipelines.
"""

from retriever.core.flow.base import Flow
from retriever.core.flow.clock import Clock, Rate, Trigger, Hybrid
from retriever.core.flow.adapter import Adapter, Latest, Hold, Window
from retriever.core.flow.config import FlowConfig
from retriever.core.flow.handle import FlowHandle
from retriever.core.flow.context import FlowContext
from retriever.core.flow.graph import FlowGraph, FlowNode, FlowEdge
from retriever.core.flow.io import flow_io, is_flow_io

__all__ = [
    # Base
    'Flow',

    # Clocks
    'Clock',
    'Rate',
    'Trigger',
    'Hybrid',

    # Adapters
    'Adapter',
    'Latest',
    'Hold',
    'Window',

    # Configuration
    'FlowConfig',
    'FlowHandle',
    'FlowContext',

    # Graph
    'FlowGraph',
    'FlowNode',
    'FlowEdge',

    # I/O
    'flow_io',
    'is_flow_io',
]
