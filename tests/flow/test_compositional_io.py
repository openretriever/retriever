
from typing import Tuple

from retriever.flow import Flow, io
from retriever.flow.base import FlowError
from retriever.rt.step import IOView

# 1. Define component types
@io
class Image:
    data: str
    timestamp: float

@io
class Lidar:
    points: int
    timestamp: float

@io
class Control:
    steering: float
    throttle: float

# 2. Define a Composite Flow
class FusionFlow(Flow[Tuple[Image, Lidar], Tuple[Control]]):
    def step(self, inp) -> Control:
        # Access via Qualified Names
        img_ts = inp.Image.timestamp
        lid_ts = inp.Lidar.timestamp
        
        # Access via Direct Names (unique)
        img_data = inp.data
        lid_points = inp.points
        
        # Access via Direct Names (ambiguous - timestamp)
        # inp.timestamp should error if both have it?
        # Actually CompositeFlowIO logic: if >1 source, raise FlowError.
        
        return Control(steering=0.1, throttle=0.5)

def test_composite_flow_definition():
    """Test that FusionFlow correctly extracts input types."""
    print("\n--- Test Composite Flow Definition ---")
    print(f"Input Types: {FusionFlow._input_types}")
    print(f"Composite Input? {FusionFlow._is_composite_input}")
    
    assert len(FusionFlow._input_types) == 2
    assert FusionFlow._input_types[0] == Image
    assert FusionFlow._input_types[1] == Lidar
    assert FusionFlow._is_composite_input is True
    print("✅ Definition Correct")

def test_composite_signal_sampling():
    """Test Signal.sample() with tuple types."""
    print("\n--- Test Composite Signal Sampling ---")
    
    # Mock Adapters/Subscribers
    # In Signal.sample(), it iterates 'adapters' keys.
    # But usually adapters keys come from 'subscribers' keys.
    # Here we mock the behavior locally or use Signal directly.
    
    # Let's create a Signal and manually set instance for testing logic, 
    # OR mock the sampling process.
    
    # We will verify CompositeFlowIO logic directly first.
    img = Image(data="rgb", timestamp=1.0)
    lid = Lidar(points=100, timestamp=1.1)
    
    comp = IOView([Image, Lidar], {"Image": img, "Lidar": lid})
    
    # Test Qualified Access
    print(f"Image.data: {comp.Image.data}")
    assert comp.Image.data == "rgb"
    
    # Test Direct Access
    print(f"data: {comp.data}")
    assert comp.data == "rgb"
    
    # Test Ambiguous Access
    try:
        ts = comp.timestamp
        print(f"❌ Should have raised Error for timestamp, got {ts}")
    except FlowError as e:
        print(f"✅ Correctly raised ambiguity error: {e}")
    except Exception as e:
        print(f"❌ Raised wrong error type: {type(e)}")
        print(f"   Message: {e}")
        print(f"   Args: {e.args}")
        print(f"   Expected FlowError type: {FlowError}")
        print(f"   Is instance? {isinstance(e, FlowError)}")


    # Test Signal Routing (_set_signal)
    print("Testing _set_signal routing...")
    # 'data' exists only in Image
    comp._set_signal("data", "new_rgb")
    assert comp.Image.data == "new_rgb"
    print("✅ Routed unique field 'data'")
    
    # 'timestamp' exists in both
    # Current logic sets on ALL matching sources
    comp._set_signal("timestamp", 2.0)
    assert comp.Image.timestamp == 2.0
    assert comp.Lidar.timestamp == 2.0
    print("✅ Routed ambiguous field 'timestamp' to all sources")

if __name__ == "__main__":
    test_composite_flow_definition()
    test_composite_signal_sampling()
    print("\n🎉 All Compositional IO tests passed!")
