"""
Pipeline Control System Demo

Demonstrates pause/resume/reset functionality with keyboard and web control.

Usage:
    # With keyboard control only
    python examples/control_demo.py

    # With web dashboard
    python examples/control_demo.py --web-port 8080

    # With all controls
    python examples/control_demo.py --web-port 8080 --keyboard

Controls:
    Keyboard:
        Space       - Toggle pause/resume
        Shift + R   - Reset all flows
        Shift + S   - Print status
        Shift + Q   - Stop pipeline

    Web Dashboard:
        Visit http://localhost:8080
"""

import argparse
import time
from dataclasses import dataclass

from retriever import Pipeline, Flow, Rate, Latest
from retriever.flow.io import io
from retriever.rt.control import Controllable, ControlConfig


# Define flow types
@io
@dataclass
class SensorData:
    value: float = 0.0
    timestamp: float = 0.0


@io
@dataclass
class ProcessedData:
    result: float = 0.0
    count: int = 0


# Create controllable flows
class SensorFlow(Controllable, Flow[None, SensorData]):
    """Simulated sensor that generates incrementing values."""

    def __init__(self):
        super().__init__()
        self.reading_count = 0

    def reset(self) -> None:
        """Reset sensor state."""
        super().reset()
        self.reading_count = 0
        print("[SensorFlow] State reset!")

    def get_custom_state(self) -> dict:
        return {"reading_count": self.reading_count}

    def step(self, _) -> SensorData:
        self.reading_count += 1
        return SensorData(
            value=self.reading_count * 1.5,
            timestamp=time.time()
        )


class ProcessorFlow(Controllable, Flow[SensorData, ProcessedData]):
    """Processor with internal buffer that can be reset."""

    def __init__(self, window_size: int = 10):
        super().__init__()
        self.window_size = window_size
        self.buffer = []
        self.process_count = 0

    def reset(self) -> None:
        """Reset processor state."""
        super().reset()
        self.buffer.clear()
        self.process_count = 0
        print("[ProcessorFlow] State reset!")

    def get_custom_state(self) -> dict:
        return {
            "buffer_size": len(self.buffer),
            "window_size": self.window_size,
            "process_count": self.process_count,
        }

    def step(self, input: SensorData) -> ProcessedData:
        self.process_count += 1

        if input.value is not None and input.value > 0:
            self.buffer.append(input.value)
            if len(self.buffer) > self.window_size:
                self.buffer.pop(0)

        avg = sum(self.buffer) / len(self.buffer) if self.buffer else 0
        return ProcessedData(result=avg, count=self.process_count)


def main():
    parser = argparse.ArgumentParser(description="Pipeline Control Demo")
    parser.add_argument("--web-port", type=int, help="Enable web dashboard on port")
    parser.add_argument("--keyboard", action="store_true", help="Enable keyboard control")
    parser.add_argument("--duration", type=float, default=60.0, help="Duration to run")
    args = parser.parse_args()

    print("=" * 70)
    print("Pipeline Control System Demo")
    print("=" * 70)

    # Create pipeline
    pipe = Pipeline("control_demo")

    # Create control config (will be passed to pipe.run())
    control_config = ControlConfig(
        web_port=args.web_port,
        keyboard=args.keyboard,
    ) if (args.web_port or args.keyboard) else None

    # Build pipeline
    with pipe:
        sensor = SensorFlow() @ Rate(5)  # 5 Hz
        processor = ProcessorFlow(window_size=5) @ Rate(5)  # 5 Hz
        pipe.connect(sensor, processor, sync=Latest())

    print("\nPipeline built with controllable flows:")
    print("  - SensorFlow: Generates incrementing values")
    print("  - ProcessorFlow: Computes moving average")

    if args.keyboard:
        print("\nKeyboard Controls:")
        print("  Space      - Toggle pause/resume")
        print("  Shift + R  - Reset all flows")
        print("  Shift + S  - Print status")
        print("  Shift + Q  - Stop pipeline")

    if args.web_port:
        print(f"\nWeb Dashboard: http://localhost:{args.web_port}")

    print(f"\nRunning for {args.duration} seconds...")
    print("=" * 70)

    # Run pipeline with control config
    try:
        pipe.run(
            duration=args.duration,
            backend="multiprocessing",
            control=control_config,  # NEW: Pass ControlConfig to run()
        )
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")

    print("\nDemo complete!")


if __name__ == "__main__":
    main()
