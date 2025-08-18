"""
Framework Completeness Tests

Tests all core components of the Retriever framework to ensure
basic functionality works properly.
"""

import pytest
from retriever import Flow, Pipeline, ExecutionEngine
from retriever.types import register_type, get_registered_types


class TestFlowComposition:
    """Test basic Flow composition and execution."""
    
    def test_basic_flow_creation(self):
        """Test creating flows from functions."""
        def double(x): return x * 2
        flow = Flow.from_module(double)
        
        result = flow(5)
        assert result == 10
    
    def test_sequential_composition(self):
        """Test >> operator for sequential composition."""
        def double(x): return x * 2
        def add_one(x): return x + 1
        
        double_flow = Flow.from_module(double)
        add_one_flow = Flow.from_module(add_one)
        pipeline = double_flow >> add_one_flow
        
        result = pipeline(5)  # Should be (5 * 2) + 1 = 11
        assert result == 11
    
    def test_fanout_composition(self):
        """Test & operator for parallel composition."""
        def double(x): return x * 2
        def triple(x): return x * 3
        
        double_flow = Flow.from_module(double)
        triple_flow = Flow.from_module(triple)
        parallel = double_flow & triple_flow
        
        result = parallel(5)  # Should be (10, 15)
        assert result == (10, 15)
    
    def test_complex_composition(self):
        """Test combining sequential and parallel composition."""
        def double(x): return x * 2
        def triple(x): return x * 3
        def sum_tuple(t): return t[0] + t[1]
        
        double_flow = Flow.from_module(double)
        triple_flow = Flow.from_module(triple)  
        sum_flow = Flow.from_module(sum_tuple)
        
        # Create parallel then sequential: (double & triple) >> sum
        pipeline = (double_flow & triple_flow) >> sum_flow
        
        result = pipeline(5)  # Should be (5*2) + (5*3) = 10 + 15 = 25
        assert result == 25


class TestExecutionEngine:
    """Test ExecutionEngine functionality."""
    
    def test_basic_execution(self):
        """Test basic flow execution through engine."""
        def process_data(x): return f'processed_{x}'
        processing_flow = Flow.from_module(process_data)
        
        engine = ExecutionEngine()
        result = engine.run_flow(processing_flow, 'test_data')
        
        assert result == 'processed_test_data'
    
    def test_pipeline_execution(self):
        """Test pipeline execution through engine."""
        def step1(x): return f'step1_{x}'
        def step2(x): return f'step2_{x}'
        
        flow1 = Flow.from_module(step1)
        flow2 = Flow.from_module(step2)
        pipeline = flow1 >> flow2
        
        engine = ExecutionEngine()
        result = engine.run_flow(pipeline, 'input')
        
        assert result == 'step2_step1_input'


class TestTypeSystem:
    """Test type system and registry."""
    
    def test_type_registration(self):
        """Test registering custom types."""
        @register_type
        class TestType:
            def __init__(self, value):
                self.value = value
        
        registered_types = get_registered_types()
        assert 'TestType' in registered_types
        
        type_info = registered_types['TestType']
        assert type_info.name == 'TestType'
        assert type_info.type_class == TestType
    
    def test_type_registration_with_name(self):
        """Test registering types with custom names."""
        @register_type("CustomName")
        class AnotherType:
            pass
        
        registered_types = get_registered_types()
        assert 'CustomName' in registered_types
        
        type_info = registered_types['CustomName']
        assert type_info.name == 'CustomName'
        assert type_info.type_class == AnotherType


class TestBackwardCompatibility:
    """Test backward compatibility features."""
    
    def test_arrow_alias(self):
        """Test that Arrow still works as alias."""
        from retriever.core.flow import Arrow
        
        def double(x): return x * 2
        
        # Should work but emit deprecation warning
        with pytest.warns(DeprecationWarning):
            arrow = Arrow.arr(double)
        
        result = arrow(5)
        assert result == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])