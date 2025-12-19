from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Callable, List, Optional, Sequence, Set, Tuple, Dict, Union

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, order=True)
class Type:
    """Struct defining a type."""
    name: str
    feature_names: Sequence[str] = field(default_factory=list, repr=False)
    parent: Optional[Type] = field(default=None, repr=False)

    @property
    def dim(self) -> int:
        return len(self.feature_names)

    def get_ancestors(self) -> Set[Type]:
        curr_type: Optional[Type] = self
        ancestors_set = set()
        while curr_type is not None:
            ancestors_set.add(curr_type)
            curr_type = curr_type.parent
        return ancestors_set

    def __call__(self, name: str) -> _TypedEntity:
        if name.startswith("?"):
            return Variable(name, self)
        return Object(name, self)

    def __hash__(self) -> int:
        return hash((self.name, tuple(self.feature_names)))


@dataclass(frozen=True, order=True, repr=False)
class _TypedEntity:
    """An entity with a type, like an Object or a Variable."""
    name: str
    type: Type

    @cached_property
    def _str(self) -> str:
        return f"{self.name}:{self.type.name}"

    @cached_property
    def _hash(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return self._str

    def is_instance(self, t: Type) -> bool:
        cur_type: Optional[Type] = self.type
        while cur_type is not None:
            if cur_type == t:
                return True
            cur_type = cur_type.parent
        return False


@dataclass(frozen=True, order=True, repr=False)
class Object(_TypedEntity):
    """A concrete entity in the world."""
    def __post_init__(self) -> None:
        assert not self.name.startswith("?")

    def __hash__(self) -> int:
        return self._hash


@dataclass(frozen=True, order=True, repr=False)
class Variable(_TypedEntity):
    """A placeholder for an object in a lifted predicate or operator."""
    def __post_init__(self) -> None:
        assert self.name.startswith("?")

    def __hash__(self) -> int:
        return self._hash


@dataclass
class State:
    """A mapping from objects to their state feature vectors."""
    data: Dict[Object, NDArray]

    def __getitem__(self, key: Object) -> NDArray:
        return self.data[key]


@dataclass(frozen=True, order=False, repr=False)
class Predicate:
    """A classifier over states."""
    name: str
    types: Sequence[Type]
    _classifier: Callable[[State, Sequence[Object]], bool] = field(compare=False)

    def __call__(self, entities: Sequence[_TypedEntity]) -> _Atom:
        if all(isinstance(ent, Variable) for ent in entities):
            return LiftedAtom(self, entities)
        if all(isinstance(ent, Object) for ent in entities):
            return GroundAtom(self, entities)
        raise ValueError("Cannot instantiate Atom with mix of vars and objs")

    @cached_property
    def arity(self) -> int:
        return len(self.types)

    def holds(self, state: State, objects: Sequence[Object]) -> bool:
        assert len(objects) == self.arity
        for obj, pred_type in zip(objects, self.types):
            assert obj.is_instance(pred_type)
        return self._classifier(state, objects)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, repr=False, eq=False)
class _Atom:
    """A predicate applied to entities."""
    predicate: Predicate
    entities: Sequence[_TypedEntity]

    def __post_init__(self) -> None:
        assert len(self.entities) == self.predicate.arity
        for ent, pred_type in zip(self.entities, self.predicate.types):
            assert ent.is_instance(pred_type)

    @cached_property
    def _str(self) -> str:
        return (str(self.predicate) + "(" +
                ", ".join(map(str, self.entities)) + ")")

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass(frozen=True, repr=False, eq=False)
class LiftedAtom(_Atom):
    """An atom applied to variables."""
    @property
    def variables(self) -> Sequence[Variable]:
        return [v for v in self.entities if isinstance(v, Variable)]


@dataclass(frozen=True, repr=False, eq=False)
class GroundAtom(_Atom):
    """An atom applied to objects."""
    @property
    def objects(self) -> Sequence[Object]:
        return [o for o in self.entities if isinstance(o, Object)]

    def holds(self, state: State) -> bool:
        return self.predicate.holds(state, self.objects)
