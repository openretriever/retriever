from __future__ import annotations

import logging

import pytest

from retriever.flow import Flow, Latest, Pipeline, PipelineBuilder, Rate, Trigger, io
from retriever.ir.clock_algebra import (
    CoveringClock,
    activation_edges,
    covering_clock,
    same_instant_cycles,
)
from retriever.registry.pipeline import build_pipeline_flow, register_pipeline


@io
class Action:
    action: int


@io
class Observation:
    obs: int


@io
class Pulse:
    go: int


@io
class Gated:
    value: int


class Env(Flow[Action, Observation]):
    def step(self, input: Action) -> Observation:
        return Observation(obs=0)


class Controller(Flow[Observation, Action]):
    def step(self, input: Observation) -> Action:
        return Action(action=0)


class Ticker(Flow[None, Observation]):
    def step(self, _):  # type: ignore[override]
        return Observation(obs=1)


class Gate(Flow[Pulse, Gated]):
    def step(self, input: Pulse) -> Gated:
        return Gated(value=1)


def _two_rate_group() -> Pipeline:
    pipe = Pipeline("clock_algebra_two_rates")
    with pipe:
        (Ticker() @ Rate(hz=20)).named("a")
        (Ticker() @ Rate(hz=30)).named("b")
    return pipe


def test_covering_clock_of_20_and_30_hz_has_40_ticks_per_second():
    cover = covering_clock(_two_rate_group().validate())
    assert cover.rates_hz == (20.0, 30.0)
    assert cover.boundary_events == ()
    assert cover.is_static
    # 20 Hz gives 2 ticks per 0.1 s, 30 Hz gives 3, and they share t = 0: 4 ticks per 0.1 s.
    ticks = cover.ticks(0.0, 1.0)
    assert len(ticks) == 40
    assert ticks[:4] == pytest.approx([0.0, 1 / 30, 0.05, 2 / 30])
    assert str(cover) == "Cover[Rate(20 Hz) ∪ Rate(30 Hz)]"


def test_trigger_cycle_is_a_same_instant_cycle_and_is_logged(caplog):
    pipe = Pipeline("clock_algebra_trigger_cycle")
    env = Env() @ Trigger("action")
    ctrl = Controller() @ Trigger("obs")
    pipe.connect(env, ctrl, sync=Latest())
    pipe.connect(ctrl, env, sync=Latest())

    with caplog.at_level(logging.WARNING, logger="retriever.flow.builder"):
        ir = pipe.validate()

    cycles = same_instant_cycles(ir)
    assert len(cycles) == 1 and len(cycles[0]) == 2
    assert len(activation_edges(ir)) == 2
    assert any("Same-instant cycle" in r.getMessage() for r in caplog.records)


def test_rate_clock_on_one_node_breaks_the_same_instant_cycle(caplog):
    pipe = Pipeline("clock_algebra_rate_breaks_cycle")
    env = Env() @ Rate(hz=10)
    ctrl = Controller() @ Trigger("obs")
    pipe.connect(env, ctrl, sync=Latest())
    pipe.connect(ctrl, env, sync=Latest())

    with caplog.at_level(logging.WARNING, logger="retriever.flow.builder"):
        ir = pipe.validate()

    assert ir.topology.has_cycle is True  # still a feedback loop
    assert same_instant_cycles(ir) == []  # but not a same-instant one
    assert not any("Same-instant cycle" in r.getMessage() for r in caplog.records)
    assert covering_clock(ir).rates_hz == (10.0,)


def test_wrapper_exposes_covering_clock_with_boundary_trigger():
    @register_pipeline("clock_algebra_gate_group", overwrite=True)
    def build():
        with PipelineBuilder("clock_algebra_gate_group") as ctx:
            (Ticker() @ Rate(hz=5)).named("ticker")
            (Gate() @ Trigger("go")).named("gate")
            return ctx

    flow = build_pipeline_flow("clock_algebra_gate_group")
    try:
        cover = flow.covering_clock
        assert isinstance(cover, CoveringClock)
        assert cover.rates_hz == (5.0,)
        assert cover.boundary_events == ("go",)
        assert flow.same_instant_cycles == []
        assert flow.viz_metadata()["covering_clock"] == "Cover[Rate(5 Hz) ∪ events(go)]"
    finally:
        flow.finalize()


def test_ticks_window_and_empty_cover():
    assert CoveringClock().ticks(0.0, 1.0) == []
    assert CoveringClock(rates_hz=(10.0,)).ticks(0.25, 0.5) == pytest.approx([0.3, 0.4])
    assert CoveringClock(rates_hz=(10.0,)).ticks(0.5, 0.5) == []
    assert str(CoveringClock()) == "Cover[∅]"
    # Adjacent windows never share a tick, also for slow clocks.
    slow = CoveringClock(rates_hz=(0.001,))
    assert slow.ticks(0.0, 1000.0) == pytest.approx([0.0])
    assert slow.ticks(1000.0, 2000.0) == pytest.approx([1000.0])
    assert CoveringClock(rates_hz=(0.0, 10.0)).ticks(0.0, 0.2) == pytest.approx([0.0, 0.1])
