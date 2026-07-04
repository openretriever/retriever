"""Structural validation of loaded IRs.

`IR.from_json()` must reject referentially-broken graphs (duplicate ids,
dangling edge/adjacency references, unknown ports) with a named IRError
instead of letting them fail deep inside backend execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from retriever.error import ErrCode, IRError
from retriever.flow import Flow, Latest, Pipeline, Rate, io
from retriever.ir.core import IR


@io
@dataclass
class Value:
    value: int


class Source(Flow[None, Value]):
    def step(self, _):  # type: ignore[override]
        return Value(value=1)


class Sink(Flow[Value, Value]):
    def step(self, input: Value) -> Value:
        return Value(value=input.value)


@pytest.fixture()
def ir_dict() -> dict:
    pipe = Pipeline("ir_structure")
    src = Source() @ Rate(hz=10)
    dst = Sink() @ Rate(hz=10)
    pipe.connect(src, dst, sync=Latest())
    return json.loads(pipe.validate().to_json())


def reload(data: dict) -> IR:
    return IR.from_json(json.dumps(data))


def test_clean_round_trip_passes(ir_dict: dict) -> None:
    ir = reload(ir_dict)
    assert {n.id for n in ir.nodes} == {n['id'] for n in ir_dict['nodes']}
    assert ir.validate_structure() is ir


def test_duplicate_node_id_rejected(ir_dict: dict) -> None:
    ir_dict['nodes'].append(dict(ir_dict['nodes'][0]))
    with pytest.raises(IRError) as excinfo:
        reload(ir_dict)
    assert excinfo.value.code == ErrCode.IR_VAL_INVALID


def test_dangling_edge_node_rejected(ir_dict: dict) -> None:
    ir_dict['edges'][0]['destination']['node'] = 'ghost'
    with pytest.raises(IRError) as excinfo:
        reload(ir_dict)
    assert excinfo.value.code == ErrCode.IR_VAL_INVALID
    assert 'ghost' in str(excinfo.value)


def test_unknown_source_port_rejected(ir_dict: dict) -> None:
    ir_dict['edges'][0]['source']['port'] = 'not_a_port'
    with pytest.raises(IRError) as excinfo:
        reload(ir_dict)
    assert excinfo.value.code == ErrCode.IR_VAL_PORT_NOT_FOUND
    assert 'not_a_port' in str(excinfo.value)


def test_unknown_destination_port_rejected(ir_dict: dict) -> None:
    ir_dict['edges'][0]['destination']['port'] = 'not_a_port'
    with pytest.raises(IRError) as excinfo:
        reload(ir_dict)
    assert excinfo.value.code == ErrCode.IR_VAL_PORT_NOT_FOUND


def test_fanin_destination_port_is_exempt(ir_dict: dict) -> None:
    dst_node = ir_dict['edges'][0]['destination']['node']
    ir_dict['edges'][0]['destination']['port'] = f"_fanin/{dst_node}/value"
    reload(ir_dict)  # must not raise


def test_unknown_successor_rejected(ir_dict: dict) -> None:
    ir_dict['nodes'][0]['successors'] = ['ghost']
    with pytest.raises(IRError) as excinfo:
        reload(ir_dict)
    assert excinfo.value.code == ErrCode.IR_VAL_INVALID


def test_save_load_round_trip(tmp_path, ir_dict: dict) -> None:
    path = tmp_path / "pipeline.json"
    ir = reload(ir_dict)
    ir.save(path)
    loaded = IR.load(path)
    assert {n.id for n in loaded.nodes} == {n.id for n in ir.nodes}
