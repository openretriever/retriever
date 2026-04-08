"""
Tests for modernized Flow API (Rate, Trigger, FlowConfig).
Verifies that legacy arguments are gone and new resource spec works.
"""
import pytest
from retriever.flow import Flow, Rate, Trigger, Hybrid, FlowConfig, io
from retriever.flow.config import ResourceSpec
from retriever.error import FlowError

@io
class IO:
    val: int

class SimpleFlow(Flow[IO, IO]):
    def step(self, input: IO):
        return input

def test_rate_clock_modern():
    """Verify Rate clock works with simple Hz and rejects sample/fields."""
    r = Rate(hz=10)
    assert r.hz == 10
    assert r.interval == 0.1
    
    # Verify legacy arguments are rejected (TypeError because they are not in __init__)
    with pytest.raises(TypeError):
        Rate(hz=10, sample=["foo"])
    
    with pytest.raises(TypeError):
        Rate(hz=10, fields=["foo"])

def test_trigger_clock_modern():
    """Verify Trigger works with positional args and rejects kwargs."""
    t = Trigger("foo", "bar")
    assert t.fields == ["foo", "bar"]
    
    # Verify legacy kwargs are rejected
    with pytest.raises(TypeError):
        Trigger(on=["foo"])
        
    with pytest.raises(TypeError):
        Trigger(fields=["foo"])

def test_hybrid_clock_modern():
    """Verify Hybrid works with new simplified init."""
    h = Hybrid(hz=5, trigger=["foo"])
    assert h.hz == 5
    assert h.trigger_fields == ["foo"]
    
    # Legacy arguments should fail
    with pytest.raises(TypeError):
        Hybrid(hz=5, sample=["foo"])

def test_flow_config_modern():
    """Verify FlowConfig works with ResourceSpec and rejects legacy fields."""
    res = ResourceSpec(cpu=2.0, memory=4.0)
    config = FlowConfig(clock=Rate(hz=1), resources=res)
    
    assert config.resources.cpu == 2.0
    assert config.resources.memory == 4.0
    
    # Legacy fields should cause TypeError
    with pytest.raises(TypeError):
        FlowConfig(clock=Rate(hz=1), priority=10)
        
    with pytest.raises(TypeError):
        FlowConfig(clock=Rate(hz=1), memory_size=1024)

def test_wiring_modern_api():
    """Verify the @ syntax works with modern clocks."""
    f = SimpleFlow()
    
    # Rate
    h1 = f @ Rate(hz=10)
    assert isinstance(h1.config.clock, Rate)
    assert h1.config.clock.hz == 10
    
    # Trigger
    h2 = f @ Trigger("x")
    assert isinstance(h2.config.clock, Trigger)
    assert h2.config.clock.fields == ["x"]
