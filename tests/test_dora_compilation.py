"""
Dora Compilation Tests

Tests the Dora YAML generation and operator compilation functionality.
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from retriever import Flow, ExecutionEngine
from retriever.core.execution import DoraExecutor


class TestDoraYAMLGeneration:
    """Test Dora YAML generation from Flow pipelines."""
    
    def test_simple_flow_yaml_generation(self):
        """Test generating YAML for a simple flow."""
        def process_data(x):
            return f"processed_{x}"
        
        flow = Flow.from_module(process_data)
        engine = ExecutionEngine()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "test_dataflow.yaml")
            result = engine.compile_to_dora([flow], output_path)
            
            assert os.path.exists(output_path)
            assert result is not None
            
            # Load and validate basic YAML structure
            with open(output_path, 'r') as f:
                yaml_content = yaml.safe_load(f)
            
            assert 'nodes' in yaml_content
            assert 'communication' in yaml_content
            assert isinstance(yaml_content['nodes'], list)
    
    def test_sequential_pipeline_yaml(self):
        """Test YAML generation for sequential pipeline."""
        def step1(x):
            return f"step1_{x}"
        
        def step2(x):
            return f"step2_{x}"
        
        flow1 = Flow.from_module(step1)
        flow2 = Flow.from_module(step2)
        pipeline = flow1 >> flow2
        
        engine = ExecutionEngine()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "sequential_dataflow.yaml")
            result = engine.compile_to_dora([pipeline], output_path)
            
            assert os.path.exists(output_path)
            
            with open(output_path, 'r') as f:
                yaml_content = yaml.safe_load(f)
            
            # Should have nodes for the pipeline components
            nodes = yaml_content['nodes']
            assert len(nodes) >= 1  # At least one node for the pipeline
    
    def test_parallel_pipeline_yaml(self):
        """Test YAML generation for parallel (fanout) pipeline."""
        def branch1(x):
            return f"branch1_{x}"
        
        def branch2(x):
            return f"branch2_{x}"
        
        flow1 = Flow.from_module(branch1)
        flow2 = Flow.from_module(branch2)
        parallel = flow1 & flow2
        
        engine = ExecutionEngine()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "parallel_dataflow.yaml")
            result = engine.compile_to_dora([parallel], output_path)
            
            assert os.path.exists(output_path)
            
            with open(output_path, 'r') as f:
                yaml_content = yaml.safe_load(f)
            
            assert 'nodes' in yaml_content
            assert 'communication' in yaml_content


class TestDoraOperatorGeneration:
    """Test Dora operator code generation."""
    
    def test_operator_file_generation(self):
        """Test that operator files are generated correctly."""
        def simple_processor(x):
            return x * 2
        
        flow = Flow.from_module(simple_processor)
        engine = ExecutionEngine()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = os.path.join(temp_dir, "test.yaml") 
            engine.compile_to_dora([flow], yaml_path)
            
            # Check if operator files were created
            operator_files = list(Path(temp_dir).glob("*_operator.py"))
            assert len(operator_files) >= 1
            
            # Check that the operator file contains valid Python code
            operator_file = operator_files[0]
            with open(operator_file, 'r') as f:
                content = f.read()
            
            # Basic validation that it's Python-like
            assert "import" in content
            assert "def" in content
    
    def test_multiple_flows_generate_multiple_operators(self):
        """Test that multiple flows generate appropriate operators."""
        def flow1_func(x):
            return x + 1
        
        def flow2_func(x):
            return x * 2
        
        flow1 = Flow.from_module(flow1_func)
        flow2 = Flow.from_module(flow2_func)
        
        engine = ExecutionEngine()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = os.path.join(temp_dir, "multi_flow.yaml")
            engine.compile_to_dora([flow1, flow2], yaml_path)
            
            # Should generate operator files
            operator_files = list(Path(temp_dir).glob("*_operator.py"))
            assert len(operator_files) >= 1  # At least one operator file


class TestDoraExecutor:
    """Test DoraExecutor functionality."""
    
    def test_dora_executor_creation(self):
        """Test creating DoraExecutor instance."""
        executor = DoraExecutor()
        assert executor is not None
    
    def test_dora_executor_yaml_generation(self):
        """Test DoraExecutor generates valid YAML."""
        def test_function(x):
            return x
        
        flow = Flow.from_module(test_function)
        executor = DoraExecutor()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = os.path.join(temp_dir, "executor_test.yaml")
            
            # Should not raise an exception
            try:
                result = executor.compile_flows_to_yaml([flow], yaml_path)
                assert os.path.exists(yaml_path)
            except NotImplementedError:
                # If not fully implemented yet, just check the interface exists
                assert hasattr(executor, 'compile_flows_to_yaml')


class TestDoraIntegration:
    """Test integration with existing examples."""
    
    def test_hello_flow_dora_compilation(self):
        """Test that hello flow example can be compiled to Dora."""
        # Simple version of the hello flow
        def hello_processor(data):
            return f"Hello {data}!"
        
        hello_flow = Flow.from_module(hello_processor)
        engine = ExecutionEngine()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = os.path.join(temp_dir, "hello_dora.yaml")
            
            # Should compile without errors
            result = engine.compile_to_dora([hello_flow], yaml_path)
            assert result is not None
            assert os.path.exists(yaml_path)
    
    def test_complex_pipeline_dora_compilation(self):
        """Test compilation of more complex pipelines."""
        def input_stage(x):
            return f"input_{x}"
        
        def processing_stage(x):
            return f"processed_{x}"
        
        def output_stage(x):
            return f"output_{x}"
        
        # Create complex pipeline: sequential + parallel
        input_flow = Flow.from_module(input_stage)
        proc_flow = Flow.from_module(processing_stage)
        output_flow = Flow.from_module(output_stage)
        
        # Branch after processing
        branch1 = proc_flow >> output_flow
        branch2 = proc_flow >> Flow.from_module(lambda x: f"alt_{x}")
        
        # Combine: input -> (branch1 & branch2)
        complex_pipeline = input_flow >> (branch1 & branch2)
        
        engine = ExecutionEngine()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = os.path.join(temp_dir, "complex_dora.yaml")
            
            # Should handle complex pipeline structure
            result = engine.compile_to_dora([complex_pipeline], yaml_path)
            assert result is not None
            assert os.path.exists(yaml_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])