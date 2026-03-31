from __future__ import annotations

from retriever import get_type_info, resolve_schema_ref
from retriever.data_spec import DataSpec, DatasetManifest, EventBuffer, SchemaRef, StreamId
from retriever.robotics_typing import PoseStamped, SE3Pose, Vector3, Quaternion, Header
from retriever.types import get_type


def test_retriever_types_umbrella_exports_registry() -> None:
    assert get_type("PoseStamped") is PoseStamped
    assert get_type("DataSpec") is DataSpec


def test_robotics_typing_registry_exposes_schema_metadata() -> None:
    info = get_type_info("PoseStamped")
    assert info.namespace == "robotics_typing"
    assert info.version == "v1"
    assert info.kind == "payload"
    assert info.schema_ref == SchemaRef(name="robotics/PoseStamped", version="v1", encoding="python")


def test_data_spec_registry_exposes_contract_metadata() -> None:
    info = get_type_info("DataSpec")
    assert info.namespace == "data_spec"
    assert info.kind == "spec"
    assert info.schema_ref == SchemaRef(name="data_spec/DataSpec", version="v1", encoding="python")


def test_resolve_schema_ref_uses_registry_for_instances() -> None:
    pose = PoseStamped(
        header=Header(stamp_ns=1, frame_id="map"),
        pose=SE3Pose(
            position=Vector3(0.0, 0.0, 0.0),
            orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        ),
    )
    assert resolve_schema_ref(pose) == SchemaRef(name="robotics/PoseStamped", version="v1", encoding="python")


def test_resolve_schema_ref_supports_data_spec_contracts() -> None:
    buffer = EventBuffer()
    assert resolve_schema_ref(buffer) == SchemaRef(name="data_spec/EventBuffer", version="v1", encoding="python")
    assert resolve_schema_ref(StreamId) == SchemaRef(name="data_spec/StreamId", version="v1", encoding="python")
    assert resolve_schema_ref(DatasetManifest) == SchemaRef(name="data_spec/DatasetManifest", version="v1", encoding="python")
