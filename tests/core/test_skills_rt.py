import pytest

from retriever.types.symbolic.skills import GroundedSkill, SkillSignature


def test_skill_signature_parsing_and_str():
    """
    Tests that parameters are correctly parsed from the template and that
    the string representation is correct.
    """
    sig = SkillSignature(
        name="move",
        template="move {actor} from {start} to {end}",
    )
    assert sig.parameters == ["actor", "start", "end"]
    assert str(sig) == "move(actor, start, end)"

    # Test with no parameters
    sig_no_params = SkillSignature(name="wave", template="wave to the crowd")
    assert sig_no_params.parameters == []
    assert str(sig_no_params) == "wave()"


def test_grounded_skill_creation_and_str():
    """
    Tests the creation and string representation of a GroundedSkill.
    """
    sig = SkillSignature(
        name="pick_up",
        template="pick up the {target}",
    )
    grounded_skill = GroundedSkill(
        signature=sig, grounded_params={"target": "red_cup_0"}
    )
    assert grounded_skill.signature == sig
    assert grounded_skill.grounded_params == {"target": "red_cup_0"}
    assert str(grounded_skill) == "pick_up(target=red_cup_0)"


def test_grounded_skill_param_mismatch():
    """
    Tests that GroundedSkill raises an error if parameters do not match the
    signature's template.
    """
    sig = SkillSignature(
        name="pick_up",
        template="pick up the {target}",
    )
    # Test with extra parameter
    with pytest.raises(ValueError, match="Mismatch between parameters"):
        GroundedSkill(
            signature=sig,
            grounded_params={"target": "red_cup_0", "extra": "blue_cup_1"},
        )
    # Test with missing parameter
    with pytest.raises(ValueError, match="Mismatch between parameters"):
        GroundedSkill(signature=sig, grounded_params={})


def test_grounded_skill_validation():
    """
    Tests the simplified validate_grounding method of GroundedSkill.
    This test no longer uses any typed objects.
    """
    # 1. Setup signature and a mock perception output.
    sig = SkillSignature(
        name="put_on",
        template="put {item} on {surface}",
    )
    perceived_objects = {
        "cup_0": "a red cup",
        "table_0": "a wooden table",
    }

    # 2. Test a valid grounding
    valid_skill = GroundedSkill(
        signature=sig, grounded_params={"item": "cup_0", "surface": "table_0"}
    )
    # Should not raise an error
    valid_skill.validate_grounding(perceived_objects)

    # 3. Test grounding with a non-existent object ID
    invalid_skill = GroundedSkill(
        signature=sig, grounded_params={"item": "cup_99", "surface": "table_0"}
    )
    with pytest.raises(ValueError, match="Grounded object ID 'cup_99' not found."):
        invalid_skill.validate_grounding(perceived_objects) 