from __future__ import annotations

from dataclasses import dataclass

from retriever.core.flow import Flow, FlowContext, Rate, Trigger, flow_io, Latest
from retriever.core.flow.adapter import Events, Window
from retriever.core.ir import validate
from retriever.core.rt.signal import Signal


def test_window_adapter_respects_now():
    adapter = Window(buffer_size=10, duration=1.0, agg="first")
    buf = [(0.0, "old"), (99.2, "a"), (99.8, "b")]
    assert adapter.sample(buf, now=100.0) == "a"


def test_events_adapter_can_filter_by_duration_and_strip_timestamps():
    adapter = Events(buffer_size=10, duration=1.0, include_timestamps=False)
    buf = [(0.0, "old"), (99.2, "a"), (99.8, "b")]
    assert adapter.sample(buf, now=100.0) == ["a", "b"]


def test_signal_sampling_passes_now_to_adapter():
    class StubSubscriber:
        def __init__(self, buf):
            self._buf = list(buf)

        def new_arrival(self) -> bool:
            return True

        def get_all(self):
            return list(self._buf)

        def empty(self) -> bool:
            return len(self._buf) == 0

        def clear(self) -> None:
            self._buf = []

    @flow_io
    @dataclass
    class In:
        events: list[tuple[float, str]]

    subs = {"events": StubSubscriber([(0.0, "old"), (99.2, "a"), (99.8, "b")])}
    adapters = {"events": Events(buffer_size=10, duration=1.0, include_timestamps=True)}

    s = Signal(subs, fields_filter=["..."], now=100.0).sample(In, adapters, now=100.0)
    assert s.instance.events == [(99.2, "a"), (99.8, "b")]


def test_flowhandle_rshift_is_then_alias():
    @flow_io
    @dataclass
    class AOut:
        value: int

    @flow_io
    @dataclass
    class BOut:
        value: int

    class A(Flow[None, AOut]):
        def run(self, _):  # type: ignore[override]
            return AOut(value=1)

    class B(Flow[AOut, BOut]):
        def run(self, input: AOut) -> BOut:
            return BOut(value=input.value + 1)

    with FlowContext("test_flowhandle_rshift_is_then_alias") as ctx:
        a = A() @ Rate(hz=10)
        b = B() @ Trigger(fields=["value"])
        a >> b

        ir = validate(ctx)

    assert len(ir.nodes) == 2
    assert len(ir.edges) == 1

