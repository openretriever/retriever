"""
Tests for Flow combinators and basic operations.

Tests all core components of the Retriever framework to ensure
basic functionality works properly.
"""

import pytest
from retriever import Flow, ExecutionEngine


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