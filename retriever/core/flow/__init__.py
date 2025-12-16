"""
Flow module - Declarative dataflow computation framework.

Provides base classes and utilities for building dataflow pipelines.
"""

from retriever.core.flow.base import Flow
from retriever.core.flow.clock import Clock, Rate, Trigger, Hybrid, Tick
from retriever.core.flow.adapter import Adapter, Latest, Hold, Window, Events
from retriever.core.flow.config import FlowConfig
from retriever.core.flow.handle import FlowHandle
from retriever.core.flow.context import FlowContext
from retriever.core.flow.graph import FlowGraph, FlowNode, FlowEdge
from retriever.core.flow.io import flow_io, is_flow_io
from retriever.core.flow.service import handle_service, call_service

__all__ = [
    # Base
    'Flow',

    # Clocks
    'Clock',
    'Rate',
    'Tick',
    'Trigger',
    'Hybrid',

    # Adapters
    'Adapter',
    'Latest',
    'Hold',
    'Window',
    'Events',

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

    # Services
    'handle_service',
    'call_service',
]
