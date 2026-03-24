"""
Demo of Pipeline Control System.

This example demonstrates:
- Individual flow control (pause/resume/reset specific flows)
- Web dashboard with real-time monitoring
- Keyboard controls (optional)
- Mobile access via QR code

Run with: pixi run demo-control
"""

import time
from dataclasses import dataclass
from typing import Optional

from retriever.flow import Flow, Pipeline, Rate, io, Latest
from retriever.rt.control import ControlConfig, Controllable


@io
@dataclass
class SensorReading:
    """Sensor reading output."""
    sensor_id: str
    value: float
    timestamp: float


@io
@dataclass
class ProcessedData:
    """Processed data output."""
    processed_value: float
    average: float
    count: int


@dataclass
class SensorFlow(Controllable, Flow[None, SensorReading]):
    """Simulated sensor that generates readings."""

    name: str = "SensorFlow"
    reading_count: int = 0

    def __post_init__(self):
        """Initialize controllable."""
        Controllable.__init__(self)

    def reset(self) -> None:
        """Reset sensor state."""
        super().reset()
        self.reading_count = 0
        print(f"[{self.name}] State reset")

    def get_custom_state(self) -> dict:
        """Report custom state for dashboard."""
        return {"reading_count": self.reading_count}

    def step(self, input_data: None) -> SensorReading:
        """Generate sensor readings."""
        self.reading_count += 1
        reading = SensorReading(
            sensor_id="sensor_1",
            value=float(self.reading_count * 10),
            timestamp=time.time()
        )

        print(f"[{self.name}] Reading #{self.reading_count}: value={reading.value}")
        return reading


@dataclass
class ProcessorFlow(Controllable, Flow[SensorReading, ProcessedData]):
    """Processes sensor data."""

    name: str = "ProcessorFlow"
    processed_count: int = 0
    total_value: float = 0.0

    def __post_init__(self):
        """Initialize controllable."""
        Controllable.__init__(self)

    def reset(self) -> None:
        """Reset processor state."""
        super().reset()
        self.processed_count = 0
        self.total_value = 0.0
        print(f"[{self.name}] State reset")

    def get_custom_state(self) -> dict:
        """Report custom state for dashboard."""
        avg = self.total_value / self.processed_count if self.processed_count > 0 else 0
        return {
            "processed_count": self.processed_count,
            "average_value": round(avg, 2)
        }

    def step(self, sensor_data: SensorReading) -> ProcessedData:
        """Process sensor data."""
        # Handle None values from adapters
        if sensor_data.value is None:
            return ProcessedData(
                processed_value=0.0,
                average=self.total_value / max(self.processed_count, 1),
                count=self.processed_count
            )

        self.processed_count += 1
        value = sensor_data.value
        self.total_value += value

        result = ProcessedData(
            processed_value=value * 1.5,
            average=self.total_value / self.processed_count,
            count=self.processed_count
        )

        print(f"[{self.name}] Processed #{self.processed_count}: avg={result.average:.2f}")
        return result


@dataclass
class MonitorFlow(Controllable, Flow[ProcessedData, None]):
    """Monitors processed data."""

    name: str = "MonitorFlow"
    alert_count: int = 0

    def __post_init__(self):
        """Initialize controllable."""
        Controllable.__init__(self)

    def reset(self) -> None:
        """Reset monitor state."""
        super().reset()
        self.alert_count = 0
        print(f"[{self.name}] State reset")

    def get_custom_state(self) -> dict:
        """Report custom state for dashboard."""
        return {"alert_count": self.alert_count}

    def step(self, processed_data: ProcessedData) -> None:
        """Monitor for anomalies."""
        # Handle None values from adapters
        if processed_data.average is None:
            return

        if processed_data.average > 100:
            self.alert_count += 1
            print(f"[{self.name}] 🚨 Alert #{self.alert_count}: High average detected!")


def main():
    """Run the control demo."""

    # Create pipeline with control enabled
    with Pipeline(name="Control Demo Pipeline") as pipe:
        # Create flows
        sensor = SensorFlow() @ Rate(hz=2)
        processor = ProcessorFlow() @ Rate(hz=2)
        monitor = MonitorFlow() @ Rate(hz=2)

        # Connect flows
        pipe.connect(sensor, processor, sync=Latest())
        pipe.connect(processor, monitor, sync=Latest())

    # Execute with control enabled
    print("\n" + "="*70)
    print("Starting Pipeline with Control System")
    print("="*70)
    print("\nControl Features:")
    print("  • Web Dashboard: Access via browser (URL shown below)")
    print("  • Individual Flow Control: Pause/resume/reset specific flows")
    print("  • Real-time Monitoring: View flow states and custom metrics")
    print("  • Mobile Access: Scan QR code with your phone")
    print("\nDashboard Controls:")
    print("  • Global: Start/Pause/Stop/Reset all flows")
    print("  • Per-Flow: Start/Pause/Stop individual flows")
    print("  • Logs: View real-time output from all flows")
    print("\n" + "="*70 + "\n")

    pipe.run(
        backend="multiprocessing",
        duration=30,
        control=ControlConfig(
            enabled=True,
            web_port=8080,
            keyboard=True  # Enable keyboard controls
        ),
        blocking=True
    )

    print("\n" + "="*70)
    print("Pipeline execution completed")
    print("="*70)


if __name__ == "__main__":
    main()
