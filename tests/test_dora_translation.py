#!/usr/bin/env python3
"""
Unit Tests for Flow → Dora Translation Layer

Tests the complete translation system step by step:
1. Flow instance serialization  
2. Operator code generation
3. YAML dataflow generation
4. End-to-end pipeline translation
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path
import numpy as np

# Test imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dataclasses import dataclass

from retriever.core.flow import Flow, flow_io
from retriever.core.types import Pipeline
from retriever.integrations.dora.translation import (
    FlowInstanceSerializer,
    WorkingOperatorGenerator, 
    PipelineTranslator,
    DoraConfig
)

@flow_io
@dataclass
class ArrayOut:
    """@flow_io wrapper around a numpy array for single-port flows."""

    output: np.ndarray


class ExampleFlow(Flow[None, ArrayOut]):
    """Simple test flow for unit testing."""
    
    def __init__(self, multiplier=2):
        super().__init__()
        self.multiplier = multiplier
    
    def run(self, _: None) -> ArrayOut:
        return ArrayOut(output=np.array([1, 2, 3]) * self.multiplier)


class TestFlowInstanceSerializer(unittest.TestCase):
    """Test Flow instance serialization capabilities."""
    
    def setUp(self):
        self.flow = ExampleFlow(multiplier=3)
        self.serializer = FlowInstanceSerializer()
    
    def test_basic_serialization(self):
        """Test basic flow instance serialization."""
        result = self.serializer.serialize_flow_instance(self.flow)
        
        # Check required fields
        required_fields = ["class_name", "module_path", "run_method_source", 
                          "class_source", "instance_attributes"]
        for field in required_fields:
            self.assertIn(field, result)
        
        # Check specific values
        self.assertEqual(result["class_name"], "ExampleFlow")
        self.assertIn("test_dora_translation", result["module_path"])
        self.assertIn("def run(self, _: None)", result["run_method_source"])
    
    def test_instance_attributes_extraction(self):
        """Test extraction of instance attributes."""
        result = self.serializer.serialize_flow_instance(self.flow)
        
        # Should capture the multiplier attribute
        self.assertIn("instance_attributes", result)
        self.assertEqual(result["instance_attributes"]["multiplier"], 3)
    
    def test_class_source_extraction(self):
        """Test extraction of class source code."""
        result = self.serializer.serialize_flow_instance(self.flow)
        
        class_source = result["class_source"]
        self.assertIn("class ExampleFlow", class_source)
        self.assertIn("def run(self", class_source)
        self.assertIn("np.array([1, 2, 3])", class_source)


class TestWorkingOperatorGenerator(unittest.TestCase):
    """Test operator code generation from Flow instances."""
    
    def setUp(self):
        self.flow = ExampleFlow(multiplier=5)
        self.generator = WorkingOperatorGenerator()
    
    def test_operator_generation(self):
        """Test complete operator code generation."""
        operator_code = self.generator.generate_working_operator(self.flow, "test")
        
        # Check essential components
        essential_parts = [
            "#!/usr/bin/env python3",
            "class Operator:",
            "def __init__(self):",
            "self.flow.run(input_data)",
            "def on_event(self, dora_event, send_output):",
            "operator = Operator()",
            "def on_event(dora_event, send_output):",
        ]
        
        for part in essential_parts:
            self.assertIn(part, operator_code)
    
    def test_import_handling(self):
        """Test proper import generation."""
        operator_code = self.generator.generate_working_operator(self.flow, "test")
        
        # Should import the Flow class
        self.assertIn("from retriever.integrations.dora.serialization import ArrowMessageSerializer", operator_code)
        self.assertIn("from retriever.core.flow import Flow", operator_code)
        
        # Should avoid duplicate imports for base Flow class
        if "test_dora_translation" in self.flow.__module__:
            self.assertIn("from tests.test_dora_translation import ExampleFlow", operator_code)
    
    def test_attribute_assignment(self):
        """Test instance attribute assignment in operator."""
        operator_code = self.generator.generate_working_operator(self.flow, "test")
        
        # Should set the multiplier attribute
        self.assertIn("self.flow.multiplier = 5", operator_code)
    
    def test_rate_handling(self):
        """Test FRP rate annotation handling."""
        # Test default rate
        operator_code = self.generator.generate_working_operator(self.flow, "test")
        self.assertIn("self.target_rate = 50", operator_code)  # Default 20Hz


class TestPipelineTranslator(unittest.TestCase):
    """Test complete pipeline to Dora translation."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.translator = PipelineTranslator()
        self.flow = ExampleFlow(multiplier=7)
        self.pipeline = Pipeline.from_flow(self.flow)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_pipeline_translation(self):
        """Test complete pipeline translation."""
        config = self.translator.translate_pipeline(self.pipeline, self.temp_dir)
        
        # Check config structure
        self.assertIsInstance(config, DoraConfig)
        self.assertTrue(os.path.exists(config.yaml_path))
        self.assertEqual(len(config.operators), 1)
        self.assertTrue(os.path.exists(config.operators[0]))
    
    def test_yaml_generation(self):
        """Test YAML dataflow generation."""
        config = self.translator.translate_pipeline(self.pipeline, self.temp_dir)
        
        # Read generated YAML
        with open(config.yaml_path, 'r') as f:
            yaml_content = f.read()
        
        # Check YAML structure
        yaml_checks = [
            "nodes:",
            "id: example_flow",
            "operator:",
            "python: example_flow_op.py",
            "inputs:",
            "tick: dora/timer/millis/",
            "outputs:",
            "- output"
        ]
        
        for check in yaml_checks:
            self.assertIn(check, yaml_content)
    
    def test_operator_file_generation(self):
        """Test operator file creation."""
        config = self.translator.translate_pipeline(self.pipeline, self.temp_dir)
        
        operator_path = config.operators[0]
        self.assertTrue(os.path.exists(operator_path))
        
        # Read operator content
        with open(operator_path, 'r') as f:
            operator_content = f.read()
        
        # Should be valid Python with proper structure
        self.assertIn("class Operator:", operator_content)
        self.assertIn("def on_event(self, dora_event, send_output):", operator_content)
        self.assertIn("ExampleFlow", operator_content)
    
    def test_flow_extraction(self):
        """Test flow extraction from pipeline."""
        flows = self.translator._extract_flows_from_pipeline(self.pipeline)
        
        self.assertEqual(len(flows), 1)
        self.assertIsInstance(flows[0], ExampleFlow)
        self.assertEqual(flows[0].multiplier, 7)


class TestIntegrationFlow(unittest.TestCase):
    """Integration tests for complete Flow→Dora workflow."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_end_to_end_translation(self):
        """Test complete end-to-end translation workflow."""
        # Create test pipeline
        flow = ExampleFlow(multiplier=10)
        pipeline = Pipeline.from_flow(flow)
        
        # Translate to Dora
        translator = PipelineTranslator()
        config = translator.translate_pipeline(pipeline, self.temp_dir)
        
        # Verify all files exist and are valid
        self.assertTrue(os.path.exists(config.yaml_path))
        self.assertTrue(os.path.exists(config.operators[0]))
        
        # Test YAML is valid (basic structure check)
        with open(config.yaml_path, 'r') as f:
            yaml_content = f.read()
        
        # Should contain proper Dora structure
        self.assertIn("nodes:", yaml_content)
        self.assertIn("operator:", yaml_content)
        
        # Test operator is valid Python
        with open(config.operators[0], 'r') as f:
            operator_code = f.read()
        
        # Should be syntactically valid Python
        try:
            compile(operator_code, config.operators[0], 'exec')
        except SyntaxError as e:
            self.fail(f"Generated operator has syntax errors: {e}")
    
    def test_multiple_flows_composition(self):
        """Test handling of multi-flow compositions."""
        # This is a placeholder for future multi-flow support
        # Currently we handle single flows, but architecture supports expansion
        pass


if __name__ == '__main__':
    print("🧪 Running Flow → Dora Translation Tests")
    print("=" * 60)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)
