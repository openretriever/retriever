"""
Service Request/Response - Inter-flow RPC with Dora Backend

Demonstrates @handle_service and @call_service decorators for
synchronous request/response communication between flows.

Run:
  pixi run demo-request-dora
  # or:
  pixi run python -m examples.tutorial.b_ir_and_execution.07_request_response --backend dora --duration 5
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from retriever.flow import Flow, Pipeline, flow_io, Rate, Trigger
from retriever.flow import handle_service, call_service
from retriever.flow.service import ServiceCall

@dataclass
class MathRequest:
    value: int


@dataclass
class MathResponse:
    result: int


# =============================================================================
# Flow I/O Types
# =============================================================================

@flow_io
@dataclass
class NumberOutput:
    value: int


@flow_io
@dataclass
class NumberInput:
    value: int


# =============================================================================
# Flows
# =============================================================================

class MathService(Flow[None, NumberOutput]):
    """Generates numbers and provides 'double' service."""

    def __init__(self):
        super().__init__()
        self.counter = 0

    @handle_service
    def double(self, request: MathRequest) -> MathResponse:
        print(f"  [MathService] double({request.value}) → {request.value * 2}")
        return MathResponse(result=request.value * 2)
    
    @handle_service
    def triple(self, request: MathRequest) -> MathResponse:
        print(f"  [MathService] triple({request.value}) → {request.value * 3}")
        return MathResponse(result=request.value * 3)

    def run(self, _input) -> NumberOutput:
        self.counter += 1
        print(f"  [MathService] Emitting: {self.counter}")
        return NumberOutput(value=self.counter)


@call_service(MathService.double, MathService.triple)
class Calculator(Flow[NumberInput, None]):
    """Receives values and calls MathService.double."""

    def run(self, input: NumberInput):
        value = input.value
        print(f"  [Calculator] Received {value}, calling double")
        response2 = yield ServiceCall(MathService.double, MathRequest(value=value))

        print(f"  [Calculator] Received {value}, calling triple")
        response3 = yield ServiceCall(MathService.triple, MathRequest(value=value))

        print(f"  [Calculator] Result: double({response2.result}), triple({response3.result})")


def build_pipeline():
    pipe = Pipeline("service_demo")
    with pipe:
        # MathService generates numbers and provides services.
        math_svc = MathService() @ Rate(hz=1)
        # Calculator is triggered by incoming `value` and calls the services.
        calculator = Calculator() @ Trigger("value")

        # Data edge: MathService.value -> Calculator.value
        math_svc >> calculator

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Service request/response demo (Dora backend recommended).")
    p.add_argument("--backend", default="dora", choices=["multiprocessing", "dora"])
    p.add_argument("--duration", type=float, default=5.0)
    p.add_argument("--print-ir", action="store_true", help="Print the built IR (includes service edges).")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.backend != "dora":
        raise SystemExit("This demo uses yield-based ServiceCall and currently requires the dora backend.")

    print("=" * 60)
    print("Service Request/Response Demo")
    print("=" * 60 + "\n")

    pipe = build_pipeline()

    if args.print_ir:
        ir = pipe.validate()
        print(ir.to_json())

        print("\nService edges:")
        for edge in ir.edges:
            if "_request" in edge.id or "_response" in edge.id:
                print(f"  {edge.id}")

    print(f"\nExecuting with {args.backend} backend ({args.duration:.1f} seconds)...")
    print("-" * 60)
    pipe.run(backend=args.backend, duration=args.duration, blocking=True)
    print("-" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
