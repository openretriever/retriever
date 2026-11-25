"""Logical-time stepping: each Rate flow keeps its own rate (Pipeline.run_logical)."""
import pytest

from retriever.flow import Flow, Hybrid, Latest, Pipeline, Prev, Rate, Trigger, io
from retriever.registry.pipeline import build_pipeline_flow, register_pipeline


@io
class Value:
    value: int


class Source(Flow[None, Value]):
    def reset(self):
        self.i = 0

    def step(self, _):
        self.i += 1
        return Value(value=self.i)


class Relay(Flow[Value, Value]):
    def step(self, inputs):
        return Value(value=inputs.value)


def _counts(results, node):
    return sum(node in r.executed for r in results)


def test_run_logical_keeps_each_rate():
    with Pipeline() as pipe:
        fast = (Source() @ Rate(30)).named("fast")
        slow = (Relay() @ Rate(10)).named("slow")
        fast.then(slow, sync=Latest())
    res = pipe.run_logical(1.0)
    assert len(res) == 30  # covering ticks of Rate(30) ∪ Rate(10) in [0, 1)
    assert _counts(res, "fast") == 30
    assert _counts(res, "slow") == 10
    slow_times = [r.now for r in res if "slow" in r.executed]
    assert slow_times == pytest.approx([k / 10 for k in range(10)])
    # Same tick, dependency order: slow reads the value fast emitted at that tick.
    assert [r.inputs["slow"].value for r in res if "slow" in r.executed] == [1 + 3 * k for k in range(10)]


def test_run_logical_is_repeatable():
    def trace():
        with Pipeline() as pipe:
            fast = (Source() @ Rate(20)).named("fast")
            slow = (Relay() @ Rate(7)).named("slow")
            fast.then(slow, sync=Latest())
        return [(round(r.now, 9), tuple(r.executed),
                 r.outputs["slow"].value if "slow" in r.outputs else None)
                for r in pipe.run_logical(2.0)]

    assert trace() == trace()


def test_trigger_flow_runs_on_arrivals_in_logical_time():
    with Pipeline() as pipe:
        fast = (Source() @ Rate(10)).named("fast")
        echo = (Relay() @ Trigger("value")).named("echo")
        fast.then(echo, sync=Latest())
    res = pipe.run_logical(1.0)
    assert _counts(res, "echo") == 10


def test_feedback_with_prev_in_logical_time():
    class Acc(Flow[Value, Value]):
        def step(self, inputs):
            return Value(value=(inputs.value or 0) + 1)

    with Pipeline() as pipe:
        a = (Acc() @ Rate(10)).named("a")
        b = (Relay() @ Rate(5)).named("b")
        a.then(b, sync=Latest())
        b.then(a, sync=Prev(initial=0))
    res = pipe.run_logical(1.0)
    assert _counts(res, "a") == 10 and _counts(res, "b") == 5


def test_nested_group_inner_rate_is_kept():
    @register_pipeline("logical_time_inner_group", overwrite=True)
    def build():
        with Pipeline("inner") as inner:
            (Source() @ Rate(5)).named("src")
        return inner

    with Pipeline() as pipe:
        group = (build_pipeline_flow("logical_time_inner_group") @ Rate(10)).named("group")
        (Relay() @ Rate(10)).named("other")
    res = pipe.run_logical(1.0)
    inner_values = [r.outputs["group"].value for r in res
                    if "group" in r.outputs and r.outputs["group"] is not None
                    and r.outputs["group"]._has_signal("value")]
    assert inner_values == [1, 2, 3, 4, 5]


def _times(results, node):
    return [round(r.now, 9) for r in results if node in r.executed]


def test_hybrid_fallback_keeps_its_rate_in_logical_time():
    # The source emits at 0.0 and 0.5 (Rate 2); an unrelated Rate(10) flow makes
    # the covering clock tick every 0.1 s. The Hybrid flow runs on its own 5 Hz
    # grid plus on each trigger arrival, and at no other covering tick.
    with Pipeline() as pipe:
        src = (Source() @ Rate(2)).named("src")
        hyb = (Relay() @ Hybrid(5, trigger=["value"])).named("hyb")
        (Source() @ Rate(10)).named("ticker")
        src.then(hyb, sync=Latest())
    res = pipe.run_logical(1.0)
    assert _times(res, "hyb") == pytest.approx([0.0, 0.2, 0.4, 0.5, 0.6, 0.8])


def test_run_logical_offgrid_start_runs_flows_only_on_their_grid():
    with Pipeline() as pipe:
        fast = (Source() @ Rate(20)).named("fast")
        slow = (Relay() @ Rate(10)).named("slow")
        fast.then(slow, sync=Latest())
    res = pipe.run_logical(0.3, start=0.05)
    assert _times(res, "slow") == pytest.approx([0.1, 0.2])
    assert _times(res, "fast") == pytest.approx([0.05, 0.1, 0.15, 0.2, 0.25])


def test_reset_between_logical_runs_gives_equal_traces():
    with Pipeline() as pipe:
        fast = (Source() @ Rate(20)).named("fast")
        slow = (Relay() @ Rate(7)).named("slow")
        fast.then(slow, sync=Latest())

    def trace():
        return [(round(r.now, 9), tuple(r.executed),
                 r.outputs["slow"].value if "slow" in r.outputs else None)
                for r in pipe.run_logical(1.0)]

    first = trace()
    pipe.reset()
    assert trace() == first


def test_trigger_waits_for_future_stamped_arrival():
    with Pipeline() as pipe:
        (Source() @ Rate(10)).named("ticker")
        (Relay() @ Trigger("value")).named("echo")
    pipe.inject_input("echo", "value", 7, timestamp=0.35)
    res = pipe.run_logical(1.0)
    assert _times(res, "echo") == pytest.approx([0.4])
    echo = next(r for r in res if "echo" in r.executed)
    assert echo.inputs["echo"].value == 7


def test_channel_new_arrival_respects_now():
    from retriever.rt.stepper import InMemoryChannel

    ch = InMemoryChannel(buffer_size=4)
    ch.put_one(7, 0.35)
    assert ch.new_arrival(0.3) is False
    assert ch.new_arrival(0.35) is True
    assert ch.new_arrival(0.4) is False
    # Default mode (no `now`) is unchanged: any arrival counts once.
    ch.put_one(8, 0.9)
    assert ch.new_arrival() is True
    assert ch.new_arrival() is False


def test_default_step_still_runs_every_rate_flow():
    with Pipeline() as pipe:
        fast = (Source() @ Rate(30)).named("fast")
        slow = (Relay() @ Rate(10)).named("slow")
        fast.then(slow, sync=Latest())
    res = [pipe.step(now=k / 30) for k in range(6)]
    assert all(r.executed == ["fast", "slow"] for r in res)
