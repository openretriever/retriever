"""
Clock system for flow execution timing.

Clocks define when a flow executes:
- Rate: Periodic execution at fixed frequency
- Trigger: Event-driven execution on field arrival
- Hybrid: Combined periodic and event-driven execution
"""

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, Union
from retriever.flow.types import EventStream, TimedBuffer

if TYPE_CHECKING:
    from retriever.flow.base import Flow
    from retriever.flow.temporal import TemporalFlow


class Clock(ABC):
    """
    Abstract base class for execution clocks.

    Clocks determine when flows execute in the system.
    """

    def __rmatmul__(self, flow: 'Flow') -> 'TemporalFlow':
        """
        Enable flow @ clock syntax.

        Called when: flow @ clock
        Returns: FlowHandle with FlowConfig containing this clock
        """
        from retriever.flow.config import FlowConfig
        from retriever.flow.temporal import TemporalFlow
        return TemporalFlow(flow=flow, config=FlowConfig(clock=self))


@dataclass(init=False)
class Rate(Clock):
    """
    Periodic clock - executes at fixed frequency.
    
    Attributes:
        hz: Frequency in Hertz (executions per second)
        
    Lag policy:
        `on_lag` defines what happens if execution cannot keep up with `hz`.
        See `docs/handbook.md` (Rate lag policy section).
    """
    hz: float
    on_lag: str = "warn"

    def __init__(
        self,
        hz: float,
        *,
        on_lag: str = "warn",
    ):
        """
        Args:
            hz: Frequency in Hertz
            on_lag: What to do if the flow can't keep up with the target rate:
                - "warn" (default): skip missed ticks + warn (best-effort / realtime)
                - "drop": skip missed ticks (quiet)
                - "catch_up": execute every tick eventually (simulation-style)
                - "error": raise if lagging by >= 1 tick (aliases: "panic", "raise", "strict")
        """
        from retriever.error import FlowError, ErrCode

        self.hz = hz
        self.on_lag = self._normalize_on_lag(on_lag)

        if self.hz <= 0:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Rate hz must be positive",
                hz=self.hz
            )

        allowed = {"drop", "catch_up", "warn", "error"}
        if self.on_lag not in allowed:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Invalid Rate on_lag policy",
                on_lag=self.on_lag,
                allowed=sorted(allowed),
            )

    @staticmethod
    def _normalize_on_lag(policy: str) -> str:
        """
        Normalize `on_lag` aliases to a canonical policy string.

        Canonical values:
          - drop
          - warn
          - error
          - catch_up
        
        Aliases (accepted):
          - panic/raise/strict -> error
          - catchup/catch-up -> catch_up
        """
        p = str(policy).strip()
        p = p.replace("-", "_")
        p = p.lower()

        if p in {"panic", "raise", "strict"}:
            return "error"
        if p == "catchup":
            return "catch_up"
        return p

    @property
    def interval(self) -> float:
        """Interval in seconds between executions"""
        return 1.0 / self.hz

    def __repr__(self) -> str:
        base = f"Rate(hz={self.hz})"
        if self.on_lag != "warn":
            return f"{base[:-1]}, on_lag={self.on_lag!r})"
        return base


@dataclass(init=False)
class Tick(Rate):
    """
    Periodic clock that does not sample any inputs (tick-only).

    Equivalent to: `Rate(hz=..., fields=[])`
    """

    def __init__(self, hz: float, *, on_lag: str = "warn"):
        super().__init__(hz=hz, fields=[], on_lag=on_lag)

    def __repr__(self) -> str:
        if self.on_lag != "warn":
            return f"Tick(hz={self.hz}, on_lag={self.on_lag!r})"
        return f"Tick(hz={self.hz})"


@dataclass(init=False)
class Trigger(Clock):
    """
    Event-driven clock - executes when specified field data arrives.

    Attributes:
        fields: List of input field names that trigger execution
    """
    fields: List[str]

    def __init__(
        self,
        *on_fields: str,
    ):
        """
        Args:
            *on_fields: Positional field names
        """
        from retriever.error import FlowError, ErrCode

        selector = list(on_fields)

        if not selector:
            # Maybe allow empty if we default to "any input"? 
            # For now, let's keep it strict or error, as Trigger() with nothing is ambiguous.
            # Assuming "all inputs" logic belongs to connections, Trigger usually means SPECIFIC events.
            pass

        if not selector:
             raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Trigger requires at least one field name (e.g. Trigger('lidar'))",
            )
            
        self.fields = [str(x) for x in selector]

    def __repr__(self) -> str:
        return f"Trigger({', '.join(repr(f) for f in self.fields)})"


@dataclass(init=False)
class Hybrid(Clock):
    """
    Combined periodic and event-driven clock.

    Executes periodically at hz frequency OR immediately when trigger fields arrive.

    Attributes:
        hz: Frequency in Hertz for periodic execution
        trigger_fields: List of input fields that trigger immediate execution
        
    Note:
        `rate_fields` removed. Hybrid rate ticks now sample *all* connected inputs (implicit `...`)
        consistent with the new `Rate` logic.
    """
    hz: float
    trigger_fields: List[str]
    on_lag: str = "warn"

    def __init__(
        self,
        hz: float,
        # We can accept trigger fields either as *args or explicit list?
        # Let's keep it simple: required `trigger` kwarg for clarity in hybrid.
        *,
        trigger: Optional[List[str]] = None,
        on_lag: str = "warn",
    ):
        """
        Args:
            hz: Frequency in Hertz for periodic execution
            trigger: List of fields that trigger immediate execution
            on_lag: Lag policy
        """
        from retriever.error import FlowError, ErrCode
        
        self.hz = hz
        
        if trigger is None or not trigger:
             raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Hybrid clock requires explicit `trigger` fields (e.g. Hybrid(hz=10, trigger=['lidar']))",
            )
            
        # Normalize trigger
        if isinstance(trigger, str):
            self.trigger_fields = [trigger]
        else:
            self.trigger_fields = [str(x) for x in trigger]
            
        self.on_lag = Rate._normalize_on_lag(on_lag)

        if self.hz <= 0:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Hybrid hz must be positive",
                hz=self.hz
            )

        allowed = {"drop", "catch_up", "warn", "error"}
        if self.on_lag not in allowed:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Invalid Hybrid on_lag policy",
                on_lag=self.on_lag,
                allowed=sorted(allowed),
            )

    @property
    def interval(self) -> float:
        """Interval in seconds between periodic executions"""
        return 1.0 / self.hz

    def __repr__(self) -> str:
        base = f"Hybrid(hz={self.hz}, trigger={self.trigger_fields})"
        if self.on_lag != "warn":
            return f"{base[:-1]}, on_lag={self.on_lag!r})"
        return base


@dataclass(init=False)
class Synchronized(Trigger):
    """
    Synchronized execution - executes only when ALL specified fields have matching timestamps.
    
    This acts like an AND gate on input arrival, enforced by timestamp equality (within tolerance).
    """
    tolerance: float
    
    def __init__(
        self,
        *on_fields: str,
        tolerance: float = 1e-5,
        fields: Optional[Any] = None,
        on: Optional[Any] = None,
    ):
        super().__init__(*on_fields, fields=fields, on=on)
        self.tolerance = tolerance
        
    def __repr__(self) -> str:
        return f"Synchronized(on={self.fields}, tol={self.tolerance})"


class DefaultRate(Clock):
    """
    Uses the Flow's rate_config.default_rate.
    
    Raises FlowError at wiring time if:
    - Flow has no rate_config or rate_config.default_rate is not set
    
    Example:
        class CameraFlow(Flow[None, Image]):
            rate_config = FlowRateConfig(
                default_rate=30.0,
                rate_range=(10.0, 60.0),
            )
            
        camera = CameraFlow() @ DefaultRate()  # Uses 30 Hz
    """
    
    def __rmatmul__(self, flow: 'Flow') -> 'TemporalFlow':
        """
        Called when: flow @ DefaultRate()
        
        Reads default_rate from Flow.rate_config and creates a Rate clock.
        """
        from retriever.error import FlowError, ErrCode
        from retriever.flow.config import FlowConfig
        from retriever.flow.temporal import TemporalFlow
        
        flow_cls = type(flow)
        rate_config = getattr(flow_cls, 'rate_config', None)
        
        if rate_config is None or rate_config.default_rate is None:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                f"{flow_cls.__name__} has no rate_config.default_rate defined. "
                f"Either set `rate_config = FlowRateConfig(default_rate=...)` or use Rate(hz=...)",
            )
        
        default_hz = rate_config.default_rate
        
        # Create a standard Rate clock with the default hz
        rate_clock = Rate(hz=default_hz)
        return TemporalFlow(flow=flow, config=FlowConfig(clock=rate_clock))

    def __repr__(self) -> str:
        return "DefaultRate()"


@dataclass(init=False)
class AdaptiveRate(Clock):
    """
    Adjusts execution rate based on step() duration.
    
    If step() takes longer than target period, slows down (respecting min_hz).
    If step() completes faster, speeds up (respecting max_hz).
    
    Range is validated at wiring time against Flow.rate_config.rate_range if:
    - rate_config.enforce_range is True, or
    - AdaptiveRate range exceeds rate_config.rate_range
    
    Example:
        camera = CameraFlow() @ AdaptiveRate(target=30, min=10, max=60)
    """
    target_hz: float
    min_hz: float
    max_hz: float
    
    def __init__(self, target: float, min: float, max: float):
        """
        Args:
            target: Target frequency in Hz (starting point)
            min: Minimum frequency in Hz (floor when slowing down)
            max: Maximum frequency in Hz (ceiling when speeding up)
        """
        from retriever.error import FlowError, ErrCode
        
        if min <= 0 or max <= 0 or target <= 0:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "AdaptiveRate hz values must be positive",
                target=target, min=min, max=max,
            )
        
        if not (min <= target <= max):
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                f"AdaptiveRate target ({target}) must be between min ({min}) and max ({max})",
            )
        
        self.target_hz = target
        self.min_hz = min
        self.max_hz = max
    
    def __rmatmul__(self, flow: 'Flow') -> 'TemporalFlow':
        """
        Called when: flow @ AdaptiveRate(...)
        
        Validates against Flow.rate_config.rate_range if enforce_range=True.
        """
        from retriever.error import FlowError, ErrCode
        from retriever.flow.config import FlowConfig
        from retriever.flow.temporal import TemporalFlow
        
        flow_cls = type(flow)
        rate_config = getattr(flow_cls, 'rate_config', None)
        
        if rate_config is not None:
            # Check enforce_default - if True, only DefaultRate allowed
            if rate_config.enforce_default:
                raise FlowError(
                    ErrCode.FLOW_CLOCK_INVALID,
                    f"{flow_cls.__name__} has enforce_default=True. "
                    f"Use DefaultRate() instead of AdaptiveRate().",
                )
            
            # Check enforce_range - adaptive rate must fit within range
            if rate_config.enforce_range and rate_config.rate_range is not None:
                flow_min, flow_max = rate_config.rate_range
                if self.min_hz < flow_min or self.max_hz > flow_max:
                    raise FlowError(
                        ErrCode.FLOW_CLOCK_INVALID,
                        f"AdaptiveRate range [{self.min_hz}, {self.max_hz}] exceeds "
                        f"{flow_cls.__name__}.rate_config.rate_range ({flow_min}, {flow_max})",
                    )
        
        return TemporalFlow(flow=flow, config=FlowConfig(clock=self))
    
    @property
    def interval(self) -> float:
        """Current target interval (starting point before adaptation)."""
        return 1.0 / self.target_hz

    def __repr__(self) -> str:
        return f"AdaptiveRate(target={self.target_hz}, min={self.min_hz}, max={self.max_hz})"


@dataclass(init=False)
class EventClock(Clock):
    """
    FRP Event-driven clock.

    Executes whenever the provided `EventStream` emits an event.
    
    This is highly flexible, allowing execution on:
    - User interactions (clicks)
    - Sensor thresholds (via `stream.filter(...)`)
    - Combined events (via `stream.merge(...)`)
    
    Dora Support:
    - Maps to standard Dora input triggers.
    """
    stream: EventStream

    def __init__(self, stream: EventStream):
        self.stream = stream

    def __repr__(self) -> str:
        return "EventClock(stream=...)"


@dataclass(init=False)
class TimelineClock(Clock):
    """
    Schedule-driven clock.

    Executes only at specific timestamps provided by a list or TimedBuffer.
    
    This is useful for:
    - Replaying recorded event logs (use timestamps from log)
    - deterministic testing (e.g. "run at t=0.1, t=0.5, t=1.0")
    - sparsely scheduled tasks
    
    Attributes:
        timestamps: List of relative timestamps (seconds from start) when flow should run.
        
    Dora Support:
    - This would map to a series of one-shot timers or a complex timer schedule.
    """
    timestamps: List[float]

    def __init__(self, timestamps: Union[List[float], TimedBuffer]):
        from retriever.error import FlowError, ErrCode
        
        # Extract timestamps if given a TimedBuffer
        if hasattr(timestamps, 'events'): # is an EventStream/buffer-like
             # If it's a TimedBuffer (list), iterate it directly
             # If it's a generic stream, we can't know future times! 
             # So we assume it's an iterable of (ts, val) or just list of floats.
             pass

        data = []
        if isinstance(timestamps, list):
             # Check if it's [float] or [(float, val)]
             if not timestamps:
                 data = []
             elif isinstance(timestamps[0], (int, float)):
                 data = sorted(list(timestamps))
             elif isinstance(timestamps[0], (tuple, list)) and len(timestamps[0]) >= 1:
                 # Assume (ts, val) tuples from TimedBuffer
                 data = sorted([item[0] for item in timestamps])
        
        self.timestamps = data

    def __repr__(self) -> str:
        count = len(self.timestamps)
        fmt = f"[{self.timestamps[0]:.2f}, ...]" if count > 0 else "[]"
        return f"TimelineClock({count} ticks: {fmt})"
