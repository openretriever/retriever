import pytest


np = pytest.importorskip("numpy")
pa = pytest.importorskip("pyarrow")


from dataclasses import dataclass

from retriever.flow import flow_io
from retriever.rt.backend.dora.serde import deserialize_arrow, serialize_arrow


def test_serde_ndarray_roundtrip_bytes_format():
    arr = (np.arange(12, dtype=np.uint8).reshape(3, 4))
    arrow, meta = serialize_arrow(arr)

    assert meta["_type"] == "ndarray"
    assert meta["_shape"] == [3, 4]
    assert meta["_dtype"] == "uint8"

    out = deserialize_arrow(arrow, meta)
    assert isinstance(out, np.ndarray)
    assert out.shape == arr.shape
    assert out.dtype == arr.dtype
    assert np.array_equal(out, arr)


def test_serde_ndarray_backward_compat_numeric_arrow():
    arr = (np.arange(6, dtype=np.int32).reshape(2, 3))
    flat = pa.array(arr.flatten())
    meta = {"_type": "ndarray", "_shape": [2, 3]}

    out = deserialize_arrow(flat, meta)
    assert isinstance(out, np.ndarray)
    assert out.shape == arr.shape
    assert np.array_equal(out, arr)


@dataclass
class Req:
    value: int


def test_serde_dataclass_roundtrip():
    req = Req(value=7)
    arrow, meta = serialize_arrow(req)
    assert meta["_type"] == "dataclass"

    out = deserialize_arrow(arrow, meta)
    assert isinstance(out, Req)
    assert out.value == 7


@flow_io
@dataclass
class FlowIO:
    x: int
    y: int


def test_serde_flow_io_dataclass_roundtrip():
    msg = FlowIO(x=1, y=2)
    arrow, meta = serialize_arrow(msg)
    assert meta["_type"] == "dataclass"

    out = deserialize_arrow(arrow, meta)
    assert isinstance(out, FlowIO)
    assert out.x == 1
    assert out.y == 2

