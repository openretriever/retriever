"""
Type System Validation Tests

Tests the core type system, registry, and conversion functionality.
"""

import pytest
import numpy as np
from retriever import get_type

# Get types via registry
RGBImage = get_type('RGBImage')
Detection = get_type('Detection')
BoundingBox = get_type('BoundingBox')
from retriever.types.registry import (
    convert_to_arrow, convert_from_arrow, register_type,
    get_registered_types, get_global_registry
)


class TestCoreTypes:
    """Test core robotics types."""
    
    def test_rgb_image_creation(self):
        """Test creating RGBImage instances."""
        img_data = np.zeros((480, 640, 3), dtype=np.uint8)
        img = RGBImage(data=img_data)
        
        assert img.data.shape == (480, 640, 3)
        assert img.data.dtype == np.uint8
    
    def test_bounding_box_creation(self):
        """Test BoundingBox creation and properties."""
        bbox = BoundingBox(x=10, y=20, width=90, height=180)
        
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 90
        assert bbox.height == 180
        
        # Test center property
        center = bbox.center
        assert center == (55.0, 110.0)  # (10 + 90/2, 20 + 180/2)
    
    def test_detection_creation(self):
        """Test Detection with BoundingBox."""
        bbox = BoundingBox(x=10, y=20, width=90, height=180)
        detection = Detection(label='test_object', confidence=0.9, bbox=bbox)
        
        assert detection.label == 'test_object'
        assert detection.confidence == 0.9
        assert detection.bbox == bbox


class TestTypeRegistry:
    """Test type registration system."""
    
    def test_basic_type_registration(self):
        """Test registering types with decorator."""
        @register_type
        class BasicTestType:
            def __init__(self, value):
                self.value = value
        
        registry = get_global_registry()
        assert registry.is_registered(BasicTestType)
        
        registered_types = get_registered_types()
        assert 'BasicTestType' in registered_types
        
        type_info = registered_types['BasicTestType']
        assert type_info.name == 'BasicTestType'
        assert type_info.type_class == BasicTestType
    
    def test_type_registration_with_custom_name(self):
        """Test registering types with custom names."""
        @register_type("CustomTypeName")
        class AnotherTestType:
            pass
        
        registered_types = get_registered_types()
        assert 'CustomTypeName' in registered_types
        
        type_info = registered_types['CustomTypeName']
        assert type_info.name == 'CustomTypeName'
        assert type_info.type_class == AnotherTestType
    
    def test_type_registration_with_description(self):
        """Test registering types with descriptions."""
        @register_type(description="A test type for validation")
        class DescribedType:
            pass
        
        registered_types = get_registered_types()
        type_info = registered_types['DescribedType']
        assert type_info.description == "A test type for validation"


class TestArrowConversion:
    """Test PyArrow conversion system."""
    
    def test_passthrough_conversion(self):
        """Test that basic types pass through conversion unchanged."""
        test_data = {'test': 'value', 'number': 42}
        
        arrow_data = convert_to_arrow(test_data)
        back_data = convert_from_arrow(arrow_data, dict)
        
        assert test_data == arrow_data  # Should be passthrough currently
        assert test_data == back_data
    
    def test_custom_converter_registration(self):
        """Test registering custom arrow converters."""
        @register_type(arrow_converter=lambda obj: obj.__dict__)
        class ConvertibleType:
            def __init__(self, value, name):
                self.value = value
                self.name = name
        
        test_obj = ConvertibleType(42, "test_name")
        converted = convert_to_arrow(test_obj)
        
        expected = {'value': 42, 'name': 'test_name'}
        assert converted == expected
    
    def test_no_converter_passthrough(self):
        """Test that objects without converters pass through unchanged."""
        class NoConverterType:
            def __init__(self, data):
                self.data = data
        
        test_obj = NoConverterType("test_data")
        converted = convert_to_arrow(test_obj)
        
        # Should return the same object
        assert converted is test_obj


class TestTypeSystemIntegration:
    """Test integration between types and flows."""
    
    def test_types_work_with_flows(self):
        """Test that custom types work properly in Flow pipelines."""
        from retriever import Flow
        
        @register_type
        class FlowTestType:
            def __init__(self, value):
                self.value = value
        
        def create_type(value):
            return FlowTestType(value)
        
        def extract_value(obj):
            return obj.value
        
        create_flow = Flow.from_module(create_type)
        extract_flow = Flow.from_module(extract_value)
        pipeline = create_flow >> extract_flow
        
        result = pipeline("test_input")
        assert result == "test_input"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])