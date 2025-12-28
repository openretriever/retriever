import time

import pytest

from retriever.error import RTError, ErrCode
from retriever.flow.clock import Rate
from retriever.rt.backend.dora.scheduler import DoraScheduler
from retriever.rt.backend.multiprocessing.scheduler import MPScheduler


def test_mp_scheduler_drop_skips_missed_ticks() -> None:
    clock = Rate(hz=10, on_lag="drop")
    sched = MPScheduler(clock)
    sched.reset()

    # Force scheduler far behind so it must skip ticks.
    sched.next_tick = time.time() - 10.0
    before = time.time()
    res = sched.next(inputs={})

    assert res.should_execute is True
    assert sched.next_tick is not None
    # Drop policy should jump schedule close to "now" (not keep the old behind timestamp).
    assert sched.next_tick >= before - 0.5


def test_mp_scheduler_catch_up_keeps_behind_schedule() -> None:
    clock = Rate(hz=10, on_lag="catch_up")
    sched = MPScheduler(clock)
    sched.reset()

    sched.next_tick = time.time() - 10.0
    res = sched.next(inputs={})

    assert res.should_execute is True
    assert sched.next_tick is not None
    # catch_up keeps the absolute schedule, so next_tick remains behind.
    assert sched.next_tick < time.time() - 1.0


def test_mp_scheduler_error_raises_on_lag() -> None:
    clock = Rate(hz=10, on_lag="error")
    sched = MPScheduler(clock)
    sched.reset()

    sched.next_tick = time.time() - 10.0
    with pytest.raises(RTError) as ei:
        sched.next(inputs={})
    assert ei.value.code == ErrCode.RT_SCHEDULER_LAG


def test_dora_scheduler_drop_drops_stale_tick() -> None:
    clock = Rate(hz=10, on_lag="drop")
    sched = DoraScheduler(clock)
    sched.reset()

    now = time.time()
    stale = {"metadata": {"_timestamp": str(now - 1.0)}}
    sched.push_tick_event(stale)

    assert sched.next(inputs={}).should_execute is False

    fresh = {"metadata": {"_timestamp": str(time.time())}}
    sched.push_tick_event(fresh)
    assert sched.next(inputs={}).should_execute is True


def test_dora_scheduler_catch_up_accepts_stale_tick() -> None:
    clock = Rate(hz=10, on_lag="catch_up")
    sched = DoraScheduler(clock)
    sched.reset()

    now = time.time()
    stale = {"metadata": {"_timestamp": str(now - 1.0)}}
    sched.push_tick_event(stale)
    assert sched.next(inputs={}).should_execute is True


def test_dora_scheduler_error_raises_on_stale_tick() -> None:
    clock = Rate(hz=10, on_lag="error")
    sched = DoraScheduler(clock)
    sched.reset()

    now = time.time()
    stale = {"metadata": {"_timestamp": str(now - 1.0)}}
    with pytest.raises(RTError) as ei:
        sched.push_tick_event(stale)
    assert ei.value.code == ErrCode.RT_SCHEDULER_LAG


def test_on_lag_alias_panic_normalizes_to_error() -> None:
    clock = Rate(hz=10, on_lag="panic")
    assert clock.on_lag == "error"
