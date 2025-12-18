"""
Clock Types - Rate, Trigger, Hybrid

Clocks control when flows execute.
Bind clocks to flows using @ operator.

Run:
  pixi run python -m examples.00_refact.001_clock_types
"""

from dataclasses import dataclass
from retriever.flow import Flow, flow_io, Rate, Trigger, Hybrid


@flow_io
@dataclass
class Data:
    value: int


class SimpleFlow(Flow[Data, Data]):
    def run(self, input: Data):
        return Data(value=input.value * 2)


if __name__ == "__main__":
    flow = SimpleFlow()

    print("=" * 60)
    print("Rate Clock - periodic execution at fixed frequency")
    rate_clock = Rate(hz=10)
    print(f"  Rate(hz=10): executes {rate_clock.hz} times per second")
    flow_with_rate = flow @ rate_clock
    print(f"  Bound clock: {flow_with_rate.config.clock}")

    print("\n  Sampling control (optional):")
    print("    Rate(hz=10)           -> sample all inputs (default)")
    print("    Tick(hz=10)           -> sample no inputs")
    print("    Rate(hz=10, sample=['value']) -> sample a subset")

    print("\n" + "=" * 60)
    print("Trigger Clock - event-driven execution on input arrival")
    trigger_clock = Trigger("value")
    print("  Trigger('value'): executes when 'value' field arrives")
    flow_with_trigger = flow @ trigger_clock
    print(f"  Bound clock: {flow_with_trigger.config.clock}")

    print("\n" + "=" * 60)
    print("Hybrid Clock - combines Rate and Trigger")
    hybrid_clock = Hybrid(hz=5, trigger=['value'])
    print(f"  Hybrid(hz=5, trigger=['value']): periodic OR on field arrival")
    flow_with_hybrid = flow @ hybrid_clock
    print(f"  Bound clock: {flow_with_hybrid.config.clock}")

    print("\n" + "=" * 60)
