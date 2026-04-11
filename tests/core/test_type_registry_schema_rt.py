from __future__ import annotations

from dataclasses import dataclass

from retriever import get_type_info, resolve_schema_ref
from retriever.types import ClockDomain, SchemaRef, StreamId, get_type, register_type
from retriever.data_spec import DataSpec, DatasetManifest, EventBuffer
from retriever.data_spec import SchemaRef as DataSpecSchemaRef
from retriever.data_spec import StreamId as DataSpecStreamId
from retriever.robotics_typing import PoseStamped, SE3Pose, Vector3, Quaternion, Header


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
    assert get_type("PoseStamped") is PoseStamped
    assert get_type("DataSpec") is DataSpec


def test_shared_schema_types_are_registered_with_schema_metadata() -> None:
    info = get_type_info("StreamId")
    assert info.namespace == "types"
    assert info.version == "v1"
    assert info.kind == "contract"
    assert info.schema_ref == SchemaRef(name="types/StreamId", version="v1", encoding="python")


def test_robotics_typing_registry_exposes_schema_metadata() -> None:
    info = get_type_info("PoseStamped")
    assert info.namespace == "robotics_typing"
    assert info.version == "v1"
    assert info.kind == "payload"
    assert info.schema_ref == DataSpecSchemaRef(name="robotics/PoseStamped", version="v1", encoding="python")


def test_data_spec_registry_exposes_contract_metadata() -> None:
    info = get_type_info("DataSpec")
    assert info.namespace == "data_spec"
    assert info.kind == "spec"
    assert info.schema_ref == DataSpecSchemaRef(name="data_spec/DataSpec", version="v1", encoding="python")


def test_resolve_schema_ref_uses_registry_for_instances() -> None:
    payload = ExamplePayload(value=3)
    assert resolve_schema_ref(payload) == SchemaRef(name="tests/ExamplePayload", version="v1", encoding="python")


def test_resolve_schema_ref_supports_builtin_schema_types() -> None:
    assert resolve_schema_ref(StreamId("camera/rgb")) == SchemaRef(name="types/StreamId", version="v1", encoding="python")
    assert resolve_schema_ref(ClockDomain("retriever_time")) == SchemaRef(name="types/ClockDomain", version="v1", encoding="python")


def test_resolve_schema_ref_supports_robotics_types() -> None:
    pose = PoseStamped(
        header=Header(stamp_ns=1, frame_id="map"),
        pose=SE3Pose(
            position=Vector3(0.0, 0.0, 0.0),
            orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        ),
    )
    assert resolve_schema_ref(pose) == DataSpecSchemaRef(name="robotics/PoseStamped", version="v1", encoding="python")


def test_resolve_schema_ref_supports_data_spec_contracts() -> None:
    buffer = EventBuffer()
    assert resolve_schema_ref(buffer) == DataSpecSchemaRef(name="data_spec/EventBuffer", version="v1", encoding="python")
    assert resolve_schema_ref(DataSpecStreamId) == DataSpecSchemaRef(name="types/StreamId", version="v1", encoding="python")
    assert resolve_schema_ref(DatasetManifest) == DataSpecSchemaRef(name="data_spec/DatasetManifest", version="v1", encoding="python")
