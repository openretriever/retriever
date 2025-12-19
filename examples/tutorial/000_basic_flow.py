"""
000_basic_flow.py - Basic Flow (Flow as a function)

A Flow transforms inputs to outputs like a function.

Run:
  pixi run python -m examples.tutorial.000_basic_flow
"""

from dataclasses import dataclass
from retriever.flow import Flow, flow_io


@flow_io
@dataclass
class NumberInput:
    value: int


@flow_io
@dataclass
class NumberOutput:
    result: int


class DoubleFlow(Flow[NumberInput, NumberOutput]):
    """Simple flow using direct attribute access."""
    def run(self, input: NumberInput):
        print(f"  [DoubleFlow] input.value={input.value} → result={input.value * 2}")
        return NumberOutput(result=input.value * 2)


class SignalAwareFlow(Flow[NumberInput, NumberOutput]):
    """Flow using _signals for pattern matching."""
    def run(self, input: NumberInput):
        print(f"  [SignalAwareFlow] input._signals={input._signals}")

        match input._signals:
            case []:
                print("    No signals - skipping")
                return NumberOutput()
            case ['value']:
                result = input.value * 2
                print(f"    value={input.value} → result={result}")
                return NumberOutput(result=result)

        return NumberOutput()


if __name__ == "__main__":
    print("=" * 60)
    print("DoubleFlow - direct attribute access")
    flow1 = DoubleFlow()
    print(f"  Input type: {flow1.input_type.__name__}")
    print(f"  Output type: {flow1.output_type.__name__}")

    output1 = flow1.run(NumberInput(value=5))
    print(f"  Result: {output1}\n")

    print("=" * 60)
    print("SignalAwareFlow - _signals pattern matching")
    flow2 = SignalAwareFlow()

    print("\n  Case 1: Empty input (no signals)")
    empty_input = NumberInput()
    print(f"  empty_input._signals = {empty_input._signals}")
    flow2.run(empty_input)

    print("\n  Case 2: Input with value")
    full_input = NumberInput(value=7)
    print(f"  full_input._signals = {full_input._signals}")
    output2 = flow2.run(full_input)
    print(f"  Result: {output2}")
    print("=" * 60)
