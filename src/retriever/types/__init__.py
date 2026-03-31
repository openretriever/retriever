"""Shared Retriever type surface.

`retriever.types` is the umbrella import for:
- runtime and symbolic primitives
- shared schema/stream identity helpers used by recording and registry code
- schema-aware type registry helpers

Additional domain packages may register into this surface later, but this
package stays self-contained and dependency-light.
"""

from .compat import FRPConfig
from .core import Eff, Module, pure
from .schema import ClockDomain, SchemaRef, StreamId
from .skills import GroundedSkill, SkillSignature
from .symbolic import (
    GroundAtom,
    LiftedAtom,
    Object,
    ObjectType,
    Predicate,
    State,
    Variable,
)
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
