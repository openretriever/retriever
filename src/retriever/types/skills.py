from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import Dict, List


@dataclass(frozen=True)
class SkillSignature:
    """
    Defines the signature of a skill in a flexible, language-centric way.
    The parameters are implicitly defined by placeholders in the template.

    This serves as the "vocabulary" for an LLM-based planner. For example:
    SkillSignature(
        name="put_on",
        template="put {target} on {destination}",
    )
    """

    name: str
    template: str

    @cached_property
    def parameters(self) -> List[str]:
        """A list of parameter names extracted from the template string."""
        return re.findall(r"\{(.*?)\}", self.template)

    def __str__(self) -> str:
        params_str = ", ".join(self.parameters)
        return f"{self.name}({params_str})"


@dataclass(frozen=True)
class GroundedSkill:
    """
    Represents a SkillSignature grounded with concrete object IDs from perception.

    This is the structured output expected from an LLM-based planner. For example:
    GroundedSkill(
        signature=put_on_signature,
        grounded_params={"target": "red_cup_0", "destination": "table_1"}
    )
    """

    signature: SkillSignature
    grounded_params: Dict[str, str]  # param name -> object_id

    def __post_init__(self) -> None:
        if set(self.signature.parameters) != set(self.grounded_params.keys()):
            raise ValueError(
                "Mismatch between parameters in signature and grounded parameters."
            )

    def __str__(self) -> str:
        """
        Returns a string representation of the grounded skill.
        """
        params_str = ", ".join(
            f"{k}={v}" for k, v in self.grounded_params.items()
        )
        return f"{self.signature.name}({params_str})"

    def validate_grounding(self, perceived_objects: Dict[str, str]) -> None:
        """
        Checks if the grounded object IDs exist in the perception output.
        Semantic correctness (e.g., type checking) is handled by the LLM.
        """
        for obj_id in self.grounded_params.values():
            if obj_id not in perceived_objects:
                raise ValueError(f"Grounded object ID '{obj_id}' not found.") 