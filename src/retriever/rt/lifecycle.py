"""
Shared flow runtime lifecycle helpers.

This module keeps runtime instantiation and init ordering consistent across:
- in-process stepper
- multiprocessing executors
- dora executors
"""

from __future__ import annotations

import importlib
from typing import Type

from retriever.error import ErrCode, FlowError
from retriever.flow.base import Flow
from retriever.ir.core import IRNode


def load_flow_class(node: IRNode) -> Type[Flow]:
    """Load Flow class from IR node metadata without instantiating it."""
    try:
        module = importlib.import_module(node.module)
        cls = getattr(module, node.type)
    except Exception as exc:
        raise FlowError(
            ErrCode.FLOW_INVALID,
            f"Cannot load flow class {node.type}: {exc}",
            module=node.module,
            type=node.type,
        ) from exc
    return cls


def instantiate_flow_from_node(node: IRNode) -> Flow:
    """Instantiate runtime flow object from IR node init config."""
    cls = load_flow_class(node)
    cfg = node.init_config or {}
    try:
        if hasattr(cls, "from_init_config"):
            return cls.from_init_config(cfg)  # type: ignore[attr-defined]
        return cls(**cfg) if cfg else cls()  # type: ignore[misc]
    except Exception as exc:
        raise FlowError(
            ErrCode.FLOW_INVALID,
            f"Cannot instantiate {node.type}: {exc}",
            module=node.module,
            type=node.type,
            node_id=node.id,
        ) from exc


def is_main_thread_flow_node(node: IRNode) -> bool:
    """Check class-level @gui_flow marker without runtime-heavy instantiation."""
    cls = load_flow_class(node)
    return bool(getattr(cls, "_main_thread", False))


def initialize_flow_runtime(flow: Flow) -> None:
    """
    Execute runtime lifecycle bootstrap:
    1) optional __lazy_init__()
    2) reset()
    """
    lazy_init = getattr(flow, "__lazy_init__", None)
    if callable(lazy_init):
        lazy_init()
    flow.reset()
