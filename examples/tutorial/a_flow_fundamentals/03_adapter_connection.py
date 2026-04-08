"""
Adapter & Connection

Adapters control how data is sampled from queues between flows.

Preferred authoring surface:
  - Use a `Pipeline` (optionally as a context manager)
  - Wire with `a >> b` or `a.then(b, sync=Latest())`

Run:
  pixi run python -m examples.tutorial.a_flow_fundamentals.03_adapter_connection
"""


from retriever.flow import Flow, Pipeline, io, Rate, Trigger, Latest, Hold, Window


@io
class SensorData:
    temperature: float


@io
class ProcessInput:
    temp: float


@io
class ProcessedResult:
    value: float


class SensorFlow(Flow[None, SensorData]):
    def step(self, _):
        return SensorData(temperature=25.5)


class ProcessFlow(Flow[ProcessInput, ProcessedResult]):
    def step(self, input: ProcessInput):
        return ProcessedResult(value=input.temp * 2)


if __name__ == "__main__":
    print("=" * 60)
    print("Adapter Types:")
    print("\n1. Latest - samples most recent value (default)")
    latest = Latest()
    print(f"   {latest}")

    print("\n2. Hold - zero-order hold with optional debounce")
    hold = Hold(debounce=0.1)
    print(f"   {hold}")
    print(f"   Reuses previous value if new arrives within {hold.debounce}s")

    print("\n3. Window - aggregates values over time window")
    window = Window(buffer_size=200, duration=1.0, agg='mean')
    print(f"   {window}")
    print(f"   Aggregates {window.duration}s window using '{window.agg}'")

    print("\n" + "=" * 60)
    print("Connecting Flows (Pipeline):")

    pipe = Pipeline("demo_pipeline")
    with pipe:
        sensor = SensorFlow() @ Rate(hz=10)
        processor = ProcessFlow() @ Trigger("temp")

        print(f"\n  Created: {sensor.flow.__class__.__name__} @ {sensor.config.clock}")
        print(f"  Created: {processor.flow.__class__.__name__} @ {processor.config.clock}")

        print("\n  Connecting with field name mapping:")
        sensor.then(processor, map={'temperature': 'temp'}, sync=Latest())
        print(f"    map={{'temperature': 'temp'}}")
        print(f"    SensorData.temperature → ProcessInput.temp")

        print("\n  Connection registered in Pipeline")
        print(f"  Pipeline: {len(pipe.get_connections())} connection(s)")
        print(f"  Pipeline: {len(pipe.get_handles())} flow(s)")

    print("\n" + "=" * 60)
