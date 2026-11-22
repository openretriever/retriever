import warnings
from time import perf_counter

import pytest

from retriever.error import FlowError
from retriever.flow import Flow, Latest, Pipeline, Prev, Rate, Trigger, io
from retriever.ir.core import IR
from retriever.registry.pipeline import build_pipeline_flow, register_pipeline


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


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("sample_only_trigger", [False, True])
def test_prev_feedback_across_pipeline_flow_boundary(reverse, sample_only_trigger):
    trace = []
    resets = []

    class Consumer(Flow[Value, Value]):
        def reset(self):
            resets.append("consumer")

        def step(self, inputs):
            trace.append(("consumer", inputs.value))
            return Value(value=(inputs.value or 0) + 1)

    class Producer(Flow[Value, Value]):
        def step(self, inputs):
            trace.append(("producer", inputs.value))
            return Value(value=(inputs.value or 0) + 10)

    clock = Trigger("value") if sample_only_trigger else Rate(10)

    @register_pipeline("strict_boundary_consumer", overwrite=True)
    def build():
        with Pipeline("consumer_group") as inner:
            (Consumer() @ clock).named("consumer")
        return inner

    def run(wrapped):
        with Pipeline(cycles="strict") as pipe:
            def make_consumer():
                flow = build_pipeline_flow("strict_boundary_consumer") if wrapped else Consumer()
                return (flow @ (Rate(10) if wrapped else clock)).named("consumer")

            if reverse:
                producer = (Producer() @ Rate(30)).named("producer")
                consumer = make_consumer()
            else:
                consumer = make_consumer()
                producer = (Producer() @ Rate(30)).named("producer")
            consumer.then(producer, sync=Latest())
            producer.then(consumer, sync=Prev(initial=7))

        result = []
        try:
            # Parent-owned history survives inner initialization, but not a parent reset.
            pipe.inject_input(consumer, "value", 90, timestamp=-1)
            trace.clear()
            resets.clear()
            pipe.step(now=0)
            assert resets == ["consumer"]
            assert trace == ([("producer", None)] if sample_only_trigger else
                             [("consumer", 90), ("producer", 91)])
            pipe.reset_stepper()
            for t in (0, 1 / 30, 2 / 30, 0.1, 3 / 30, 4 / 30):
                trace.clear()
                pipe.step(now=t)
                result.append(trace.copy())
        finally:
            pipe.close_stepper()
        return result

    flat = run(False)
    if sample_only_trigger:
        assert flat == [[("producer", None)]] * 6
    else:
        assert flat == [[("consumer", v), ("producer", v + 1)] for v in (7, 18, 29, 40, 40, 51)]
    assert run(True) == flat


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
    with pytest.warns(UserWarning) as pair_warnings:
        assert pair.step(now=1).executed == ["B", "A"]
    message = str(pair_warnings[0].message)
    assert "backward edges in the legacy step order (candidates for sync=Prev())" in message
    assert "A.value -> B.value: pipe.connect(a, b, sync=Prev())" in message
    assert "pipe.connect(b, a" not in message


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


def test_injected_prev_never_wakes_and_reads_only_earlier_commits():
    p = Pipeline(cycles="strict")
    silent = (Add() @ Trigger("extra")).named("silent")
    sink = (Add() @ Trigger("value", "extra")).named("sink")
    p.connect(silent, sink, sync=Prev(buffer_size=1, initial=-7))

    def read(t, expected):
        p.inject_input(sink, "extra", 1, timestamp=t)
        s = p.step(now=t)
        assert s.executed == ["sink"]
        assert (s.inputs["sink"].value, s.inputs["sink"].extra) == (expected, 1)

    assert p.step(now=0).executed == []
    for t in (10, 11, 12):
        p.inject_input(sink, "value", t, timestamp=t)
    assert p.step(now=1).executed == []
    read(1, -7)
    p.inject_input(sink, "value", 5, timestamp=0.5)
    read(1, -7)  # Backdated, but committed at this tick.
    read(2, 5)
    for i in range(20):
        p.inject_input(sink, "value", i, timestamp=2)
    read(2, 5)  # A same-tick burst cannot evict the eligible sample.
    assert p.step(now=3).executed == []
    read(3, 19)
    read(10, 19)
    assert p.step(now=11).executed == []
    read(11, 10)
    p.reset()
    assert p.step(now=0).executed == []
    read(13, -7)  # Neither pending nor already-visible values survive reset.


def test_rate_10_and_rate_30_coincident_logical_ticks():
    p = Pipeline(cycles="strict")
    fast = (Source() @ Rate(30)).named("fast")
    slow = (Relay() @ Rate(10)).named("slow")
    p.connect(fast, slow, sync=Prev(buffer_size=1))
    # Rate flows execute per step here. Supply the two clocks' representations
    # of their shared instant explicitly, in both raw floating-point orders.
    ticks = (8 / 30, 9 / 30, 3 * 0.1, 9 / 30, 10 / 30)
    samples = [p.step(now=t) for t in ticks]
    assert all(s.executed == ["fast", "slow"] for s in samples)
    assert [s.inputs["slow"].value for s in samples] == [None, 1, 1, 1, 4]


@pytest.mark.parametrize("delay_return", [True, False])
def test_parallel_ports_keep_distinct_same_tick_dependencies(delay_return):
    p = Pipeline(cycles="strict")
    a, b = [(Add() @ Rate(10)).named(n) for n in ("A", "B")]
    p.connect(a, b, map={"value": "extra"}, sync=Prev())
    p.connect(a, b, sync=Latest())
    p.connect(b, a, sync=Prev() if delay_return else Latest())
    if not delay_return:
        with pytest.raises(FlowError, match="A -> B -> A"):
            p.validate()
        return
    steps = [p.step(now=t) for t in range(3)]
    assert all(s.executed == ["A", "B"] for s in steps)
    assert [(s.inputs["B"].value, s.inputs["B"].extra) for s in steps] == [
        (1, None), (3, 1), (6, 3),
    ]


@pytest.mark.parametrize("branch", [False, True])
def test_two_loops_sharing_one_node_keep_groups_and_trace(branch):
    p, a, b = feedback()
    c = (Add() @ Rate(10)).named("C")
    p.connect(a, c, sync=Latest())
    p.connect(c, a, map={"value": "extra"}, sync=Prev())
    if branch:
        sink = (Relay() @ Rate(10)).named("observer")
        p.connect(b, sink, sync=Latest())
    graph = p.get_graph()
    loops = {frozenset(g) for g in graph.get_cycles()}
    assert loops == {frozenset(("A", "B", "C"))}
    assert loops == {frozenset(g) for g in graph.get_topological_groups() if len(g) > 1}
    assert graph.get_topological_groups() == p.validate().topology.groups
    for t, expected in enumerate(((1, 2, 2), (5, 6, 6), (13, 14, 14))):
        s = p.step(now=t)
        assert set(s.executed) == ({"A", "B", "C", "observer"} if branch else {"A", "B", "C"})
        assert tuple(s.outputs[n].value for n in ("A", "B", "C")) == expected
