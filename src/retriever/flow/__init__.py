"""
Flow module - Declarative dataflow computation framework.

Provides base classes and utilities for building dataflow pipelines.
"""

from retriever.flow.base import Flow, gui_flow
from retriever.flow.clock import Clock, Rate, Trigger, Hybrid, Tick
from retriever.flow.adapter import Adapter, Latest, Hold, Window, Events
from retriever.flow.config import FlowConfig
from retriever.flow.handle import FlowHandle
from retriever.flow.context import FlowContext
from retriever.flow.pipeline import Pipeline
from retriever.flow.functional import connect, default_pipeline, reset_default_pipeline, clear_default_pipeline
from retriever.flow.graph import FlowGraph, FlowNode, FlowEdge
from retriever.flow.io import flow_io, is_flow_io
from retriever.flow.service import handle_service, call_service


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
    'Pipeline',
    'connect',
    'default_pipeline',
    'reset_default_pipeline',
    'clear_default_pipeline',

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

    # GUI
    'gui_flow',
]
