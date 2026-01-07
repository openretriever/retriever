"""Tests for IRStruct OO methods."""

import pytest
from pathlib import Path

from retriever.flow import Flow, Pipeline, Rate, Latest, io
from retriever.ir.core import IR, IRAnalysis
from retriever.ir.execution import ExecutionGraph


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
