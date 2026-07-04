"""
Type System Validation Tests

Tests the core type system, registry, and conversion functionality.
"""

import pytest
from retriever import get_type
from retriever.registry.types import (
    convert_to_arrow,
    convert_from_arrow,
    get_global_registry,
    get_registered_types,
    register_type,
)
from retriever.types.spatial import Header, JointState, PoseStamped, Quaternion, SE3Pose, Vector3

# Get canonical types via registry
RegistryPoseStamped = get_type("PoseStamped")
RegistryJointState = get_type("JointState")


class TestCoreTypes:
    """Test canonical spatial types."""

    def test_pose_stamped_creation(self):
        """Test creating a stamped SE(3) pose."""
        header = Header(stamp_ns=123, frame_id="world", source="test")
        pose = SE3Pose(
            position=Vector3(x=1.0, y=2.0, z=3.0),
            orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
        )
        msg = PoseStamped(header=header, pose=pose)

        assert msg.header.frame_id == "world"
        assert msg.pose.position.x == 1.0
        assert msg.pose.orientation.w == 1.0

    def test_joint_state_alignment(self):
        """Test joint-state alignment helper."""
        joints = JointState(
            names=("joint1", "joint2"),
            positions=(0.1, 0.2),
            velocities=(0.0, 0.0),
            efforts=(1.0, 1.5),
        )

        assert joints.is_aligned()

    def test_registry_exposes_canonical_spatial_types(self):
        """Test canonical spatial types are reachable via registry."""
        assert RegistryPoseStamped is PoseStamped
        assert RegistryJointState is JointState


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
        from retriever import Flow, io

        @register_type
        class FlowTestType:
            def __init__(self, value):
                self.value = value

        @io
        class TextIn:
            value: str

        @io
        class WrappedOut:
            item: FlowTestType

        @io
        class TextOut:
            value: str

        class WrapValue(Flow[TextIn, WrappedOut]):
            def step(self, data):
                return WrappedOut(item=FlowTestType(data.value))

        class ExtractValue(Flow[WrappedOut, TextOut]):
            def step(self, data):
                return TextOut(value=data.item.value)

        wrap = WrapValue()
        extract = ExtractValue()

        intermediate = wrap.step(TextIn(value="test_input"))
        result = extract.step(intermediate)
        assert result.value == "test_input"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
