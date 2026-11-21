import warnings
from time import perf_counter

import pytest

from retriever.error import FlowError
from retriever.flow import Flow, Latest, Pipeline, Prev, Rate, Trigger, io
from retriever.ir.core import IR


@io
class Value:
    value: int


@io
class Inputs:
    value: int
    extra: int


class Add(Flow[Inputs, Value]):
    def step(self, inputs):
        return Value(value=(inputs.value or 0) + (inputs.extra or 0) + 1)


class Source(Flow[None, Value]):
    def reset(self):
        self.i = 0

    def step(self, _):
        self.i += 1
        return Value(value=self.i)


class Relay(Flow[Value, Value]):
    def step(self, inputs):
        return Value(value=inputs.value)


def feedback(*, reverse=False, shape=False, delay=True, mode="strict"):
    pipe = Pipeline(cycles=mode)
    a, b = [(Add() @ Rate(10)).named(n) for n in ("A", "B")]
    edges = [(a, b, Latest()), (b, a, Prev() if delay else Latest())]
    for src, dst, sync in (reversed(edges) if reverse else edges):
        pipe.connect(src, dst, sync=sync)
    if shape:
        # A second feedback route: B -> C -> A. C reads B without a delay.
        c = (Add() @ Rate(10)).named("C")
        pipe.connect(b, c, sync=Latest())
        pipe.connect(c, a, map={"value": "extra"}, sync=Prev() if delay else Latest())
    return pipe, a, b


def test_reject_same_tick_cycle():
    pipe, _, _ = feedback(delay=False)
    with pytest.raises(FlowError, match=r"A -> B -> A.*Prev\(\)"):
        pipe.validate()


def test_warn_per_group_and_keep_legacy_order():
    pipe, _, _ = feedback(delay=False, shape=True, mode="warn")
    with pytest.warns(UserWarning) as seen:
        pipe.validate()
    assert len(seen) == 1
    assert "A -> B -> A" in str(seen[0].message)
    pair, _, _ = feedback(delay=False, mode="warn")
    with pytest.warns(UserWarning):
        assert pair.step(now=1).executed == ["B", "A"]


def test_unmarked_cycle_still_builds_and_steps_as_before():
    class Counter(Flow[Value, Value]):
        def reset(self):
            self.k = 0

        def step(self, inputs):
            self.k += 1
            return Value(value=10 * self.k)

    class Echo(Flow[Value, Value]):
        def step(self, inputs):
            return Value(value=-1 if inputs.value is None else inputs.value + 1)

    with Pipeline("legacy_loop") as pipe:
        a = (Counter() @ Rate(10)).named("A")
        b = (Echo() @ Rate(10)).named("B")
        a.then(b, sync=Latest())
        b.then(a, sync=Latest())

    steps = [pipe.step(now=k * 0.1) for k in range(4)]
    assert [s.inputs["B"].value for s in steps] == [None, 10, 20, 30]
    assert [s.inputs["A"].value for s in steps] == [-1, 11, 21, 31]


def test_dense_feedback_group_reports_one_witness(monkeypatch):
    def complete_graph(mode):
        pipe = Pipeline(cycles=mode)
        nodes = [(Add() @ Rate(10)).named(f"N{i:02}") for i in range(12)]
        for src in nodes:
            for dst in nodes:
                if src is not dst:
                    pipe.connect(src, dst, sync=Latest())
        return pipe

    messages = []

    def capture(message, *args, **kwargs):
        # Fail on the second warning rather than collecting millions on regression.
        assert not messages, "more than one warning for a single feedback group"
        messages.append(str(message))

    legacy = complete_graph("warn")
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        monkeypatch.setattr(warnings, "showwarning", capture)
        start = perf_counter()
        ir = legacy.validate()
        assert perf_counter() - start < 5
    assert len(ir.nodes) == 12 and len(ir.edges) == 132
    assert len(messages) == 1 and "N00 -> N01 -> N00" in messages[0]

    strict = complete_graph("strict")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(FlowError, match=r"N00 -> N01 -> N00.*Prev\(\)"):
            strict.validate()


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("shape", [False, True])
def test_feedback_uses_only_earlier_commits(reverse, shape):
    pipe, _, _ = feedback(reverse=reverse, shape=shape)
    ir = pipe.validate()
    assert IR.from_json(ir.to_json()).topology == ir.topology
    # Two calls at the same timestamp must not advance the delay.
    got = [pipe.step(now=t) for t in (1, 1, 2, 3)]
    expected = [(1, 2), (1, 2), (6, 7), (16, 17)] if shape else [(1, 2), (1, 2), (3, 4), (5, 6)]
    assert [(s.outputs["A"].value, s.outputs["B"].value) for s in got] == expected
    assert [s.inputs["A"].value for s in got] == [None, None, 2, expected[2][1]]


def test_prev_requires_consumer_time_even_with_an_empty_buffer():
    for events in ([], [(1, 11)]):
        with pytest.raises(ValueError, match="explicit consumer time"):
            Prev()(events)
    with pytest.raises(IndexError, match="no event before"):
        Prev()([(1, 11)], now=1)


def test_delayed_trigger_and_strict_timestamp_cutoff():
    p = Pipeline(cycles="strict")
    a = (Source() @ Rate(10)).named("A")
    b = (Add() @ Trigger("value")).named("B")
    p.connect(a, b, sync=Prev())
    assert [p.step(now=t).executed for t in (1, 1, 2)] == [["A"], ["A"], ["A"]]
    assert Prev()([(3, 30), (1, 10), (1, 11), (2, 20)], now=2) == 11


def test_prev_subclass_supplies_initial_without_triggering():
    from retriever.flow.adapter import register_adapter

    @register_adapter("fixture_initialized_delay")
    class InitializedDelay(Prev):
        pass

    pipe = Pipeline(cycles="strict")
    a = (Add() @ Rate(10)).named("A")
    b = (Add() @ Trigger("value")).named("B")
    pipe.connect(a, b, sync=Latest())
    pipe.connect(b, a, sync=InitializedDelay(initial=0))
    steps = [pipe.step(now=t) for t in (1, 2)]
    assert [s.executed for s in steps] == [["A", "B"], ["A", "B"]]
    assert [s.inputs["A"].value for s in steps] == [0, 2]


def test_strict_rejects_feedback_with_no_clock_driven_node():
    pipe = Pipeline(cycles="strict")
    a, b = [(Add() @ Trigger("value")).named(n) for n in ("A", "B")]
    pipe.connect(a, b, sync=Latest())
    pipe.connect(b, a, sync=Prev(initial=3))
    with pytest.raises(FlowError, match="A, B needs a clock-driven node"):
        pipe.validate()


def test_record_replay_recomputes_both_feedback_nodes(tmp_path):
    def wired(reverse):
        p, a, _ = feedback(reverse=reverse)
        src = (Source() @ Rate(10)).named("drive")
        p.connect(src, a, map={"value": "extra"}, sync=Latest())
        return p, src

    live, src = wired(False)
    path = tmp_path / "drive.pkl.gz"
    live.record(src, path, steps=4, dt=0.1)
    reference, _ = wired(False)
    replay, src = wired(True)
    replay.replay(src, path=path)
    for expected in [(2, 3), (6, 7), (11, 12), (17, 18)]:
        for p in (reference, replay):
            outputs = p.step(dt=0.1).outputs
            assert (outputs["A"].value, outputs["B"].value) == expected


def test_self_connection_remains_invalid():
    pipe = Pipeline(cycles="strict")
    a = Add() @ Rate(10)
    with pytest.raises(FlowError, match="itself"):
        pipe.connect(a, a, sync=Prev())


def test_marking_one_cycle_does_not_hide_another_in_the_same_group():
    p, a, b = feedback()
    c = (Add() @ Rate(10)).named("C")
    p.connect(b, c, sync=Latest())
    p.connect(c, a, map={"value": "extra"}, sync=Latest())
    with pytest.raises(FlowError, match="A -> B -> C -> A"):
        p.validate()


@pytest.mark.parametrize("relay", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_equivalent_feedback_paths_give_the_same_trace(relay, reverse):
    p = Pipeline(cycles="strict")
    a, b = [(Add() @ Rate(10)).named(n) for n in ("A", "B")]
    edges = [(a, b, Latest())]
    if relay:
        c = (Relay() @ Rate(10)).named("C")
        edges += [(b, c, Latest()), (c, a, Prev())]
    else:
        edges.append((b, a, Prev()))
    for src, dst, sync in reversed(edges) if reverse else edges:
        p.connect(src, dst, sync=sync)
    for t in range(4):
        s = p.step(now=t)
        assert (s.outputs["A"].value, s.outputs["B"].value) == (2*t + 1, 2*t + 2)
