"""Registry for discoverable `Flow` classes.

Use this registry when a flow should be selectable by name rather than imported
directly. The public contract is intentionally small:

- `@register_flow("camera")` to publish a class
- `get_flow("camera")` to construct a fresh instance
- `get_flow_class("camera")` to inspect the class itself
- optional best-effort plugin loading via `retriever.plugins`
"""

from typing import Dict, Type, Optional, Callable, TypeVar, TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict
import logging

from retriever.flow.base import Flow as FlowBase
from retriever.utils import load_plugins

logger = logging.getLogger(__name__)
_plugins_load_warning_emitted = False

if TYPE_CHECKING:
    from retriever.flow.base import Flow

F = TypeVar('F', bound=FlowBase)


def _ensure_plugins_loaded() -> None:
    global _plugins_load_warning_emitted
    # Best-effort plugin loading: enables external packages to register flows.
    try:
        load_plugins()
    except Exception:
        if not _plugins_load_warning_emitted:
            logger.warning(
                "Failed to load retriever flow plugins; continuing with local registry only.",
                exc_info=True,
            )
            _plugins_load_warning_emitted = True

@dataclass 
class FlowInfo:
    """Information about a registered Flow component."""
    flow_class: Type['Flow']
    name: str
    category: str
    module: str
    input_type: Optional[Type] = None
    output_type: Optional[Type] = None
    description: str = ""
    tags: list = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class FlowRegistry:
    """Registry of named `Flow` classes and their lightweight metadata."""
    
    def __init__(self):
        self._flows: Dict[str, FlowInfo] = {}
        self._categories: Dict[str, Dict[str, FlowInfo]] = defaultdict(dict)
        self._flow_to_name: Dict[Type, str] = {}
    
    def register(self, 
                 name: str,
                 category: str = "general",
                 description: str = "",
                 tags: Optional[list] = None) -> Callable[[Type[F]], Type[F]]:
        """
        Register a Flow component for easy discovery and substitution.
        
        Args:
            name: Unique name for this flow (e.g., "camera", "yolo_detector")
            category: Category for organization (e.g., "vision", "control", "planning")
            description: Human-readable description
            tags: List of tags for filtering/search
            
        Returns:
            Decorator function that registers the Flow class
            
        Example:
            @register_flow("camera", category="vision", description="Default camera flow")
            class WebcamFlow(Flow[None, RGBImage]):
                def step(self, _): return capture_webcam()
                
            # Later: camera = get_flow("camera")
        """
        def decorator(flow_class: Type[F]) -> Type[F]:
            return self._register_flow(flow_class, name, category, description, tags or [])
        return decorator
    
    def _register_flow(self, 
                      flow_class: Type[F], 
                      name: str, 
                      category: str,
                      description: str,
                      tags: list) -> Type[F]:
        """Internal registration logic."""

        if not issubclass(flow_class, FlowBase):
            raise TypeError(
                f"register_flow('{name}') expects a retriever.flow.Flow subclass, "
                f"got: {flow_class}"
            )
        
        # Extract type information from Flow[I, O] if available
        input_type, output_type = self._extract_flow_types(flow_class)
        
        # Check for conflicts
        if name in self._flows:
            existing = self._flows[name]
            if existing.flow_class != flow_class:
                logger.warning(
                    "Overriding flow '%s' (was %s, now %s)",
                    name,
                    existing.flow_class.__name__,
                    flow_class.__name__,
                )
        
        # Create flow info
        flow_info = FlowInfo(
            flow_class=flow_class,
            name=name,
            category=category,
            module=flow_class.__module__,
            input_type=input_type,
            output_type=output_type,
            description=description,
            tags=tags
        )
        
        # Register in both main registry and category registry
        self._flows[name] = flow_info
        self._categories[category][name] = flow_info
        self._flow_to_name[flow_class] = name
        
        # Add metadata to the class for introspection
        flow_class._retriever_flow_name = name
        flow_class._retriever_flow_category = category
        flow_class._retriever_registered = True
        
        return flow_class
    
    def get_flow(self, name: str, **kwargs) -> 'Flow':
        """
        Get a newly constructed Flow instance by registered name.
        
        Args:
            name: Registered name of the flow
            **kwargs: Arguments to pass to Flow constructor
            
        Returns:
            Instance of the registered Flow class
            
        Example:
            camera = get_flow("camera", camera_id=1)
            detector = get_flow("yolo_detector", confidence_threshold=0.8)
        """
        _ensure_plugins_loaded()
        if name not in self._flows:
            available = list(self._flows.keys())
            raise ValueError(f"Flow '{name}' not registered. Available: {available}")
        
        flow_info = self._flows[name]
        return flow_info.flow_class(**kwargs)
    
    def get_flow_class(self, name: str) -> Type['Flow']:
        """Get the registered Flow class itself (without constructing it)."""
        _ensure_plugins_loaded()
        if name not in self._flows:
            available = list(self._flows.keys())
            raise ValueError(f"Flow '{name}' not registered. Available: {available}")
        return self._flows[name].flow_class
    
    def list_flows(self, category: Optional[str] = None) -> Dict[str, FlowInfo]:
        """List all registered flows, optionally filtered by category."""
        _ensure_plugins_loaded()
        if category is None:
            return dict(self._flows)
        else:
            return dict(self._categories.get(category, {}))
    
    def list_categories(self) -> Dict[str, int]:
        """List all categories and count of flows in each."""
        return {cat: len(flows) for cat, flows in self._categories.items()}
    
    def find_flows(self, 
                   input_type: Optional[Type] = None,
                   output_type: Optional[Type] = None,
                   tags: Optional[list] = None) -> Dict[str, FlowInfo]:
        """Find flows by type signature or tags."""
        _ensure_plugins_loaded()
        results = {}
        
        for name, flow_info in self._flows.items():
            # Filter by input type
            if input_type and flow_info.input_type != input_type:
                continue
            # Filter by output type  
            if output_type and flow_info.output_type != output_type:
                continue
            # Filter by tags
            if tags and not any(tag in flow_info.tags for tag in tags):
                continue
                
            results[name] = flow_info
            
        return results
    
    def _extract_flow_types(self, flow_class: Type) -> tuple[Optional[Type], Optional[Type]]:
        """Extract input/output types from Flow[I, O] generic signature."""
        try:
            # Try to get generic type information
            if hasattr(flow_class, '__orig_bases__'):
                for base in flow_class.__orig_bases__:
                    if hasattr(base, '__origin__') and hasattr(base, '__args__'):
                        if len(base.__args__) >= 2:
                            return base.__args__[0], base.__args__[1]
        except Exception:
            logger.debug(
                "Failed to infer Flow generic types for %s",
                flow_class,
                exc_info=True,
            )
        return None, None


# Global registry instance
_global_flow_registry = FlowRegistry()

# Public API functions
def register_flow(name: str, 
                 category: str = "general",
                 description: str = "",
                 tags: Optional[list] = None) -> Callable[[Type[F]], Type[F]]:
    """Register a Flow component for easy discovery and substitution."""
    return _global_flow_registry.register(name, category, description, tags)

def get_flow(name: str, **kwargs) -> 'Flow':
    """Get a Flow instance by registered name."""
    return _global_flow_registry.get_flow(name, **kwargs)

def get_flow_class(name: str) -> Type['Flow']:
    """Get a Flow class by registered name."""
    return _global_flow_registry.get_flow_class(name)

def list_flows(category: Optional[str] = None) -> Dict[str, FlowInfo]:
    """List all registered flows, optionally filtered by category."""
    return _global_flow_registry.list_flows(category)

def find_flows(input_type: Optional[Type] = None,
               output_type: Optional[Type] = None, 
               tags: Optional[list] = None) -> Dict[str, FlowInfo]:
    """Find flows by type signature or tags."""
    return _global_flow_registry.find_flows(input_type, output_type, tags)

def get_flow_registry() -> FlowRegistry:
    """Get the global flow registry for advanced usage."""
    return _global_flow_registry
