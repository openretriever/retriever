"""Schema-aware type registry for Retriever payload and contract discovery.

This registry sits between domain packages such as `retriever.robotics_typing`
and `retriever.data_spec`, and downstream consumers such as recording/export
layers. It intentionally stays lightweight:

- register Python classes under stable names
- carry optional schema metadata for recording/export
- support simple discovery and category/tag filtering
- preserve older decorator ergonomics used by legacy tests/examples
"""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, TypeVar

from retriever.utils import load_plugins

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _ensure_plugins_loaded() -> None:
    try:
        load_plugins()
    except Exception:
        pass


@dataclass(frozen=True)
class TypeInfo:
    """Metadata for a registered Retriever type."""

    type_class: Type[Any]
    name: str
    category: str
    module: str
    description: str = ""
    tags: Tuple[str, ...] = field(default_factory=tuple)
    namespace: str = ""
    version: str = ""
    kind: str = "payload"
    aliases: Tuple[str, ...] = field(default_factory=tuple)
    schema_name: Optional[str] = None
    schema_version: str = "v1"
    schema_encoding: str = "python"
    arrow_converter: Optional[Callable[[Any], Any]] = None

    @property
    def canonical_import(self) -> str:
        return f"{self.module}.{self.type_class.__name__}"

    @property
    def schema_ref(self) -> Any:
        """Return a `SchemaRef` lazily when schema metadata is present."""
        if self.schema_name is None:
            return None
        from retriever.data_spec import SchemaRef

        return SchemaRef(
            name=self.schema_name,
            version=self.schema_version,
            encoding=self.schema_encoding,
        )


class TypeRegistry:
    """Global registry for Retriever payload and contract types."""

    def __init__(self) -> None:
        self._types: Dict[str, TypeInfo] = {}
        self._types_by_class: Dict[Type[Any], TypeInfo] = {}
        self._aliases: Dict[str, str] = {}
        self._categories: Dict[str, Dict[str, TypeInfo]] = defaultdict(dict)

    def register(
        self,
        name_or_cls: Optional[Type[T] | str] = None,
        *,
        category: str = "general",
        description: str = "",
        tags: Optional[Iterable[str]] = None,
        namespace: str = "",
        version: str = "",
        kind: str = "payload",
        aliases: Optional[Iterable[str]] = None,
        schema_name: Optional[str] = None,
        schema_version: str = "v1",
        schema_encoding: str = "python",
        arrow_converter: Optional[Callable[[Any], Any]] = None,
    ) -> Callable[[Type[T]], Type[T]] | Type[T]:
        """Register a type, supporting both bare and configured decorators.

        Examples:
            @register_type
            class MyType: ...

            @register_type("PoseStamped", category="robotics", schema_name="robotics/PoseStamped")
            class PoseStamped: ...
        """

        def decorator(cls: Type[T]) -> Type[T]:
            name = cls.__name__ if not isinstance(name_or_cls, str) else name_or_cls
            self._register_type(
                cls,
                name=name,
                category=category,
                description=description,
                tags=tuple(tags or ()),
                namespace=namespace,
                version=version,
                kind=kind,
                aliases=tuple(aliases or ()),
                schema_name=schema_name,
                schema_version=schema_version,
                schema_encoding=schema_encoding,
                arrow_converter=arrow_converter,
            )
            return cls

        if inspect.isclass(name_or_cls):
            return decorator(name_or_cls)
        return decorator

    def _register_type(
        self,
        cls: Type[T],
        *,
        name: str,
        category: str,
        description: str,
        tags: Tuple[str, ...],
        namespace: str,
        version: str,
        kind: str,
        aliases: Tuple[str, ...],
        schema_name: Optional[str],
        schema_version: str,
        schema_encoding: str,
        arrow_converter: Optional[Callable[[Any], Any]],
    ) -> None:
        existing = self._types.get(name)
        if existing and existing.type_class != cls:
            logger.warning(
                "Overriding type '%s' (was %s, now %s)",
                name,
                existing.type_class.__name__,
                cls.__name__,
            )

        info = TypeInfo(
            type_class=cls,
            name=name,
            category=category,
            module=cls.__module__,
            description=description,
            tags=tags,
            namespace=namespace,
            version=version,
            kind=kind,
            aliases=aliases,
            schema_name=schema_name,
            schema_version=schema_version,
            schema_encoding=schema_encoding,
            arrow_converter=arrow_converter,
        )

        self._types[name] = info
        self._types_by_class[cls] = info
        self._categories[category][name] = info
        for alias in aliases:
            if alias != name:
                self._aliases[alias] = name

        cls._retriever_type_name = name
        cls._retriever_type_category = category
        cls._retriever_type_namespace = namespace
        cls._retriever_type_version = version
        cls._retriever_type_kind = kind
        cls._retriever_registered = True

    def _resolve_name(self, name: str) -> str:
        return self._aliases.get(name, name)

    def get_type(self, name: str) -> Type[Any]:
        _ensure_plugins_loaded()
        resolved = self._resolve_name(name)
        if resolved not in self._types:
            available = sorted(set(self._types.keys()) | set(self._aliases.keys()))
            raise ValueError(f"Type '{name}' not registered. Available: {available}")
        return self._types[resolved].type_class

    def get_type_info(self, name_or_type: str | Type[Any]) -> TypeInfo:
        _ensure_plugins_loaded()
        if isinstance(name_or_type, str):
            resolved = self._resolve_name(name_or_type)
            if resolved not in self._types:
                available = sorted(set(self._types.keys()) | set(self._aliases.keys()))
                raise ValueError(f"Type '{name_or_type}' not registered. Available: {available}")
            return self._types[resolved]

        try:
            return self._types_by_class[name_or_type]
        except KeyError:
            raise ValueError(f"Type class '{name_or_type}' not registered.") from None

    def list_types(self, category: Optional[str] = None) -> Dict[str, TypeInfo]:
        _ensure_plugins_loaded()
        if category is None:
            return dict(self._types)
        return dict(self._categories.get(category, {}))

    def get_registered_types(self, category: Optional[str] = None) -> Dict[str, TypeInfo]:
        return self.list_types(category=category)

    def is_registered(self, type_class: Type[Any]) -> bool:
        _ensure_plugins_loaded()
        return type_class in self._types_by_class

    def get_type_name(self, type_class: Type[Any]) -> Optional[str]:
        _ensure_plugins_loaded()
        info = self._types_by_class.get(type_class)
        return info.name if info else None

    def find_types(
        self,
        *,
        category: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        namespace: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> Dict[str, TypeInfo]:
        _ensure_plugins_loaded()
        infos = self.list_types(category=category)
        wanted_tags = set(tags or ())
        results: Dict[str, TypeInfo] = {}
        for name, info in infos.items():
            if namespace is not None and info.namespace != namespace:
                continue
            if kind is not None and info.kind != kind:
                continue
            if wanted_tags and not wanted_tags.issubset(set(info.tags)):
                continue
            results[name] = info
        return results

    def resolve_schema_ref(self, value_or_type: Any) -> Any:
        """Resolve a registered `SchemaRef` for a value or type if available."""
        _ensure_plugins_loaded()
        cls = value_or_type if inspect.isclass(value_or_type) else type(value_or_type)
        info = self._types_by_class.get(cls)
        return info.schema_ref if info else None

    def get_arrow_converter(self, type_class: Type[Any]) -> Optional[Callable[[Any], Any]]:
        info = self._types_by_class.get(type_class)
        return info.arrow_converter if info else None


_global_type_registry = TypeRegistry()


def register_type(
    name_or_cls: Optional[Type[T] | str] = None,
    *,
    category: str = "general",
    description: str = "",
    tags: Optional[Iterable[str]] = None,
    namespace: str = "",
    version: str = "",
    kind: str = "payload",
    aliases: Optional[Iterable[str]] = None,
    schema_name: Optional[str] = None,
    schema_version: str = "v1",
    schema_encoding: str = "python",
    arrow_converter: Optional[Callable[[Any], Any]] = None,
) -> Callable[[Type[T]], Type[T]] | Type[T]:
    return _global_type_registry.register(
        name_or_cls,
        category=category,
        description=description,
        tags=tags,
        namespace=namespace,
        version=version,
        kind=kind,
        aliases=aliases,
        schema_name=schema_name,
        schema_version=schema_version,
        schema_encoding=schema_encoding,
        arrow_converter=arrow_converter,
    )


def get_type(name: str) -> Type[Any]:
    return _global_type_registry.get_type(name)


def get_type_info(name_or_type: str | Type[Any]) -> TypeInfo:
    return _global_type_registry.get_type_info(name_or_type)


def list_types(category: Optional[str] = None) -> Dict[str, TypeInfo]:
    return _global_type_registry.list_types(category=category)


def get_registered_types(category: Optional[str] = None) -> Dict[str, TypeInfo]:
    return _global_type_registry.get_registered_types(category=category)


def find_types(
    *,
    category: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    namespace: Optional[str] = None,
    kind: Optional[str] = None,
) -> Dict[str, TypeInfo]:
    return _global_type_registry.find_types(
        category=category,
        tags=tags,
        namespace=namespace,
        kind=kind,
    )


def is_registered_type(type_class: Type[Any]) -> bool:
    return _global_type_registry.is_registered(type_class)


def get_type_name(type_class: Type[Any]) -> Optional[str]:
    return _global_type_registry.get_type_name(type_class)


def get_global_registry() -> TypeRegistry:
    return _global_type_registry


def resolve_schema_ref(value_or_type: Any) -> Any:
    return _global_type_registry.resolve_schema_ref(value_or_type)


def convert_to_arrow(obj: Any) -> Any:
    converter = _global_type_registry.get_arrow_converter(type(obj))
    return converter(obj) if converter else obj


def convert_from_arrow(arrow_obj: Any, target_type: Optional[Type[Any]] = None) -> Any:
    if target_type is None:
        return arrow_obj
    try:
        return target_type(arrow_obj)
    except Exception:
        return arrow_obj


__all__ = [
    "TypeInfo",
    "TypeRegistry",
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
    "register_type",
    "resolve_schema_ref",
]
