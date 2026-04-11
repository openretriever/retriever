"""Retriever type system: primitives, registry, and domain type packages.

`retriever.types` is the umbrella for:
- shared schema/stream identity primitives: `ClockDomain`, `SchemaRef`, `StreamId`
- runtime/language primitives: `Eff`, symbolic objects, skills
- the schema-aware type registry: `register_type`, `get_type`, ...
- domain type subpackages:
  - `retriever.types.data_spec`  — event/data contracts, manifests, join policies
  - `retriever.types.robotics`   — robotics payload standard (PoseStamped, JointState, ...)

Compat aliases `retriever.data_spec` and `retriever.robotics_typing` still work.
"""

from .core import Eff, pure, Module
from .schema import ClockDomain, SchemaRef, StreamId
from .symbolic import (
    GroundAtom,
    LiftedAtom,
    Object,
    ObjectType,
    Predicate,
    State,
    Variable,
)
from .skills import SkillSignature, GroundedSkill
from .compat import FRPConfig
from .registry import (
    TypeInfo,
    TypeRegistry,
    convert_from_arrow,
    convert_to_arrow,
    find_types,
    get_global_registry,
    get_registered_types,
    get_type,
    get_type_info,
    get_type_name,
    is_registered_type,
    list_types,
    register_type,
    resolve_schema_ref,
)

__all__ = [
    "ClockDomain",
    "Eff",
    "FRPConfig",
    "GroundAtom",
    "GroundedSkill",
    "LiftedAtom",
    "Module",
    "Object",
    "ObjectType",
    "Predicate",
    "SchemaRef",
    "SkillSignature",
    "State",
    "StreamId",
    "TypeInfo",
    "TypeRegistry",
    "Variable",
    "convert_from_arrow",
    "convert_to_arrow",
    "find_types",
    "get_global_registry",
    "get_registered_types",
    "get_type",
    "get_type_info",
    "get_type_name",
    "is_registered_type",
    "list_types",
    "pure",
    "register_type",
    "resolve_schema_ref",
]
