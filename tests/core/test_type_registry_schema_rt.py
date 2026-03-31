from __future__ import annotations

from dataclasses import dataclass

from retriever import get_type_info, resolve_schema_ref
from retriever.types import ClockDomain, SchemaRef, StreamId, get_type, register_type


@register_type(
    "ExamplePayload",
    category="tests",
    namespace="tests",
    version="v1",
    kind="payload",
    schema_name="tests/ExamplePayload",
)
@dataclass(frozen=True)
class ExamplePayload:
    value: int


def test_retriever_types_umbrella_exports_registry() -> None:
    assert get_type("SchemaRef") is SchemaRef
    assert get_type("ExamplePayload") is ExamplePayload


def test_shared_schema_types_are_registered_with_schema_metadata() -> None:
    info = get_type_info("StreamId")
    assert info.namespace == "types"
    assert info.version == "v1"
    assert info.kind == "contract"
    assert info.schema_ref == SchemaRef(name="types/StreamId", version="v1", encoding="python")


def test_resolve_schema_ref_uses_registry_for_instances() -> None:
    payload = ExamplePayload(value=3)
    assert resolve_schema_ref(payload) == SchemaRef(name="tests/ExamplePayload", version="v1", encoding="python")


def test_resolve_schema_ref_supports_builtin_schema_types() -> None:
    assert resolve_schema_ref(StreamId("camera/rgb")) == SchemaRef(name="types/StreamId", version="v1", encoding="python")
    assert resolve_schema_ref(ClockDomain("retriever_time")) == SchemaRef(name="types/ClockDomain", version="v1", encoding="python")
