"""
Type Registry System for Data Type Discovery and Introspection

Enables registering custom I/O types (dataclasses) for use in the ecosystem:
- @register_type("Pose2D") decorator for easy registration
- list_types() for discovery
"""

from typing import Dict, Type, Optional, Callable, TypeVar, List, Iterable
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from retriever.utils import load_plugins

logger = logging.getLogger(__name__)

T = TypeVar('T')

def _ensure_plugins_loaded() -> None:
    try:
        load_plugins()
    except Exception:
        pass

@dataclass
class TypeInfo:
    """Information about a registered IO Type."""
    type_class: Type
    name: str
    category: str
    module: str
    description: str = ""
    tags: List[str] = field(default_factory=list)

class TypeRegistry:
    """Global registry for IO types."""
    
    def __init__(self):
        self._types: Dict[str, TypeInfo] = {}
        self._categories: Dict[str, Dict[str, TypeInfo]] = defaultdict(dict)
    
    def register(self, 
                 name: str,
                 category: str = "general",
                 description: str = "",
                 tags: Optional[Iterable[str]] = None) -> Callable[[Type[T]], Type[T]]:
        """
        Register a Type for discovery.
        
        Args:
            name: Unique name (e.g., "Frame", "Pose2D")
            category: Category (e.g., "vision", "geometry")
            description: Human-readable description
            tags: Tags for filtering
        """
        def decorator(cls: Type[T]) -> Type[T]:
            self._register_type(cls, name, category, description, list(tags or []))
            return cls
        return decorator
    
    def _register_type(self, 
                       cls: Type[T], 
                       name: str, 
                       category: str,
                       description: str,
                       tags: List[str]) -> None:
        
        if name in self._types:
            existing = self._types[name]
            if existing.type_class != cls:
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
            tags=tags
        )
        
        self._types[name] = info
        self._categories[category][name] = info
        
        # Metadata
        cls._retriever_type_name = name
        cls._retriever_type_category = category
        cls._retriever_registered = True

    def get_type(self, name: str) -> Type:
        """Get a Type class by name."""
        _ensure_plugins_loaded()
        if name not in self._types:
            available = list(self._types.keys())
            raise ValueError(f"Type '{name}' not registered. Available: {available}")
        return self._types[name].type_class

    def list_types(self, category: Optional[str] = None) -> Dict[str, TypeInfo]:
        """List registered types."""
        _ensure_plugins_loaded()
        if category is None:
            return dict(self._types)
        return dict(self._categories.get(category, {}))
    
    def find_types(self, 
                   category: Optional[str] = None,
                   tags: Optional[Iterable[str]] = None) -> Dict[str, TypeInfo]:
        """Find types by category or tags."""
        _ensure_plugins_loaded()
        types = self.list_types(category)
        if not tags:
            return types
            
        wanted = set(tags)
        return {name: info for name, info in types.items() if wanted.issubset(set(info.tags))}


_global_type_registry = TypeRegistry()

# Public API
def register_type(name: str, 
                 category: str = "general",
                 description: str = "",
                 tags: Optional[Iterable[str]] = None) -> Callable[[Type[T]], Type[T]]:
    return _global_type_registry.register(name, category, description, tags)

def get_type(name: str) -> Type:
    return _global_type_registry.get_type(name)

def list_types(category: Optional[str] = None) -> Dict[str, TypeInfo]:
    return _global_type_registry.list_types(category)

def find_types(category: Optional[str] = None,
               tags: Optional[Iterable[str]] = None) -> Dict[str, TypeInfo]:
    return _global_type_registry.find_types(category, tags)
