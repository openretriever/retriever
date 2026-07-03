"""
IR Validation - FlowGraph → IR

Validates a Pipeline and produces typed IR (Intermediate Representation).
Shows IR structure via JSON and explains validation checks.

Run:
  pixi run python -m examples.tutorial.b_ir_and_execution.02_ir_validation
"""

from retriever.flow import Flow, io, Rate, Trigger, Pipeline, Latest


@io
class Data:
    value: int


class SourceFlow(Flow[None, Data]):
    def step(self, _):
        return Data(value=42)


class ProcessFlow(Flow[Data, Data]):
    def step(self, input: Data):
        return Data(value=input.value * 2)


class SinkFlow(Flow[Data, None]):
    def step(self, input: Data):
        print(f"Received: {input.value}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Validating Pipeline and producing IR:\n")

    pipe = Pipeline("pipeline")
    with pipe:
        source = SourceFlow() @ Rate(hz=10)
        process = ProcessFlow() @ Trigger("value")
        sink = SinkFlow() @ Trigger("value")

        print("Building flow graph:")
        print("  [1] SourceFlow → ProcessFlow")
        source.then(process, map={'value': 'value'}, sync=Latest())

        print("  [2] ProcessFlow → SinkFlow")
        process.then(sink, map={'value': 'value'}, sync=Latest())

        print(f"\nPipeline: {len(pipe.get_connections())} connections, {len(pipe.get_handles())} flows")

        print("\nRunning validation (build IR)...")
        ir = pipe.validate()
        print("✓ Validation successful!\n")

    print("=" * 60)
    print("IR Structure (as JSON):\n")
    print(ir.to_json(indent=2))

    print("\n" + "=" * 60)
    print("What's included in IR:")
    print(f"  • version: IR format version ({ir.version})")
    print(f"  • metadata: pipeline name, timestamps, validation status")
    print(f"  • nodes: {ir.topology.node_count} nodes with type, config, ports")
    print(f"  • edges: {ir.topology.edge_count} edges with type, adapter, qsize")
    print(f"  • topology: sources, sinks, groups, cycle info")

    print("\n" + "=" * 60)
    print("What's checked during validation:")
    print("  [1] Port existence - all ports name must exist on their nodes")
    print("  [2] Type compatibility - source and destination types must match")
    print("  [3] More validations are coming soon")
    print("\n" + "=" * 60)
    print("Next: IR can be compiled into an ExecutionGraph (partitioning + placement)")
    print("=" * 60)
