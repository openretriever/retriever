"""Tests for IRStruct OO methods."""

import pytest
from pathlib import Path

from retriever.flow import Flow, Pipeline, Rate, Latest, io
from retriever.ir.core import IR, IRAnalysis
from retriever.ir.execution import ExecutionGraph
from retriever.registry.pipeline import build_pipeline_flow, register_pipeline


# Simple test pipeline
@io
class CounterOut:
    count: int


class CounterFlow(Flow[None, CounterOut]):
    def __init__(self):
        self.count = 0

    def step(self, _) -> CounterOut:
        self.count += 1
        return CounterOut(count=self.count)


@io
class SinkIn:
    count: int


class SinkFlow(Flow[SinkIn, None]):
    def step(self, inp: SinkIn) -> None:
        pass


@io
class BiasIn:
    count: int
    bias: int


@io
class BiasOut:
    count: int


class BiasFlow(Flow[BiasIn, BiasOut]):
    def step(self, inp: BiasIn) -> BiasOut:
        return BiasOut(count=inp.count + inp.bias)


@register_pipeline(
    "test.composed_visualization",
    surface_policy="explicit",
    input_ports=["adder.bias"],
    output_ports=["adder.count"],
    overwrite=True,
)
def _build_composed_visualization_pipeline() -> Pipeline:
    pipe = Pipeline("test.composed_visualization")
    with pipe:
        counter = (CounterFlow() @ Rate(10.0)).named("counter")
        adder = (BiasFlow() @ Rate(10.0)).named("adder")
        counter.then(adder, map={"count": "count"}, sync=Latest())
    return pipe


def _build_simple_ir() -> IR:
    """Build a simple IR for testing."""
    pipe = Pipeline("test_pipeline")
    counter = CounterFlow() @ Rate(10.0)
    sink = SinkFlow() @ Rate(10.0)
    pipe.connect(counter, sink, map={"count": "count"}, sync=Latest())
    return pipe.validate()


class TestIRMethods:
    """Test IR OO methods."""

    def test_analysis_property(self):
        """Test ir.analysis returns cached IRAnalysis."""
        ir = _build_simple_ir()
        a1 = ir.analysis
        a2 = ir.analysis
        assert isinstance(a1, IRAnalysis)
        assert a1 is a2  # Same cached object

    def test_to_ascii(self):
        """Test ir.to_ascii() returns string."""
        ir = _build_simple_ir()
        result = ir.to_ascii()
        assert isinstance(result, str)
        assert "CounterFlow" in result or "Counter" in result

    def test_compile(self):
        """Test ir.compile() returns ExecutionGraph."""
        ir = _build_simple_ir()
        graph = ir.compile()
        assert isinstance(graph, ExecutionGraph)
        assert len(graph.partitions) > 0

    def test_compile_with_policy(self):
        """Test ir.compile() with different policies."""
        ir = _build_simple_ir()
        graph = ir.compile(policy="conservative")
        assert isinstance(graph, ExecutionGraph)

    def test_visualize(self, tmp_path: Path):
        """Test ir.visualize() creates HTML file."""
        ir = _build_simple_ir()
        path = ir.visualize(tmp_path / "viz.html")
        assert path.exists()
        content = path.read_text()
        assert "<html" in content.lower()

    def test_visualize_wrapped_pipeline(self, tmp_path: Path):
        """Test composed pipeline wrappers carry visualization metadata."""
        outer = Pipeline("outer_wrapped_visualization")
        with outer:
            stage = (build_pipeline_flow("test.composed_visualization") @ Rate(10.0)).named("stage")
            sink = (SinkFlow() @ Rate(10.0)).named("sink")
            stage.then(sink, map={"count": "count"}, sync=Latest())

        unlowered_ir = outer.validate(lower_composite_flows=False)
        stage_node = next(node for node in unlowered_ir.nodes if node.id == "stage")

        assert stage_node.config["in_process_only"] is True
        wrapped = stage_node.config["viz"]
        assert wrapped["kind"] == "pipeline"
        assert wrapped["pipeline_name"] == "test.composed_visualization"
        assert wrapped["summary"] == {"node_count": 2, "edge_count": 1}
        assert wrapped["surface"]["inputs"][0]["external_name"] == "bias"
        assert wrapped["surface"]["outputs"][0]["external_name"] == "count"
        assert [node["id"] for node in wrapped["internal"]["nodes"]] == ["counter", "adder"]

        lowered_ir = outer.validate()
        lowered_nodes = {node.id: node for node in lowered_ir.nodes if node.id.startswith("stage__")}
        assert set(lowered_nodes) == {"stage__counter", "stage__adder"}

        group = lowered_nodes["stage__counter"].config["viz"]["pipeline_groups"][0]
        assert group["wrapper_node_id"] == "stage"
        assert group["pipeline_name"] == "test.composed_visualization"
        assert group["summary"] == {"node_count": 2, "edge_count": 1}
        assert group["surface"]["inputs"][0]["external_name"] == "bias"
        assert group["surface"]["outputs"][0]["external_name"] == "count"
        assert [node["lowered_id"] for node in group["internal"]["nodes"]] == [
            "stage__counter",
            "stage__adder",
        ]

        ascii_graph = lowered_ir.to_ascii()
        assert "+ Pipeline [stage] (test.composed_visualization)" in ascii_graph
        assert "[counter]" in ascii_graph

        path = lowered_ir.visualize(tmp_path / "wrapped_viz.html")
        content = path.read_text()
        assert "pipeline-group" in content
        assert "test.composed_visualization" in content

    def test_save_load(self, tmp_path: Path):
        """Test ir.save() and IR.load() round-trip."""
        ir = _build_simple_ir()
        path = tmp_path / "ir.json"
        ir.save(path)
        assert path.exists()

        loaded = IR.load(path)
        assert loaded.metadata.name == ir.metadata.name
        assert len(loaded.nodes) == len(ir.nodes)
        assert len(loaded.edges) == len(ir.edges)

    def test_to_json_from_json(self):
        """Test to_json() and from_json() round-trip."""
        ir = _build_simple_ir()
        json_str = ir.to_json()
        loaded = IR.from_json(json_str)
        assert loaded.metadata.name == ir.metadata.name
