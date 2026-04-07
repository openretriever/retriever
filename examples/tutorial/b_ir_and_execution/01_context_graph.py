"""
FlowGraph (via Pipeline / FlowContext)

`Pipeline` is the preferred authoring surface and is FlowContext-compatible.
It builds a FlowGraph from flow connections.

The FlowGraph represents the dataflow structure and is used for IR validation.
Demonstrates cycle detection and SCC topological grouping.

Run:
  pixi run python -m examples.tutorial.b_ir_and_execution.01_context_graph
"""

from dataclasses import dataclass
from retriever.flow import Flow, flow_io, Rate, Trigger, Pipeline, Latest


@flow_io
@dataclass
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


def demo_acyclic_graph():
    """Demonstrate acyclic graph construction"""
    print("=" * 60)
    print("Demo 1: Acyclic Graph\n")

    pipe = Pipeline("pipeline")
    with pipe:
        source = SourceFlow() @ Rate(hz=2)
        process = ProcessFlow() @ Trigger("value")
        sink = SinkFlow() @ Trigger("value")

        print("Establishing connections:")
        print("  [1] SourceFlow → ProcessFlow")
        source.then(process, map={'value': 'value'}, sync=Latest())

        print("  [2] ProcessFlow → SinkFlow")
        process.then(sink, map={'value': 'value'}, sync=Latest())

        print(f"\nPipeline registered {len(pipe.get_connections())} connections")

        print("\nBuilding graph...")
        graph = pipe.graph()

    print(graph.visualize())


def demo_cyclic_graph():
    """Demonstrate cyclic graph with feedback loop"""
    print("\n" + "=" * 60)
    print("Demo 2: Cyclic Graph (Feedback Loop)\n")

    pipe = Pipeline("feedback_pipeline")
    with pipe:
        source = SourceFlow() @ Rate(hz=2)
        process1 = ProcessFlow() @ Trigger("value")
        process2 = ProcessFlow() @ Trigger("value")
        sink = SinkFlow() @ Trigger("value")

        print("Establishing connections with feedback:")
        print("  [1] SourceFlow → ProcessFlow#1")
        source.then(process1, map={'value': 'value'}, sync=Latest())

        print("  [2] ProcessFlow#1 → ProcessFlow#2")
        process1.then(process2, map={'value': 'value'}, sync=Latest())

        print("  [3] ProcessFlow#2 → SinkFlow")
        process2.then(sink, map={'value': 'value'}, sync=Latest())

        print("  [4] ProcessFlow#2 → ProcessFlow#1 (creates cycle!)")
        process2.then(process1, map={'value': 'value'}, sync=Latest())

        print("\n  Topology diagram:")
        print("            ┌──────┐")
        print("            ▼      │")
        print("  Source → P1 ───→ P2 → Sink")
        print("            (cycle)")

        print(f"\nPipeline registered {len(pipe.get_connections())} connections")

        print("\nBuilding graph...")
        graph = pipe.graph()

    print(graph.visualize())

    print(f"\nCycle detection:")
    print(f"  has_cycles() = {graph.has_cycles()}")
    cycles = graph.get_cycles()
    print(f"  get_cycles() = {cycles}")

    print(f"\nSCC Topological Groups:")
    topo_groups = graph.get_topological_groups()
    for i, group in enumerate(topo_groups):
        if len(group) > 1:
            print(f"  Group {i} (Cycle): {group}")
        else:
            print(f"  Group {i}: {group}")


if __name__ == "__main__":
    demo_acyclic_graph()
    demo_cyclic_graph()

    print("\n" + "=" * 60)
    print("Next: These graphs will be validated to produce IR")
    print("=" * 60)
