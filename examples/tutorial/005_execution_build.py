"""
Execution Build - Group compatible nodes

Builds a physical execution graph (partitions + placement), then lowers it to
an executable IR by grouping/fusing nodes.

Demonstrates 'conservative' and 'aggressive' builtin policies.

Run:
  pixi run python -m examples.00_refact.005_execution_build
"""

from dataclasses import dataclass

from retriever.flow import Flow, Pipeline, flow_io, Rate, Trigger
from retriever.ir import build_execution


@flow_io
@dataclass
class Data:
    value: int


class SourceFlow(Flow[None, Data]):
    def run(self, _):
        return Data(value=42)


class ProcessFlow(Flow[Data, Data]):
    def run(self, input: Data):
        return Data(value=input.value * 2)


class SinkFlow(Flow[Data, None]):
    def run(self, input: Data):
        print(f"Received: {input.value}")
        return None


def demo_simple_build():
    """Demonstrate building an ExecutionGraph on a simple pipeline."""
    print("=" * 60)
    print("Demo 1: Simple Pipeline (Conservative Policy)\n")

    pipe = Pipeline("pipeline")
    with pipe:
        source = SourceFlow() @ Rate(hz=10)
        process = ProcessFlow() @ Trigger("value")
        sink = SinkFlow() @ Trigger("value")

        print("Building flow graph:")
        print("  [1] SourceFlow @ Rate(10Hz) → ProcessFlow @ Trigger")
        source >> process

        print("  [2] ProcessFlow @ Trigger → SinkFlow @ Trigger")
        process >> sink

        print("\nBuilding IR (validation)...")
        ir = pipe.build_ir()

    print(f"Original IR: {len(ir.nodes)} nodes, {len(ir.edges)} edges")

    print("\nBuilding execution graph with 'conservative' policy...")
    graph = build_execution(ir, policy='conservative')
    execution_ir = graph.to_execution_ir()

    print(f"ExecutionGraph: {len(graph.partitions)} partitions, {len(graph.edges)} cross edges")
    print(f"Execution IR: {len(execution_ir.nodes)} nodes, {len(execution_ir.edges)} edges")
    print(f"Reduction: {len(ir.nodes)} → {len(execution_ir.nodes)} executors")


def demo_predicate_blockers():
    """Demonstrate how predicates block grouping candidates."""
    print("\n" + "=" * 60)
    print("Demo 2: Complex Graph - Testing Predicate Conditions\n")

    pipe = Pipeline("complex_pipeline")
    with pipe:
        # Linear chain with same rate (can fuse)
        source = SourceFlow() @ Rate(hz=10)
        proc1 = ProcessFlow() @ Trigger("value")
        proc2 = ProcessFlow() @ Trigger("value")

        # Node with different rate (cannot fuse - breaks same_effective_rate)
        proc3 = ProcessFlow() @ Rate(hz=20)  # Different rate!

        # Cycle nodes (cannot fuse - breaks not_in_cycle)
        cycle1 = ProcessFlow() @ Trigger("value")
        cycle2 = ProcessFlow() @ Trigger("value")

        sink = SinkFlow() @ Trigger("value")

        print("Building complex flow graph:")
        print("  [1] Source @ Rate(10Hz) → Proc1 @ Trigger (Latest)")
        source >> proc1

        print("  [2] Proc1 → Proc2 (Latest)")
        proc1 >> proc2

        print("  [3] Proc2 → Proc3 @ Rate(20Hz) (different rate!)")
        proc2 >> proc3

        print("  [4] Proc3 → Cycle1 (Latest)")
        proc3 >> cycle1

        print("  [5] Cycle1 → Cycle2 (Latest)")
        cycle1 >> cycle2

        print("  [6] Cycle2 → Cycle1 (Latest - creates cycle!)")
        cycle2 >> cycle1

        print("  [7] Cycle2 → Sink (Latest)")
        cycle2 >> sink

        print("\n  Expected grouping behavior:")
        print("    ✓ Source+Proc1+Proc2: linear chain, same rate (10Hz), Latest, no cycle")
        print("    ✗ Proc3: different rate (20Hz vs 10Hz)")
        print("    ✗ Cycle1+Cycle2: in cycle (violates not_in_cycle)")

        print("\nBuilding IR (validation)...")
        ir = pipe.build_ir()

    print(f"\nOriginal IR: {len(ir.nodes)} nodes, {len(ir.edges)} edges")
    print(f"Has cycles: {ir.topology.has_cycle}")

    print("\nBuilding execution graph with 'aggressive' policy...")
    graph = build_execution(ir, policy='aggressive', verbose=True)
    optimized = graph.to_execution_ir()

    print(f"\nExecution IR: {len(optimized.nodes)} nodes, {len(optimized.edges)} edges")
    reduction_pct = (1 - len(optimized.nodes) / len(ir.nodes)) * 100
    print(f"Reduction: {len(ir.nodes)} → {len(optimized.nodes)} nodes ({reduction_pct:.1f}%)")

    if optimized.optimization:
        print(f"\nGrouping details:")
        print(f"  Co-located groups ({len(optimized.optimization.fusion_map)} nodes):")
        for fused_id, original_ids in optimized.optimization.fusion_map.items():
            print(f"    {fused_id}: {' → '.join(original_ids)}")
        print(f"\n  Unfused nodes (blocked by predicates):")
        fused_originals = set()
        for originals in optimized.optimization.fusion_map.values():
            fused_originals.update(originals)
        for node in ir.nodes:
            if node.id not in fused_originals and node.id in [n.id for n in optimized.nodes]:
                print(f"    {node.id}")


if __name__ == "__main__":
    demo_simple_build()
    demo_predicate_blockers()

    print("\n" + "=" * 60)
    print("Execution build policies:")
    print("  Builtin policies: 'conservative', 'aggressive', 'strict'")
    print("  Builtin predicates (used by policies): linear_chain, not_in_cycle,")
    print("                                       same_effective_rate, latest_adapter,")
    print("                                       compatible_resource, and more")
    print("\n" + "=" * 60)
    print("Next: Run a Pipeline via `pipe.run(build=False)` (raw IR) or `pipe.run(build=True)` (ExecutionGraph)")
    print("=" * 60)
