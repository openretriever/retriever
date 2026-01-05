import dataclasses
import pytest
import numpy as np
from dataclasses import dataclass
from typing import Optional

from retriever.flow import io, flow_io
from retriever.error import FlowError

def test_io_auto_dataclass():
    """Test that @io automatically converts a class to a dataclass."""
    @io
    class MyData:
        x: int
        y: str

    assert dataclasses.is_dataclass(MyData)
    
    # Check default initialization (all fields should be Optional/None)
    obj = MyData()
    assert obj.x is None
    assert obj.y is None
    
    # Check initialization with values
    obj2 = MyData(x=10, y="hello")
    assert obj2.x == 10
    assert obj2.y == "hello"

def test_io_existing_dataclass():
    """Test @io on an existing dataclass."""
    @io
    @dataclass
    class MyExisting:
        a: float
    
    assert dataclasses.is_dataclass(MyExisting)
    obj = MyExisting(a=3.14)
    assert obj.a == 3.14

def test_io_helpers():
    """Test injected signal helpers."""
    @io
    class SignalData:
        val: int
        
    obj = SignalData(val=42)
    
    # _get_signal
    assert obj._get_signal("val") == 42
    
    # _set_signal
    obj._set_signal("val", 100)
    assert obj.val == 100
    
    # _has_signal
    assert obj._has_signal("val") is True
    
    obj_empty = SignalData()
    assert obj_empty._has_signal("val") is False

    # Error handling
    with pytest.raises(FlowError):
        obj._get_signal("nonexistent")

def test_legacy_alias():
    """Test that @flow_io works as an alias."""
    @flow_io
    class LegacyData:
        z: int
        
    assert dataclasses.is_dataclass(LegacyData)
    obj = LegacyData(z=1)
    assert obj.z == 1

if __name__ == "__main__":
    try:
        test_io_auto_dataclass()
        test_io_existing_dataclass()
        test_io_helpers()
        test_legacy_alias()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
