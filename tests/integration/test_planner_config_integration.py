import pytest
from unittest.mock import MagicMock, patch

from retriever.config import load_config
from retriever.planning.llm_planner import LLMPlanner
from retriever.core.skills import SkillSignature
from retriever.core.types import NLCommand, ObjectDescriptionDict


def test_planner_from_config():
    """Test that the LLM planner can be instantiated from configuration."""
    # Create a temporary config file content
    config_content = """
planner:
  planner_type: "LLMPlanner"
  client_type: "openai"
  client_kwargs:
    model: "gpt-4o"
    max_tokens: 512
    temperature: 0.1

perception:
  model_name: "yolo11n"

robot_interface:
  robot_ip: "192.168.80.3"
"""
    
    # Write to a temporary file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_config_path = f.name
    
    try:
        # Load the configuration
        cfg = load_config(temp_config_path)
        
        # Verify configuration loaded correctly
        assert cfg.planner.planner_type == "LLMPlanner"
        assert cfg.planner.client_type == "openai"
        assert cfg.planner.client_kwargs["model"] == "gpt-4o"
        assert cfg.planner.client_kwargs["max_tokens"] == 512
        assert cfg.planner.client_kwargs["temperature"] == 0.1
        
        # Test that we can create a planner from this config
        with patch('retriever.planning.llm_planner.create_llm_client') as mock_create_client:
            mock_client = MagicMock()
            mock_create_client.return_value = mock_client
            
            planner = LLMPlanner(
                client_type=cfg.planner.client_type,
                client_kwargs=cfg.planner.client_kwargs
            )
            
            # Verify the client was created with the right parameters
            mock_create_client.assert_called_once_with(
                "openai",
                model="gpt-4o",
                max_tokens=512,
                temperature=0.1
            )
    finally:
        # Clean up temp file
        os.unlink(temp_config_path)


def test_config_overrides():
    """Test that configuration overrides work correctly."""
    import tempfile
    import os
    
    config_content = """
planner:
  planner_type: "LLMPlanner"
  client_type: "openai"
  client_kwargs:
    model: "gpt-4o"
    max_tokens: 512

perception:
  model_name: "yolo11n"

robot_interface:
  robot_ip: "192.168.80.3"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_config_path = f.name
    
    try:
        # Load config with overrides
        overrides = [
            "planner.client_type=gemini",
            "planner.client_kwargs.model=gemini-1.5-flash",
            "planner.client_kwargs.temperature=0.7"
        ]
        cfg = load_config(temp_config_path, overrides)
        
        # Verify overrides applied
        assert cfg.planner.client_type == "gemini"
        assert cfg.planner.client_kwargs["model"] == "gemini-1.5-flash"
        assert cfg.planner.client_kwargs["temperature"] == 0.7
        assert cfg.planner.client_kwargs["max_tokens"] == 512  # Not overridden
        
    finally:
        os.unlink(temp_config_path)


@patch('retriever.planning.llm_planner.create_llm_client')
def test_end_to_end_planner_with_config(mock_create_client):
    """Test end-to-end planner functionality with configuration."""
    # Setup mock client
    mock_client = MagicMock()
    mock_client.predict.return_value = "pick_up(target=cup_0)\nnavigate_to(location=kitchen_1)"
    mock_create_client.return_value = mock_client
    
    # Create config
    import tempfile
    import os
    
    config_content = """
planner:
  planner_type: "LLMPlanner"
  client_type: "openai"
  client_kwargs:
    model: "gpt-4o"
    max_tokens: 1024

perception:
  model_name: "yolo11n"

robot_interface:
  robot_ip: "192.168.80.3"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_config_path = f.name
    
    try:
        cfg = load_config(temp_config_path)
        
        # Create planner from config
        planner = LLMPlanner(
            client_type=cfg.planner.client_type,
            client_kwargs=cfg.planner.client_kwargs
        )
        
        # Test data
        skills = [
            SkillSignature(name="pick_up", template="pick up {target}"),
            SkillSignature(name="navigate_to", template="navigate to {location}")
        ]
        objects = ObjectDescriptionDict(descriptions={
            "cup_0": "a red cup",
            "kitchen_1": "the kitchen area"
        })
        goal = NLCommand(text="take the cup to the kitchen")
        
        # Execute planning
        plan = planner((objects, goal, skills))
        
        # Verify results
        assert len(plan) == 2
        assert plan[0].signature.name == "pick_up"
        assert plan[0].grounded_params == {"target": "cup_0"}
        assert plan[1].signature.name == "navigate_to"
        assert plan[1].grounded_params == {"location": "kitchen_1"}
        
    finally:
        os.unlink(temp_config_path) 