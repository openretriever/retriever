import pytest
from unittest.mock import MagicMock, patch

from retriever.core.skills import GroundedSkill, SkillSignature
from retriever.core.types import NLCommand, ObjectDescriptionDict
from retriever.models.api_models.clients import LLMClient
from retriever.planning.llm_planner import LLMPlanner


class TestLLMPlanner:
    """Comprehensive test suite for the LLM planner."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock LLM client."""
        client = MagicMock(spec=LLMClient)
        return client
    
    @pytest.fixture
    def sample_skills(self):
        """Sample skills for testing."""
        return [
            SkillSignature(name="pick_up", template="pick up {target}"),
            SkillSignature(name="put_down", template="put down {item} on {surface}"),
            SkillSignature(name="navigate_to", template="navigate to {location}"),
        ]
    
    @pytest.fixture
    def sample_objects(self):
        """Sample objects for testing."""
        return ObjectDescriptionDict(
            descriptions={
                "cup_0": "a red coffee cup",
                "cup_1": "a blue water cup", 
                "cup_2": "a white tea cup",
                "table_1": "a wooden dining table",
                "kitchen_1": "the kitchen area",
            }
        )
    
    @pytest.fixture
    def sample_goal(self):
        """Sample goal for testing."""
        return NLCommand(text="remove 3 cups from the table")

    def test_successful_planning(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test successful plan generation and parsing."""
        # Setup mock response
        mock_response = """pick_up(target=cup_0)
navigate_to(location=kitchen_1)
put_down(item=cup_0, surface=kitchen_1)
pick_up(target=cup_1)
navigate_to(location=kitchen_1)
put_down(item=cup_1, surface=kitchen_1)"""
        
        mock_client.predict.return_value = mock_response
        planner = LLMPlanner(client=mock_client)
        
        # Test planning
        plan = planner((sample_objects, sample_goal, sample_skills))
        
        # Verify result
        assert len(plan) == 6
        assert plan[0].signature.name == "pick_up"
        assert plan[0].grounded_params == {"target": "cup_0"}
        assert plan[3].signature.name == "pick_up"
        assert plan[3].grounded_params == {"target": "cup_1"}
        
        # Verify client was called
        mock_client.predict.assert_called_once()
        
    def test_empty_llm_response(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test handling of empty LLM response."""
        mock_client.predict.return_value = None
        planner = LLMPlanner(client=mock_client)
        
        with pytest.raises(ValueError, match="Received empty response from the LLM client"):
            planner((sample_objects, sample_goal, sample_skills))
    
    def test_malformed_plan_response(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test handling of malformed LLM response."""
        mock_client.predict.return_value = "this is not a valid plan format"
        planner = LLMPlanner(client=mock_client)
        
        with pytest.raises(ValueError, match="Could not parse line"):
            planner((sample_objects, sample_goal, sample_skills))
    
    def test_unknown_skill_name(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test handling of unknown skill names in LLM response."""
        mock_client.predict.return_value = "unknown_skill(param=value)"
        planner = LLMPlanner(client=mock_client)
        
        with pytest.raises(ValueError, match="Unknown skill name"):
            planner((sample_objects, sample_goal, sample_skills))
    
    def test_unknown_object_id(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test handling of unknown object IDs in LLM response."""
        mock_client.predict.return_value = "pick_up(target=unknown_object)"
        planner = LLMPlanner(client=mock_client)
        
        with pytest.raises(ValueError, match="Grounded object ID 'unknown_object' not found"):
            planner((sample_objects, sample_goal, sample_skills))
    
    def test_malformed_parameters(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test handling of malformed parameters in skill calls."""
        mock_client.predict.return_value = "pick_up(invalid_param_format)"
        planner = LLMPlanner(client=mock_client)
        
        with pytest.raises(ValueError, match="Could not parse line"):
            planner((sample_objects, sample_goal, sample_skills))
    
    def test_empty_plan_lines(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test handling of empty lines in LLM response."""
        mock_response = """pick_up(target=cup_0)

put_down(item=cup_0, surface=table_1)

"""
        mock_client.predict.return_value = mock_response
        planner = LLMPlanner(client=mock_client)
        
        plan = planner((sample_objects, sample_goal, sample_skills))
        assert len(plan) == 2  # Empty lines should be ignored
    
    @patch('retriever.planning.llm_planner.create_llm_client')
    def test_default_client_creation(self, mock_create_client, sample_skills, sample_objects, sample_goal):
        """Test that the planner creates a default client when none is provided."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.predict.return_value = "pick_up(target=cup_0)"
        mock_create_client.return_value = mock_client
        
        planner = LLMPlanner()  # No client provided
        plan = planner((sample_objects, sample_goal, sample_skills))
        
        # Verify client factory was called with defaults
        mock_create_client.assert_called_once_with("openai", max_tokens=1024)
        assert len(plan) == 1
    
    @patch('retriever.planning.llm_planner.create_llm_client')
    def test_custom_client_kwargs(self, mock_create_client):
        """Test that custom client kwargs are passed through."""
        mock_client = MagicMock(spec=LLMClient)
        mock_create_client.return_value = mock_client
        
        custom_kwargs = {"model": "gpt-3.5-turbo", "temperature": 0.5}
        planner = LLMPlanner(client_type="openai", client_kwargs=custom_kwargs)
        
        expected_kwargs = custom_kwargs.copy()
        expected_kwargs["max_tokens"] = 1024  # Default added
        mock_create_client.assert_called_once_with("openai", **expected_kwargs)
    
    def test_prompt_construction(self, mock_client, sample_skills, sample_objects, sample_goal):
        """Test that the prompt is constructed correctly."""
        mock_client.predict.return_value = "pick_up(target=cup_0)"
        planner = LLMPlanner(client=mock_client)
        
        planner((sample_objects, sample_goal, sample_skills))
        
        # Get the prompt that was sent to the client
        call_args = mock_client.predict.call_args
        prompt = call_args[0][0]
        
        # Verify key sections are in the prompt
        assert "## Perceived Objects" in prompt
        assert "cup_0: a red coffee cup" in prompt
        assert "## Available Skills" in prompt
        assert "pick_up(target)" in prompt
        assert "## Goal" in prompt
        assert "remove 3 cups from the table" in prompt
        assert "## Plan" in prompt
    
    def test_no_parameters_skill(self, mock_client, sample_objects, sample_goal):
        """Test skills with no parameters."""
        skills_with_no_params = [
            SkillSignature(name="observe", template="observe the environment"),
            SkillSignature(name="pick_up", template="pick up {target}"),
        ]
        
        mock_client.predict.return_value = "observe()\npick_up(target=cup_0)"
        planner = LLMPlanner(client=mock_client)
        
        plan = planner((sample_objects, sample_goal, skills_with_no_params))
        
        assert len(plan) == 2
        assert plan[0].signature.name == "observe"
        assert plan[0].grounded_params == {}
        assert plan[1].signature.name == "pick_up"
        assert plan[1].grounded_params == {"target": "cup_0"} 