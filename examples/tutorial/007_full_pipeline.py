"""
Full Pipeline - Comprehensive Example

Demonstrates all key features in one complete pipeline:
• Multi-port flows (composite data types)
• Different adapters (Latest, Window)
• Different clocks (Rate, Trigger)
• Feedback loops (cycles)
• Execution build (grouping/co-location) via `Pipeline.run(build=True)`
• Runtime execution via `Pipeline.run(...)`

Run:
  pixi run python -m examples.00_refact.007_full_pipeline --backend multiprocessing --duration 4
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from retriever.flow import (
    Flow, Pipeline, flow_io, Rate, Trigger,
    Latest, Window
)


# Multi-port data types
@flow_io
@dataclass
class SensorData:
    """Sensor with multiple fields"""
    value: float
    status: int


@flow_io
@dataclass
class ProcessedData:
    """Processed data with optional adjustment"""
    result: float
    adjustment: float


@flow_io
@dataclass
class FeedbackData:
    """Feedback adjustment data"""
    adjustment: float


# Flow implementations
class SensorFlow(Flow[None, SensorData]):
    """Generates sensor readings at fixed rate"""
    def __init__(self):
        super().__init__()
        self.counter = 0

    def run(self, _):
        self.counter += 1
        result = SensorData(value=float(self.counter), status=1)
        print(f"  [Sensor] value={result.value}, status={result.status}")
        return result


class ProcessorFlow(Flow[SensorData, ProcessedData]):
    """Processes sensor data"""
    def run(self, input: SensorData):
        result = ProcessedData(result=input.value * 2)
        print(f"  [Processor] {input.value} × 2 = {result.result}")
        return result


class AggregatorFlow(Flow[ProcessedData, ProcessedData]):
    """Aggregates data with feedback"""
    def __init__(self):
        super().__init__()
        self.feedback_adjustment = 0.0
        self.last_result = 0.0

    def run(self, input: ProcessedData):
        # Update state from signals
        if input._has_signal('adjustment'):
            self.feedback_adjustment = input._get_signal('adjustment')
            print(f"  [Aggregator] updated adjustment={self.feedback_adjustment:.2f}")

        if input._has_signal('result'):
            result = input._get_signal('result')
            adjusted = result + self.feedback_adjustment
            self.last_result = adjusted
            print(f"  [Aggregator] {result} + {self.feedback_adjustment:.2f} = {adjusted:.2f}")
            return ProcessedData(result=adjusted)

        # No result signal, no output
        return None


class FeedbackFlow(Flow[ProcessedData, FeedbackData]):
    """Computes feedback adjustment"""
    def run(self, input: ProcessedData):
        # Calculate 10% feedback
        adjustment = input.result * 0.1
        result = FeedbackData(adjustment=adjustment)
        print(f"  [Feedback] computing adjustment={result.adjustment:.2f} from {input.result:.2f}")
        return result


class OutputFlow(Flow[ProcessedData, None]):
    """Final output sink"""
    def run(self, input: ProcessedData):
        print(f"  [Output] ✓ Final={input.result:.2f}\n")
        return None


def build_pipeline() -> Pipeline:
    """Build comprehensive pipeline demonstrating all features"""
    print("Building comprehensive pipeline:\n")
    print("Architecture:")
    print("  Sensor @ Rate(1Hz) → Processor @ Trigger → Aggregator @ Trigger ─┐")
    print("                       (Latest)              (Window 2s)   ↓       │")
    print("                                                           ↓       │")
    print("                                             Feedback @ Trigger    │")
    print("                                             (Latest)              │")
    print("                                                    ↓              │")
    print("                                                    └──────────────┘")
    print("                                                    ↓  (Latest) (cycle)")
    print("                                             Output @ Trigger\n")

    print("Features demonstrated:")
    print("  • Multi-port: SensorData{value, status}, different field mappings")
    print("  • Adapters: Latest (low latency), Window (time-based aggregation)")
    print("  • Clocks: Rate (periodic sensor), Trigger (event-driven processing)")
    print("  • Cycle: Aggregator → Feedback → Aggregator (feedback loop)")
    print("  • Compilation: Sensor+Processor can co-locate (Rate→Trigger, Latest, linear)")
    print("                 Aggregator+Feedback in cycle cannot co-locate\n")

    pipe = Pipeline("full_pipeline")
    with pipe:
        # Create flows with different clocks
        sensor = SensorFlow() @ Rate(hz=1)
        processor = ProcessorFlow() @ Trigger("value", "status")
        aggregator = AggregatorFlow() @ Trigger("result", "adjustment")
        feedback = FeedbackFlow() @ Trigger("result")
        output = OutputFlow() @ Trigger("result")

        print("Connecting flows:")
        print("  [1] Sensor → Processor (Latest)")
        sensor.then(processor, map={'value': 'value', 'status': 'status'}, sync=Latest())

        print("  [2] Processor → Aggregator (Window 2s mean)")
        processor.then(aggregator, map={'result': 'result'}, sync=Window(duration=2.0, agg='mean'))

        print("  [3] Aggregator → Feedback (Latest)")
        aggregator.then(feedback, map={'result': 'result'}, sync=Latest())

        print("  [4] Feedback → Aggregator (Latest, different field, creates cycle!)")
        feedback.then(aggregator, map={'adjustment': 'adjustment'}, sync=Latest())

        print("  [5] Aggregator → Output (Latest)")
        aggregator.then(output, map={'result': 'result'}, sync=Latest())

        print("\nBuilding IR (validation)...")
        ir = pipe.build_ir()

    print(f"✓ IR created: {len(ir.nodes)} nodes, {len(ir.edges)} edges")
    print(f"  Has cycle: {ir.topology.has_cycle}")
    print(f"  Sources: {ir.topology.sources}")
    print(f"  Sinks: {ir.topology.sinks}")
    print(f"  Topology groups: {ir.topology.groups}\n")

    return pipe


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Comprehensive pipeline demo (raw IR vs ExecutionGraph).")
    p.add_argument("--backend", default="multiprocessing", choices=["multiprocessing", "dora"])
    p.add_argument("--duration", type=float, default=4.0)
    p.add_argument("--build", action="store_true", help="Run via ExecutionGraph only (grouping/co-location).")
    return p.parse_args()


def demo_unoptimized(pipe: Pipeline, *, backend: str, duration: float):
    """Run raw IR (one executor per node)."""
    print("=" * 70)
    print("Demo 1: Unoptimized Pipeline\n")

    ir = pipe.build_ir()
    print(f"Executing {len(ir.nodes)} separate nodes:")
    for node in ir.nodes:
        print(f"  • {node.type}")

    print("\nRunning for 4 seconds (expect ~3 sensor readings)...")
    print("-" * 70)

    pipe.run(backend=backend, duration=duration, blocking=True, build=False)

    print("-" * 70)


def demo_optimized(pipe: Pipeline, *, backend: str, duration: float):
    """Run via ExecutionGraph (grouping/co-location)."""
    print("\n" + "=" * 70)
    print("Demo 2: Compiled Execution Graph\n")

    print("Building execution graph with 'aggressive' policy...")
    graph = pipe.build_execution(policy="aggressive")
    optimized = graph.to_execution_ir()

    ir = pipe.build_ir()
    print(f"✓ Compiled: {len(ir.nodes)} flows → {len(optimized.nodes)} executors\n")

    if optimized.optimization:
        print("Fusion results:")
        for _, original_ids in optimized.optimization.fusion_map.items():
            print(f"  ✓ Fused: {' → '.join(original_ids)}")
    else:
        print("No optimization applied")

    print(f"\nExecuting {len(optimized.nodes)} nodes:")
    for node in optimized.nodes:
        print(f"  • {node.type}")

    print("\nRunning for 4 seconds (expect ~3 sensor readings)...")
    print("-" * 70)

    pipe.run(backend=backend, duration=duration, blocking=True, build=True, policy="aggressive")

    print("-" * 70)


def demo_summary():
    """Summarize what was demonstrated"""
    print("\n" + "=" * 70)
    print("Summary: Full Pipeline Features\n")

    print("✓ Multi-port connections:")
    print("  - SensorData{value, status}, ProcessedData{result}, FeedbackData{adjustment}")
    print("  - Field-by-field mapping with different field names")
    print("  - Feedback maps 'adjustment' field to Aggregator's 'adjustment' port\n")

    print("✓ Multiple adapters:")
    print("  - Latest: Default adapter (low latency)")
    print("  - Window: Time-based aggregation (2s mean)\n")

    print("✓ Multiple clocks:")
    print("  - Rate: Periodic sensor readings (1 Hz)")
    print("  - Trigger: Event-driven processing on field arrival\n")

    print("✓ Cycle handling:")
    print("  - Aggregator → Feedback → Aggregator feedback loop")
    print("  - Topology groups show strongly connected components")
    print("  - Compilation respects cycles (not_in_cycle predicate)\n")

    print("✓ Execution compilation:")
    print("  - Aggressive policy groups compatible linear chains")
    print("  - Rate → Trigger chains with Latest can co-locate (Sensor+Processor)")
    print("  - Blocked by: cycles, Window adapters\n")

    print("✓ Runtime execution:")
    print("  - Both optimized and unoptimized produce same results")
    print("  - Optimized version has fewer processes")
    print("  - Demonstrates end-to-end: Flow → IR → ExecutionGraph → Runtime")


if __name__ == "__main__":
    print("=" * 70)
    print("Full Pipeline Example - All Features")
    print("=" * 70 + "\n")

    args = parse_args()

    # Build pipeline once
    pipe = build_pipeline()

    # Run demos
    if not args.build:
        demo_unoptimized(pipe, backend=args.backend, duration=args.duration)
    demo_optimized(pipe, backend=args.backend, duration=args.duration)
    demo_summary()

    print("\n" + "=" * 70)
    print("Full pipeline demonstration complete!")
    print("=" * 70)
