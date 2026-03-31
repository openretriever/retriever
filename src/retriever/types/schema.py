from __future__ import annotations

from dataclasses import dataclass

from retriever.types_registry import register_type

_TYPES_CATEGORY = "types"
_TYPES_NAMESPACE = "types"
_TYPES_VERSION = "v1"


def _register_shared_type(
    name: str,
    *,
    kind: str = "contract",
    tags: tuple[str, ...] = ("types", "schema", "v1"),
):
    return register_type(
        name,
        category=_TYPES_CATEGORY,
        namespace=_TYPES_NAMESPACE,
        version=_TYPES_VERSION,
        kind=kind,
        tags=tags,
        schema_name=f"types/{name}",
        schema_version=_TYPES_VERSION,
        description=f"retriever.types {name} contract",
    )


@_register_shared_type("StreamId", tags=("types", "v1", "stream"))
@dataclass(frozen=True, order=True)
class StreamId:
    """Stable stream identifier used by registry and recording layers."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("stream id must be non-empty")

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def parse(value: str | "StreamId") -> "StreamId":
        if isinstance(value, StreamId):
            return value
        return StreamId(value=value)


@_register_shared_type("ClockDomain", tags=("types", "v1", "clock"))
@dataclass(frozen=True)
class ClockDomain:
    """Clock domain label for recorded or surfaced streams."""

    name: str = "event_time"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("clock domain name must be non-empty")


@_register_shared_type("SchemaRef", tags=("types", "v1", "schema"))
@dataclass(frozen=True)
class SchemaRef:
    """Schema identity for typed payloads and contracts."""

    name: str
    version: str = "v1"
    encoding: str = "python"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("schema name must be non-empty")
        if not self.version:
            raise ValueError("schema version must be non-empty")


__all__ = ["ClockDomain", "SchemaRef", "StreamId"]
