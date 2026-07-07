# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Time and Sync
#
# Robots do not run on one global step: cameras stream, controllers run fast,
# policies have variable latency. Retriever makes that explicit with two
# independent per-Flow decisions — a **clock** that decides *when* a Flow wakes,
# and a **sync policy** on each edge that decides *which* buffered upstream record
# becomes its input. This notebook builds tiny multi-rate graphs and steps them
# in-process so you can watch both knobs change what each `step()` sees. No
# backend, camera, or robot — every cell runs in your process.

# %% [markdown]
# > **Running in Colab?** The next cell installs `retriever-core`. From a source
# > checkout (or once it's already installed) the install is skipped.

# %%
# Colab setup: install retriever-core only if it isn't importable yet.
try:
    import retriever  # noqa: F401
except ImportError:  # pragma: no cover
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "retriever-core"], check=True
    )

# %% [markdown]
# ## Two independent knobs
#
# Every Flow answers two separate questions. The clock (`@ Rate/Trigger/Hybrid`)
# answers *when do I wake?* The sync policy (`sync=` on each edge) answers *which
# buffered record do I read?* They compose freely, and each one has a plain,
# inspectable repr.

# %%
from retriever.flow import Events, Hold, Hybrid, Latest, Rate, Trigger, Window

print("Clocks — decide WHEN a Flow wakes:")
print("  Rate(hz=20)                 ->", Rate(hz=20), f"(every {Rate(hz=20).interval:.3f}s)")
print("  Trigger('value')            ->", Trigger("value"))
print("  Hybrid(hz=5, trigger=[...]) ->", Hybrid(hz=5, trigger=["value"]))
print()
print("Sync policies — decide WHICH upstream record step() gets:")
print("  Latest()                    ->", Latest())
print("  Window(20, 0.35s, 'mean')   ->", Window(buffer_size=20, duration=0.35, agg="mean"))
print("  Hold(debounce=0.25)         ->", Hold(debounce=0.25))
print("  Events(10, 0.35s)           ->", Events(buffer_size=10, duration=0.35, include_timestamps=False))

# %% [markdown]
# ## Clocks decide *when*
#
# A `Rate` Flow wakes on its own timer, every tick, whether or not new data
# arrived. A `Trigger` Flow wakes *only* when its named field arrives. A `Hybrid`
# Flow wakes on the timer **or** immediately on the event. Here a sensor fires
# every tick but only *emits* a reading on even ticks; watch which downstream
# Flows go quiet when nothing new arrives.

# %%
from retriever.flow import Flow, Pipeline, io


@io
class Reading:
    value: int


class Sensor(Flow[None, Reading]):
    """Wakes every tick, but only publishes a reading on even ticks."""

    def reset(self):
        self.tick = 0
        self.emitted = 0

    def step(self, _):
        self.tick += 1
        if self.tick % 2 == 1:  # emit on the 1st, 3rd, 5th tick...
            self.emitted += 1
            return Reading(value=self.emitted)
        return Reading()  # nothing published this tick


class Ticker(Flow[Reading, Reading]):  # @ Rate — wakes every tick
    def step(self, r: Reading) -> Reading:
        return Reading(value=r.value)


class Detector(Flow[Reading, Reading]):  # @ Trigger — wakes only on arrival
    def step(self, r: Reading) -> Reading:
        return Reading(value=r.value)


class RateOrEvent(Flow[Reading, Reading]):  # @ Hybrid — wakes on timer OR event
    def step(self, r: Reading) -> Reading:
        return Reading(value=r.value)


clocks = Pipeline("time.clocks")
with clocks:
    sensor = Sensor() @ Rate(hz=10)
    ticker = Ticker() @ Rate(hz=10)
    detector = Detector() @ Trigger("value")
    hybrid = RateOrEvent() @ Hybrid(hz=10, trigger=["value"])
    clocks.connect(sensor, ticker, sync=Latest())
    clocks.connect(sensor, detector, sync=Latest())
    clocks.connect(sensor, hybrid, sync=Latest())

print("tick | Sensor emits | Ticker(Rate) | Detector(Trigger) | RateOrEvent(Hybrid)")
for i in range(6):
    res = clocks.step(dt=0.1)
    emitted = res.outputs["Sensor"].value
    emit_s = f"v={emitted}" if emitted is not None else "  -"
    tick_seen = f"sees v={res.inputs['Ticker'].value}"
    det = f"FIRED v={res.inputs['Detector'].value}" if "Detector" in res.executed else "idle"
    hyb = "FIRED" if "RateOrEvent" in res.executed else "idle"
    print(f"  {i}  |    {emit_s:5}    |  {tick_seen:9} | {det:11} | {hyb}")
clocks.close_stepper()

# %% [markdown]
# `Detector` is the only Flow that goes quiet on odd ticks — its `Trigger` clock
# has nothing to fire on. `Ticker` (`Rate`) and `RateOrEvent` (`Hybrid`) wake
# every tick regardless. (The in-process stepper wakes `Rate` and `Hybrid` once
# per tick; the extra thing `Hybrid` buys you — waking *immediately* on an event
# instead of waiting for the next timer edge — is a live-scheduling property.)

# %% [markdown]
# ## Sync decides *which record*
#
# Every edge keeps a timestamped buffer of upstream outputs. The `sync=` policy
# consumes that buffer at wake time and returns exactly one input. Fan the *same*
# 10 Hz ramp (emitting 1, 2, 3, ...) into three consumers with three policies and
# compare what each `step()` receives on the same tick.

# %%
@io
class Signal:
    value: int


class Ramp(Flow[None, Signal]):
    def reset(self):
        self.n = 0

    def step(self, _):
        self.n += 1
        return Signal(value=self.n)


class Newest(Flow[Signal, Signal]):
    def step(self, s: Signal) -> Signal:
        return Signal(value=s.value)


class Averaged(Flow[Signal, Signal]):
    def step(self, s: Signal) -> Signal:
        return Signal(value=s.value)


class Recent(Flow[Signal, Signal]):
    def step(self, s: Signal) -> Signal:
        return Signal(value=s.value)


sync = Pipeline("time.sync")
with sync:
    ramp = Ramp() @ Rate(hz=10)
    newest = Newest() @ Rate(hz=10)
    averaged = Averaged() @ Rate(hz=10)
    recent = Recent() @ Rate(hz=10)
    sync.connect(ramp, newest, sync=Latest())
    sync.connect(ramp, averaged, sync=Window(buffer_size=20, duration=0.35, agg="mean"))
    sync.connect(ramp, recent, sync=Events(buffer_size=10, duration=0.35, include_timestamps=False))

print("tick | Latest() | Window(mean, 0.35s) | Events(recent 0.35s)")
for i in range(6):
    res = sync.step(dt=0.1)
    latest_v = res.inputs["Newest"].value
    mean_v = res.inputs["Averaged"].value
    recent_v = res.inputs["Recent"].value
    print(f"  {i}  |    {latest_v:>2}    |        {mean_v:>4}         | {recent_v}")
sync.close_stepper()

# %% [markdown]
# Same stream, same tick, three different inputs. `Latest()` hands over one fresh
# value. `Window(agg="mean")` summarizes the last 0.35 s and slides forward.
# `Events(...)` returns the recent records themselves, for Flows that reason over
# a short history. The policy is a pure function of the *buffered, timestamped
# records* — not of any global state.

# %% [markdown]
# ## Hold: rate-limit a chatty stream
#
# `Hold` is a zero-order hold: it repeats the last accepted value. With
# `debounce=`, it also refuses to accept a new value until that many seconds have
# passed — a leading-edge rate limiter. Feed the same 10 Hz ramp through
# `Latest()` and `Hold(debounce=0.25)` side by side.

# %%
class Debounced(Flow[Signal, Signal]):
    def step(self, s: Signal) -> Signal:
        return Signal(value=s.value)


hold = Pipeline("time.hold")
with hold:
    src = Ramp() @ Rate(hz=10)
    live = Newest() @ Rate(hz=10)
    steady = Debounced() @ Rate(hz=10)
    hold.connect(src, live, sync=Latest())
    hold.connect(src, steady, sync=Hold(debounce=0.25))

print("tick | Latest() | Hold(debounce=0.25)")
for i in range(6):
    res = hold.step(dt=0.1)
    print(f"  {i}  |    {res.inputs['Newest'].value:>2}    | {res.inputs['Debounced'].value:>2}")
hold.close_stepper()

# %% [markdown]
# `Latest()` passes every new reading (1, 2, 3, ...). `Hold(debounce=0.25)`
# accepts one, then ignores updates for 0.25 s and re-serves the held value —
# so a downstream Flow sees a calm, rate-limited signal without adding its own
# state. Clocks and sync are also the determinism boundary: the wall clock
# decides which records land in a buffer, but every sync policy is a pure
# function of those records — replay the same trace and every `step()` sees the
# same input. Next: [Runtime](/concepts/runtime/) connects clocks and sync to
# validation, in-process stepping, backends, and replay.
