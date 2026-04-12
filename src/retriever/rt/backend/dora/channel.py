"""
DoraSubscriber/DoraPublisher - Event-based channel for dora backend.

DoraSubscriber: Maintains temporal buffer for received events
DoraPublisher: Sends messages via dora with sender timestamps
"""

from typing import Any, Dict, Iterable, Optional

from retriever.flow.adapter import Adapter
from retriever.flow.types import TimedBuffer
from retriever.ir.core import IRVizPolicy
from retriever.rt.buffer_engine import BufferEngineKind, create_buffer_engine
from retriever.rt.backend.dora.serde import serialize_arrow
from retriever.rt.backend.dora.serde import deserialize_arrow
from retriever.lib.rerun import log_value_from_env
from retriever.error import backend_error, ErrCode

import logging
logger = logging.getLogger(__name__)


class DoraSubscriber:
    """
    Event-based subscriber with temporal buffer.

    Extracts sender timestamps from dora event metadata.
    Implements Subscriber protocol.
    """

    def __init__(self, buffer_size: int, *, buffer_engine: BufferEngineKind = "python"):
        self._engine = create_buffer_engine(buffer_engine, buffer_size=buffer_size)
        self._arrival_flag = False

    def add_event(self, event: Dict[str, Any]) -> None:
        """Deserialize dora event and buffer with sender timestamp."""
        arrow = event.get("value")
        meta = event.get("metadata", {})

        if '_timestamp' not in meta:
            raise backend_error(
                ErrCode.DORA_EVENT_INVALID,
                "Dora event missing '_timestamp' in metadata"
            )

        timestamp = float(meta['_timestamp'])
        value = deserialize_arrow(arrow, meta)
        self._engine.push(timestamp, value)
        self._arrival_flag = True

    def new_arrival(self) -> bool:
        """Check if new data arrived, reset flag."""
        result = self._arrival_flag
        self._arrival_flag = False
        return result

    def empty(self) -> bool:
        """Check if buffer is empty."""
        return self._engine.empty()

    def get_all(self) -> TimedBuffer[Any]:
        """Get all buffered messages (non-destructive)."""
        return self._engine.events()

    def sample(self, adapter: Adapter, *, now: Optional[float] = None) -> Any:
        """Sample from the buffered events using an Adapter (Tier B.3 hook)."""
        return self._engine.sample(adapter, now=now)

    def clear(self) -> None:
        """Remove all buffered messages."""
        self._engine.clear()


class DoraPublisher:
    """
    Dora output publisher with timestamp transmission.

    Implements Publisher protocol.
    """

    def __init__(
        self,
        send_fn: callable,
        port_name: str,
        *,
        rerun_path: Optional[str] = None,
        rerun_policy: Optional[IRVizPolicy] = None,
    ):
        self._send_fn = send_fn
        self.port_name = port_name
        self.rerun_path = rerun_path
        self.rerun_policy = rerun_policy
        self._last_rerun_log_time: Optional[float] = None

    def put_one(self, value: Any, timestamp: float, block: bool = True) -> None:
        """Publish message with timestamp."""
        if self.rerun_path and self._should_log_rerun(timestamp):
            fields: Optional[Iterable[str]] = None
            if self.rerun_policy is not None:
                fields = self.rerun_policy.fields
            log_value_from_env(
                self.rerun_path,
                value,
                time_seconds=timestamp,
                fields=fields,
            )

        arrow, metadata = serialize_arrow(value)
        metadata['_timestamp'] = str(timestamp)

        try:
            self._send_fn(self.port_name, arrow, metadata)
        except Exception as e:
            raise backend_error(
                ErrCode.DORA_SET_OUTPUT_FAILED,
                f"Failed to send output [{self.port_name}]: {e}",
            )

    def _should_log_rerun(self, timestamp: float) -> bool:
        policy = self.rerun_policy
        if policy is None:
            return True
        if not policy.enabled:
            return False
        if policy.hz is None:
            return True
        if self._last_rerun_log_time is not None:
            if (timestamp - self._last_rerun_log_time) < (1.0 / policy.hz):
                return False
        self._last_rerun_log_time = timestamp
        return True
