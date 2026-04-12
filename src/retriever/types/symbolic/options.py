from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence, Set

from numpy.typing import NDArray

from retriever.flow import io
from .objects import GroundAtom, Object, ObjectType, State


@io
class Action:
    """An action in an environment.

    This is a light wrapper around a numpy float array that can
    optionally store the option which produced it.
    """

    arr: NDArray
    option: Optional[Any] = field(
        repr=False, default=None
    )  # Typed as Any to avoid serialization issues with callables
    extra_info: Optional[Any] = None

    def set_option(self, option: "Option") -> None:
        self.option = option


@dataclass
class Option:
    """Struct defining an option (temporally extended action/skill).

    An option consists of:
    - Policy: State -> Action
    - Initiation Set: State -> bool (Can this option start?)
    - Termination Condition: State -> bool (Should this option stop?)

    This matches the specific Option definition from Predicators.

    Note: To support pickling for multiprocessing backends, we store
    the parent ParameterizedOption reference and call its methods
    instead of storing closures.
    """

    name: str

    # Context for this specific option instance
    parent: Optional["ParameterizedOption"] = field(repr=False, default=None)
    objects: Sequence[Object] = field(default_factory=list)
    params: Sequence[float] = field(default_factory=list)
    memory: dict = field(default_factory=dict, repr=False)

    def policy(self, state: State) -> Action:
        """Execute policy for this option."""
        if self.parent is None:
            raise ValueError("Option has no parent ParameterizedOption")
        return self.parent.policy(state, self.memory, self.objects, self.params)

    def initiable(self, state: State) -> bool:
        """Check if this option can be initiated."""
        if self.parent is None:
            raise ValueError("Option has no parent ParameterizedOption")
        return self.parent.initiable(state, self.memory, self.objects, self.params)

    def terminal(self, state: State) -> bool:
        """Check if this option should terminate."""
        if self.parent is None:
            raise ValueError("Option has no parent ParameterizedOption")
        return self.parent.terminal(state, self.memory, self.objects, self.params)

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass(frozen=True)
class ParameterizedOption:
    """Struct defining a parameterized option.

    This acts as a factory for Options. It takes specific objects and parameters
    to "ground" into a concrete Option execution unit.
    """

    name: str
    types: Sequence[ObjectType]

    # Generators
    policy: Callable[[State, dict, Sequence[Object], Sequence[float]], Action] = field(
        repr=False
    )
    initiable: Callable[[State, dict, Sequence[Object], Sequence[float]], bool] = field(
        repr=False
    )
    terminal: Callable[[State, dict, Sequence[Object], Sequence[float]], bool] = field(
        repr=False
    )

    def ground(self, objects: Sequence[Object], params: Sequence[float]) -> Option:
        """Ground into an Option, given objects and parameter values.

        The returned Option stores a reference to this ParameterizedOption
        and calls its methods with the stored context. This design supports
        pickling for multiprocessing backends.
        """
        memory = {}  # specific memory for this grounded option instance

        return Option(
            name=self.name,
            parent=self,
            objects=list(objects),  # Convert to list for pickling
            params=list(params),  # Convert to list for pickling
            memory=memory,
        )


@dataclass
class Task:
    """Struct defining a planning task."""

    init: State
    goal: Set[GroundAtom]


__all__ = ["Action", "Option", "ParameterizedOption", "Task"]
