"""
MPChannel - Queue-based channel implementation for multiprocessing backend.

Wraps multiprocessing.Queue and maintains temporal buffer for history.
"""

from multiprocessing import Queue
from multiprocessing.connection import Connection
from queue import Empty
from typing import Any, List, Optional

from retriever.flow.adapter import Adapter
from retriever.flow.frp import EventBuffer
from retriever.rt.buffer_engine import BufferEngineKind, create_buffer_engine


class MPChannel:
    """
    Queue-based channel with temporal buffer.

    Two-tier architecture:
    - IPC Queue(s): Cross-process transport (supports multiple for fan-in)
    - temporal Buffer: Per-consumer history

    Implements Publisher/Subscriber protocols.
    """

    def __init__(self, queue: Queue, buffer_size: int, *, buffer_engine: BufferEngineKind = "python"):
        """
        Initialize MPChannel.

        Args:
            queue: multiprocessing.Queue for IPC
            buffer_size: temporal buffer capacity
        """
        self._queues = [queue]
        self._engine = create_buffer_engine(buffer_engine, buffer_size=buffer_size)
        self.arrival_flag = False

    @property
    def queue(self) -> Queue:
        """Primary queue for put_one() (output side)."""
        return self._queues[0]

    def add_queue(self, queue: Queue) -> None:
        """Add another queue for fan-in input."""
        self._queues.append(queue)

    @property
    def reader(self) -> Optional[Connection]:
        """
        Primary reader connection for use with connection.wait().

        Returns:
            Connection object for select/poll, or None if unavailable
        """
        return getattr(self.queue, '_reader', None)

    @property
    def readers(self) -> List[Optional[Connection]]:
        """
        All reader connections for fan-in support.

        Returns:
            List of Connection objects for all queues
        """
        return [getattr(q, '_reader', None) for q in self._queues]

    def drain(self) -> None:
        """Pull all messages from ALL Queues into temporal buffer."""
        for queue in self._queues:
            while True:
                try:
                    item = queue.get_nowait()
                    ts, value = item
                    self._engine.push(ts, value)
                    self.arrival_flag = True
                except Empty:
                    break

    def new_arrival(self) -> bool:
        """Check if new data arrived."""
        result = self.arrival_flag
        self.arrival_flag = False
        return result

    def empty(self) -> bool:
        """Check if buffer has messages."""
        return self._engine.empty()

    def put_one(self, value: Any, timestamp: float, block: bool = True) -> None:
        """
        Publish message with timestamp.

        Args:
            value: Message value
            timestamp: Sender timestamp
            block: Block until space available
        """
        self.queue.put((timestamp, value), block=block)

    def get_all(self) -> EventBuffer[Any]:
        """
        Get all buffered messages (non-destructive).

        Returns:
            List of (timestamp, value) tuples
        """
        return self._engine.events()

    def sample(self, adapter: Adapter, *, now: Optional[float] = None) -> Any:
        """Sample from the buffered events using an Adapter (Tier B.3 hook)."""
        return self._engine.sample(adapter, now=now)

    def clear(self) -> None:
        """Remove all buffered messages."""
        self._engine.clear()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"MPChannel(queue_size={self.queue.qsize}, buffer_size={len(self.get_all())})"
