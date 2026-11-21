"""The frozen JSON and trace were produced by the 0.0.4 writer at b0d7663."""
import json
from pathlib import Path

import pytest

from retriever.error import IRError
from retriever.flow import Flow, Pipeline, Rate, Latest, io
from retriever.ir.core import IR
from retriever.rt.stepper import PipelineStepper


FIXTURE = Path(__file__).with_name("fixtures") / "feedback-0.0.4.json"


@io
class Single:
    value: int


@io
class Pair:
    value: int
    extra: int


class Split(Flow[Single, Pair]):
    def step(self, inputs):
        x = (inputs.value or 0) + 1
        return Pair(value=x, extra=x * 10)


class Join(Flow[Pair, Single]):
    def step(self, inputs):
        return Single(value=(inputs.value or 0) + (inputs.extra or 0))


def authored():
    pipe = Pipeline("legacy_parallel")
    a = (Split() @ Rate(10)).named("A")
    b = (Join() @ Rate(10)).named("B")
    pipe.connect(a, b, sync=Latest())
    pipe.connect(b, a, sync=Latest())
    return pipe


class SavedProgram:
    """Bind the local stepper to the flows and clocks named in the file."""
    def __init__(self, ir):
        self.ir = ir

    def validate(self, *, lower_composite_flows):
        return self.ir

    def get_handle_for_node(self, node_id):
        n = self.ir.get_node(node_id)
        return n.instantiate() @ n.instantiate_clock(n.config)


def trace(program):
    out = []
    for t in range(4):
        s = program.step(now=t)
        out.append((s.inputs["A"].value, s.inputs["B"].value, s.inputs["B"].extra))
    return out


def test_old_writer_file_steps_without_reordering_parallel_ports():
    ir = IR.load(FIXTURE)
    assert ir.topology.edge_count == 3
    assert trace(PipelineStepper(SavedProgram(ir))) == [
        (None, 1, 10), (11, 12, 120), (132, 133, 1330), (1463, 1464, 14640),
    ]


def test_old_reader_pair_count_and_order():
    data = json.loads(FIXTURE.read_text())
    data["topology"].update(edge_count=2, groups=[["B", "A"]])
    ir = IR.from_json(json.dumps(data))
    assert trace(PipelineStepper(SavedProgram(ir))) == [
        (0, None, None), (11, 1, 10), (132, 12, 120), (1463, 133, 1330),
    ]


@pytest.mark.parametrize("bad", [dict(edge_count=4), dict(groups=[["B", "A"]])])
def test_old_file_rejects_corrupt_topology(bad):
    data = json.loads(FIXTURE.read_text())
    data["topology"].update(bad)
    with pytest.raises(IRError, match="Topology .* mismatch"):
        IR.from_json(json.dumps(data))
