import pytest
from unittest.mock import MagicMock, patch

import dspy

from retriever.core.skills import GroundedSkill, SkillSignature
from retriever.core.types import NLCommand, ObjectDescriptionDict
from retriever.planning.dspy_llm_planner import DSPyLLMPlanner


@patch("dspy.Predict")
def test_dspy_llm_planner_parsing(MockPredict):
    """
    Tests that the DSPyLLMPlanner correctly parses a mocked LLM response.
    """
    # 1. Define the canned LLM response.
    mock_response = """
    pick_up(target=cup_0)
    put_on(item=cup_0, surface=table_1)
    """
    # Mock the predictor instance and its return value
    mock_predictor_instance = MagicMock()
    mock_predictor_instance.return_value = dspy.Prediction(plan=mock_response)
    MockPredict.return_value = mock_predictor_instance

    # 2. Setup the planner and its inputs.
    # Configure a dummy LM to satisfy the planner's constructor
    dspy.settings.configure(lm=dspy.OpenAI(model="gpt-3.5-turbo"))
    planner = DSPyLLMPlanner()

    pick_up_skill = SkillSignature(name="pick_up", template="pick up {target}")
    put_on_skill = SkillSignature(
        name="put_on", template="put {item} on {surface}"
    )
    available_skills = [pick_up_skill, put_on_skill]

    objects = ObjectDescriptionDict(
        descriptions={
            "cup_0": "a red cup",
            "table_1": "a wooden table",
        }
    )
    goal = NLCommand(text="put the red cup on the table")

    # 3. Call the planner.
    plan = planner((objects, goal, available_skills))

    # 4. Assert the output is correct.
    assert len(plan) == 2
    assert plan[0].signature.name == "pick_up"
    assert plan[0].grounded_params == {"target": "cup_0"}
    assert plan[1].signature.name == "put_on"
    assert plan[1].grounded_params == {"item": "cup_0", "surface": "table_1"}

    # Clean up global settings
    dspy.settings.configure(lm=None)


@patch("dspy.Predict")
def test_dspy_llm_planner_parsing_errors(MockPredict):
    """
    Tests that the planner raises errors for malformed LLM responses.
    """
    # Setup mocks and planner
    mock_predictor_instance = MagicMock()
    MockPredict.return_value = mock_predictor_instance
    dspy.settings.configure(lm=dspy.OpenAI(model="gpt-3.5-turbo"))
    planner = DSPyLLMPlanner()

    pick_up_skill = SkillSignature(name="pick_up", template="pick up {target}")
    objects = ObjectDescriptionDict(descriptions={"cup_0": "a red cup"})
    goal = NLCommand(text="do something")
    inputs = (objects, goal, [pick_up_skill])

    # Case 1: Malformed line that doesn't match the regex
    mock_predictor_instance.return_value = dspy.Prediction(plan="drop_cup_on_floor")
    with pytest.raises(ValueError, match="Could not parse line"):
        planner(inputs)

    # Case 2: Response with a skill that doesn't exist
    mock_predictor_instance.return_value = dspy.Prediction(plan="wave(target=cup_0)")
    with pytest.raises(ValueError, match="Unknown skill name"):
        planner(inputs)

    # Case 3: Response with a valid skill but invalid object ID
    mock_predictor_instance.return_value = dspy.Prediction(
        plan="pick_up(target=cup_99)"
    )
    with pytest.raises(ValueError, match="Grounded object ID 'cup_99' not found"):
        planner(inputs)

    # Clean up global settings
    dspy.settings.configure(lm=None) 