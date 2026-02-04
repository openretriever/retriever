"""
Pipeline control system for Retriever flows.

Provides pause/resume/reset capabilities and external control via:
- CLI (retriever-ctl)
- Web dashboard
- Global keyboard shortcuts
"""

from dataclasses import dataclass
from typing import Optional

from retriever.rt.control.channel import (
    ControlChannel,
    ControlCommand,
    ControlMessage,
    ControlResponse,
    MPControlChannel,
    InProcessControlChannel,
)

from retriever.rt.control.controllable import (
    Controllable,
    FlowState,
    FlowStatus,
)

from retriever.rt.control.controller import (
    PipelineController,
    PipelineStatus,
)


@dataclass
class ControlConfig:
    """
    Configuration for pipeline control system.

    Usage:
        # In pipe.run()
        pipe.run(control=ControlConfig(web_port=8080, keyboard=True))

        # Or globally
        retriever.init(control=ControlConfig(keyboard=True))

    Attributes:
        enabled: Enable control system (auto-enabled if web_port or keyboard set)
        web_port: Port for web dashboard (None = disabled)
        keyboard: Enable global keyboard shortcuts
        cli_port: Port for CLI control (not yet implemented)
    """
    enabled: bool = True
    web_port: Optional[int] = None
    keyboard: bool = False
    cli_port: int = 9999

    def __post_init__(self):
        # Auto-enable if any interface is configured
        if self.web_port or self.keyboard:
            self.enabled = True


__all__ = [
    # Config
    "ControlConfig",
    # Channel
    "ControlChannel",
    "ControlCommand",
    "ControlMessage",
    "ControlResponse",
    "MPControlChannel",
    "InProcessControlChannel",
    # Controllable
    "Controllable",
    "FlowState",
    "FlowStatus",
    # Controller
    "PipelineController",
    "PipelineStatus",
]
