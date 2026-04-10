"""
Flow module - Declarative dataflow computation framework.

Provides base classes and utilities for building dataflow pipelines.
"""

from retriever.flow.base import Flow, gui_flow
from retriever.flow.clock import Clock, Rate, Trigger, Hybrid, Tick, DefaultRate, AdaptiveRate
from retriever.flow.adapter import Adapter, Latest, Hold, Window, Events
from retriever.flow.config import FlowConfig, FlowRateConfig, EdgeConfig
from retriever.flow.temporal import TemporalFlow
from retriever.flow.builder import PipelineBuilder
from retriever.flow.pipeline import Pipeline
from retriever.flow.functional import connect, default_pipeline, reset_default_pipeline, clear_default_pipeline
from retriever.flow.graph import PipelineGraph, PipelineNode, PipelineEdge
from retriever.flow.io import flow_io, is_flow_io, io
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
    'DefaultRate',
    'AdaptiveRate',

    # Adapters
    'Adapter',
    'Latest',
    'Hold',
    'Window',
    'Events',

    # Configuration
    'FlowConfig',
    'FlowRateConfig',
    'EdgeConfig',
    'TemporalFlow',
    'PipelineBuilder',
    'Pipeline',
    'connect',
    'default_pipeline',
    'reset_default_pipeline',
    'clear_default_pipeline',

    # Graph
    'PipelineGraph',
    'PipelineNode',
    'PipelineEdge',

    # I/O
    'io',
    'flow_io',
    'is_flow_io',

    # Services
    'handle_service',
    'call_service',

    # GUI
    'gui_flow',
]
