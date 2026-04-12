from __future__ import annotations

from dataclasses import dataclass

from retriever import get_type, get_type_info, resolve_schema_ref
from retriever.registry.types import register_type
from retriever.types import ClockDomain, SchemaRef, StreamId
from retriever.types.data import DataSpec, DatasetManifest, EventBuffer
from retriever.types.data.v1 import DataSpec as PinnedDataSpec
from retriever.types.spatial import Header, PoseStamped, Quaternion, SE3Pose, Vector3
from retriever.types.spatial.v1 import PoseStamped as PinnedPoseStamped


@register_type(
    'ExamplePayload',
    category='tests',
    namespace='tests',
    version='v1',
    kind='payload',
    schema_name='tests/ExamplePayload',
)
@dataclass(frozen=True)
class ExamplePayload:
    value: int


def test_retriever_types_umbrella_exports_registry() -> None:
    assert get_type('SchemaRef') is SchemaRef
    assert get_type('ExamplePayload') is ExamplePayload
    assert get_type('PoseStamped') is PoseStamped
    assert get_type('DataSpec') is DataSpec


def test_shared_schema_types_are_registered_with_schema_metadata() -> None:
    info = get_type_info('StreamId')
    assert info.namespace == 'types'
    assert info.version == 'v1'
    assert info.kind == 'contract'
    assert info.schema_ref == SchemaRef(name='types/StreamId', version='v1', encoding='python')


def test_spatial_registry_exposes_schema_metadata() -> None:
    info = get_type_info('PoseStamped')
    assert info.namespace == 'spatial'
    assert info.version == 'v1'
    assert info.kind == 'payload'
    assert info.schema_ref == SchemaRef(name='spatial/PoseStamped', version='v1', encoding='python')


def test_data_registry_exposes_contract_metadata() -> None:
    info = get_type_info('DataSpec')
    assert info.namespace == 'data'
    assert info.kind == 'spec'
    assert info.schema_ref == SchemaRef(name='data/DataSpec', version='v1', encoding='python')


def test_resolve_schema_ref_uses_registry_for_instances() -> None:
    payload = ExamplePayload(value=3)
    assert resolve_schema_ref(payload) == SchemaRef(name='tests/ExamplePayload', version='v1', encoding='python')


def test_resolve_schema_ref_supports_builtin_schema_types() -> None:
    assert resolve_schema_ref(StreamId('camera/rgb')) == SchemaRef(name='types/StreamId', version='v1', encoding='python')
    assert resolve_schema_ref(ClockDomain('retriever_time')) == SchemaRef(name='types/ClockDomain', version='v1', encoding='python')


def test_resolve_schema_ref_supports_spatial_types() -> None:
    pose = PoseStamped(
        header=Header(stamp_ns=1, frame_id='map'),
        pose=SE3Pose(
            position=Vector3(0.0, 0.0, 0.0),
            orientation=Quaternion(0.0, 0.0, 0.0, 1.0),
        ),
    )
    assert resolve_schema_ref(pose) == SchemaRef(name='spatial/PoseStamped', version='v1', encoding='python')


def test_resolve_schema_ref_supports_data_contracts() -> None:
    buffer = EventBuffer()
    assert resolve_schema_ref(buffer) == SchemaRef(name='data/EventBuffer', version='v1', encoding='python')
    assert resolve_schema_ref(StreamId) == SchemaRef(name='types/StreamId', version='v1', encoding='python')
    assert resolve_schema_ref(DatasetManifest) == SchemaRef(name='data/DatasetManifest', version='v1', encoding='python')


def test_pinned_surfaces_match_canonical_types() -> None:
    assert PinnedDataSpec is DataSpec
    assert PinnedPoseStamped is PoseStamped
