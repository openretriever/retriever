"""Retriever type system: primitives, registry, and canonical domain packages.

`retriever.types` is the umbrella for:
- shared schema/stream identity primitives: `ClockDomain`, `SchemaRef`, `StreamId`
- runtime/language primitives: `Eff`, symbolic objects, skills
- the schema-aware type registry: `register_type`, `get_type`, ...
- domain type subpackages:
  - `retriever.types.data`     — event/data contracts, manifests, join policies
  - `retriever.types.spatial`  — spatial payload standard (PoseStamped, JointState, ...)
  - `retriever.types.symbolic` — object-centric planning contracts (objects, options, skills)
"""

from .core import Eff, pure, Module
from .schema import ClockDomain, SchemaRef, StreamId
from .symbolic import (
    Action,
    GroundAtom,
    GroundedSkill,
    LiftedAtom,
    Object,
    ObjectType,
    Option,
    ParameterizedOption,
    Predicate,
    SkillSignature,
    State,
    Task,
    Variable,
)
from .compat import FRPConfig
from . import data, spatial
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
    "Action",
    "ClockDomain",
    "Eff",
    "FRPConfig",
    "GroundAtom",
    "GroundedSkill",
    "LiftedAtom",
    "Module",
    "Object",
    "ObjectType",
    "Option",
    "ParameterizedOption",
    "Predicate",
    "SchemaRef",
    "SkillSignature",
    "State",
    "Task",
    "StreamId",
    "TypeInfo",
    "TypeRegistry",
    "Variable",
    "data",
    "spatial",
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
