"""Language-facing symbolic skill contracts.

These types sit above object-centric predicates/options. They are useful when a
planner or agent reasons in natural-language-like action templates and then
grounds those templates against perceived object ids.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import Dict, List


@dataclass(frozen=True)
class SkillSignature:
    """Template-level skill vocabulary for language-facing planning.

    Parameters are inferred from `{placeholder}` entries in the template string,
    so the signature stays compact while remaining inspectable.
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
    """A `SkillSignature` grounded with concrete perceived object ids."""

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

__all__ = ["GroundedSkill", "SkillSignature"]
