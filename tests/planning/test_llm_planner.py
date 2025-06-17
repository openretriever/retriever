import pytest
from unittest.mock import MagicMock

from retriever.core.skills import GroundedSkill, SkillSignature
from retriever.core.types import NLCommand, ObjectDescriptionDict
from retriever.models.api_models.clients import LLMClient
from retriever.planning.llm_planner import LLMPlanner


def test_llm_planner_parsing():
    """
    Tests that the LLMPlanner correctly parses a mocked LLM response.
    """
    # 1. Define the canned LLM response.
    mock_response = """
    pick_up(target=cup_0)
    put_on(item=cup_0, surface=table_1)
    """
    # 2. Setup the mocked client and the planner.
    mock_client = MagicMock(spec=LLMClient)
    mock_client.predict.return_value = mock_response
    planner = LLMPlanner(client=mock_client)

    # 3. Setup the planner inputs.
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

    # 4. Call the planner.
    plan = planner((objects, goal, available_skills))

    # 5. Assert the output is correct.
    assert len(plan) == 2
    assert plan[0].signature.name == "pick_up"
    assert plan[0].grounded_params == {"target": "cup_0"}
    assert plan[1].signature.name == "put_on"
    assert plan[1].grounded_params == {"item": "cup_0", "surface": "table_1"}
    mock_client.predict.assert_called_once()


def test_llm_planner_parsing_errors():
    """
    Tests that the planner raises errors for malformed LLM responses.
    """
    # Setup the mocked client and the planner.
    mock_client = MagicMock(spec=LLMClient)
    planner = LLMPlanner(client=mock_client)

    pick_up_skill = SkillSignature(name="pick_up", template="pick up {target}")
    objects = ObjectDescriptionDict(descriptions={"cup_0": "a red cup"})
    goal = NLCommand(text="do something")
    inputs = (objects, goal, [pick_up_skill])

    # Case 1: Malformed line that doesn't match the regex
    mock_client.predict.return_value = "drop_cup_on_floor"
    with pytest.raises(ValueError, match="Could not parse line"):
        planner(inputs)

    # Case 2: Response with a skill that doesn't exist
    mock_client.predict.return_value = "wave(target=cup_0)"
    with pytest.raises(ValueError, match="Unknown skill name"):
        planner(inputs)

    # Case 3: Response with a valid skill but invalid object ID
    mock_client.predict.return_value = "pick_up(target=cup_99)"
    with pytest.raises(ValueError, match="Grounded object ID 'cup_99' not found"):
        planner(inputs) 