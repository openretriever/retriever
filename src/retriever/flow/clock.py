"""
Clock system for flow execution timing.

Clocks define when a flow executes:
- Rate: Periodic execution at fixed frequency
- Trigger: Event-driven execution on field arrival
- Hybrid: Combined periodic and event-driven execution
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from retriever.core.flow.base import Flow
    from retriever.core.flow.handle import FlowHandle


class Clock(ABC):
    """
    Abstract base class for execution clocks.

    Clocks determine when flows execute in the system.
    """

    def __rmatmul__(self, flow: 'Flow') -> 'FlowHandle':
        """
        Enable flow @ clock syntax.

        Called when: flow @ clock
        Returns: FlowHandle with FlowConfig containing this clock
        """
        from retriever.core.flow.config import FlowConfig
        from retriever.core.flow.handle import FlowHandle
        return FlowHandle(flow=flow, config=FlowConfig(clock=self))


@dataclass(init=False)
class Rate(Clock):
    """
    Periodic clock - executes at fixed frequency.

    Attributes:
        hz: Frequency in Hertz (executions per second)
        fields: Input fields to sample at each tick.
            - Default: ["..."] (sample all inputs)
            - []: sample no inputs (tick-only)
            - ["field_a", "field_b"]: sample specific fields

    Ergonomics:
        Prefer `sample=` over `fields=` when specifying which inputs to sample.
        `fields=` remains supported for backwards compatibility.

    Lag policy:
        `on_lag` defines what happens if execution cannot keep up with `hz`.
        See `docs/handbook.md` (Rate lag policy section).
    """
    hz: float
    fields: List[str] = field(default_factory=lambda: ["..."])
    on_lag: str = "warn"

    def __init__(
        self,
        hz: float,
        fields: Optional[Any] = None,
        *,
        sample: Optional[Any] = None,
        on_lag: str = "warn",
    ):
        """
        Args:
            hz: Frequency in Hertz
            fields: Backward-compatible alias for `sample`
            sample: Which input fields to sample
                - None / "all" / "*" / ...: sample all inputs
                - []: sample no inputs (tick-only)
                - "field": sample one field
                - ["field_a", ...]: sample specific fields
            on_lag: What to do if the flow can't keep up with the target rate:
                - "warn" (default): skip missed ticks + warn (best-effort / realtime)
                - "drop": skip missed ticks (quiet)
                - "catch_up": execute every tick eventually (simulation-style)
                - "error": raise if lagging by >= 1 tick (aliases: "panic", "raise", "strict")
        """
        from retriever.core.error import FlowError, ErrCode

        if fields is not None and sample is not None:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Provide only one of `sample` or `fields`",
                sample=sample,
                fields=fields,
            )

        selector = sample if sample is not None else fields
        normalized = self._normalize_sample(selector)

        self.hz = hz
        self.fields = normalized
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

    @staticmethod
    def _normalize_sample(selector: Optional[Any]) -> List[str]:
        if selector is None or selector is ...:
            return ["..."]

        if selector == "*" or selector == "all" or selector == "...":
            return ["..."]

        if isinstance(selector, str):
            return [selector]

        if isinstance(selector, (list, tuple, set)):
            return [str(x) for x in selector]

        raise TypeError(f"Unsupported sample selector: {selector!r}")

    @property
    def interval(self) -> float:
        """Interval in seconds between executions"""
        return 1.0 / self.hz

    def __repr__(self) -> str:
        if self.fields == ["..."]:
            base = f"Rate(hz={self.hz})"
        else:
            base = f"Rate(hz={self.hz}, sample={self.fields})"

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
        fields: Optional[Any] = None,
        on: Optional[Any] = None,
    ):
        """
        Args:
            *on_fields: Positional field names (ergonomic form)
            fields: Backward-compatible keyword form (list[str])
            on: Alias for `fields` (list[str] or str)
        """
        from retriever.core.error import FlowError, ErrCode

        if on_fields and (fields is not None or on is not None):
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Provide trigger fields either positionally OR via `on=`/`fields=`",
                on_fields=list(on_fields),
                fields=fields,
                on=on,
            )

        selector = list(on_fields) if on_fields else (on if on is not None else fields)

        if selector is None:
            normalized: List[str] = []
        elif isinstance(selector, str):
            normalized = [selector]
        elif isinstance(selector, (list, tuple, set)):
            normalized = [str(x) for x in selector]
        else:
            raise TypeError(f"Unsupported trigger selector: {selector!r}")

        self.fields = normalized

        if not self.fields:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Trigger fields cannot be empty",
                fields=self.fields
            )

    def __repr__(self) -> str:
        return f"Trigger(on={self.fields})"


@dataclass(init=False)
class Hybrid(Clock):
    """
    Combined periodic and event-driven clock.

    Executes periodically at hz frequency OR immediately when trigger fields arrive.

    Attributes:
        hz: Frequency in Hertz for periodic execution
        trigger_fields: List of input fields that trigger immediate execution
        rate_fields: Fields to sample on periodic ticks.
            - Default: ["..."] (sample all inputs)
            - []: sample no inputs on rate ticks
            - ["field_a", ...]: sample specific fields on rate ticks

        on_lag: What to do if periodic ticks can't keep up (same semantics as `Rate.on_lag`).
    """
    hz: float
    trigger_fields: List[str]
    rate_fields: List[str] = field(default_factory=lambda: ["..."])
    on_lag: str = "warn"

    def __init__(
        self,
        hz: float,
        trigger_fields: Any = None,
        rate_fields: Optional[Any] = None,
        *,
        trigger: Optional[Any] = None,
        sample: Optional[Any] = None,
        on_lag: str = "warn",
    ):
        """
        Args:
            hz: Frequency in Hertz for periodic execution
            trigger_fields: Backward-compatible positional/keyword trigger fields
            rate_fields: Backward-compatible rate sampling selector (list[str] or ...)
            trigger: Alias for `trigger_fields`
            sample: Alias for `rate_fields`
        """
        from retriever.core.error import FlowError, ErrCode

        if trigger is not None:
            trigger_fields = trigger

        if rate_fields is not None and sample is not None:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Provide only one of `sample` or `rate_fields`",
                sample=sample,
                rate_fields=rate_fields,
            )

        rate_selector = sample if sample is not None else rate_fields
        if rate_selector is None:
            rate_normalized = ["..."]
        elif rate_selector is ...:
            rate_normalized = ["..."]
        elif rate_selector == "*" or rate_selector == "all" or rate_selector == "...":
            rate_normalized = ["..."]
        elif isinstance(rate_selector, str):
            rate_normalized = [rate_selector]
        elif isinstance(rate_selector, (list, tuple, set)):
            rate_normalized = [str(x) for x in rate_selector]
        else:
            raise TypeError(f"Unsupported rate_fields selector: {rate_selector!r}")

        if trigger_fields is None:
            trigger_normalized: List[str] = []
        elif isinstance(trigger_fields, str):
            trigger_normalized = [trigger_fields]
        elif isinstance(trigger_fields, (list, tuple, set)):
            trigger_normalized = [str(x) for x in trigger_fields]
        else:
            raise TypeError(f"Unsupported trigger_fields selector: {trigger_fields!r}")

        self.hz = hz
        self.trigger_fields = trigger_normalized
        self.rate_fields = rate_normalized
        self.on_lag = Rate._normalize_on_lag(on_lag)

        if self.hz <= 0:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Hybrid hz must be positive",
                hz=self.hz
            )

        if not self.trigger_fields:
            raise FlowError(
                ErrCode.FLOW_CLOCK_INVALID,
                "Hybrid trigger_fields cannot be empty",
                trigger_fields=self.trigger_fields
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
        if self.rate_fields == ["..."]:
            base = f"Hybrid(hz={self.hz}, trigger={self.trigger_fields})"
        else:
            base = f"Hybrid(hz={self.hz}, trigger={self.trigger_fields}, sample={self.rate_fields})"

        if self.on_lag != "warn":
            return f"{base[:-1]}, on_lag={self.on_lag!r})"
        return base
