"""
Pipeline Registry System for Complete Workflow Discovery

Allows registration and discovery of complete pipelines for common robotics tasks.
Enables PyTorch-style component access like: get_pipeline("perception")
"""

from typing import Dict, Type, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
import inspect

from .flow import Flow

# Use Any for now since Pipeline is complex - we'll define our own base later
P = TypeVar('P')

@dataclass 
class PipelineInfo:
    """Information about a registered pipeline."""
    pipeline_class: Type
    name: str
    category: str = "general"
    description: str = ""
    tags: list = None
    input_type: Optional[Type] = None
    output_type: Optional[Type] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class PipelineRegistry:
    """Global registry for Retriever pipelines."""
    
    def __init__(self):
        self._pipelines: Dict[str, PipelineInfo] = {}
        self._pipeline_to_name: Dict[Type, str] = {}
    
    def register(self, 
                 pipeline_class: Type, 
                 name: str,
                 category: str = "general",
                 description: str = "",
                 tags: Optional[list] = None,
                 input_type: Optional[Type] = None,
                 output_type: Optional[Type] = None) -> Type:
        """
        Register a pipeline for use in Retriever.
        
        Args:
            pipeline_class: The pipeline class to register
            name: Name for the pipeline
            category: Category like "robotics", "vision", "planning"
            description: Human-readable description
            tags: Optional tags for discovery
            input_type: Optional input type hint
            output_type: Optional output type hint
            
        Returns:
            The registered pipeline class (for use as decorator)
            
        Example:
            @register_pipeline("perception", category="robotics", 
                             description="Complete perception stack",
                             tags=["vision", "detection"])
            class PerceptionPipeline(Pipeline):
                def __init__(self):
                    camera = get_flow("camera")
                    detector = get_flow("yolo_detector") 
                    super().__init__([camera, detector])
        """
        # Check for conflicts
        if name in self._pipelines:
            existing = self._pipelines[name]
            if existing.pipeline_class != pipeline_class:
                raise ValueError(f"Pipeline name '{name}' already registered for {existing.pipeline_class}")
            return pipeline_class  # Already registered
            
        # Try to extract type information from class if available
        if input_type is None or output_type is None:
            # Look for type hints in __init__ or other methods
            # This is a placeholder - could be enhanced with actual type inspection
            pass
            
        # Register the pipeline
        pipeline_info = PipelineInfo(
            pipeline_class=pipeline_class,
            name=name,
            category=category,
            description=description,
            tags=tags or [],
            input_type=input_type,
            output_type=output_type
        )
        
        self._pipelines[name] = pipeline_info
        self._pipeline_to_name[pipeline_class] = name
        
        # Add metadata to the class
        pipeline_class._retriever_pipeline_name = name
        pipeline_class._retriever_registered = True
        
        return pipeline_class
    
    def get_pipeline(self, name: str, **kwargs) -> Any:
        """Get a pipeline instance by name.
        
        Args:
            name: The registered pipeline name
            **kwargs: Arguments to pass to pipeline constructor
            
        Returns:
            Instantiated pipeline
            
        Raises:
            ValueError: If pipeline is not found
        """
        info = self._pipelines.get(name)
        if info is None:
            available = list(self._pipelines.keys())
            raise ValueError(f"Pipeline '{name}' not found. Available pipelines: {available}")
        
        return info.pipeline_class(**kwargs)
    
    def get_pipeline_class(self, name: str) -> Type:
        """Get pipeline class by name without instantiating."""
        info = self._pipelines.get(name)
        if info is None:
            available = list(self._pipelines.keys())
            raise ValueError(f"Pipeline '{name}' not found. Available pipelines: {available}")
        return info.pipeline_class
    
    def list_pipelines(self, category: Optional[str] = None) -> Dict[str, PipelineInfo]:
        """List all registered pipelines, optionally filtered by category."""
        if category is None:
            return self._pipelines.copy()
        return {name: info for name, info in self._pipelines.items() 
                if info.category == category}
    
    def find_pipelines(self, 
                      input_type: Optional[Type] = None,
                      output_type: Optional[Type] = None,
                      category: Optional[str] = None,
                      tags: Optional[list] = None) -> Dict[str, PipelineInfo]:
        """Find pipelines matching specific criteria."""
        results = {}
        
        for name, info in self._pipelines.items():
            # Check input type filter
            if input_type and info.input_type and not issubclass(input_type, info.input_type):
                continue
                
            # Check output type filter  
            if output_type and info.output_type and not issubclass(info.output_type, output_type):
                continue
                
            # Check category filter
            if category and info.category != category:
                continue
                
            # Check tags filter
            if tags and not all(tag in info.tags for tag in tags):
                continue
                
            results[name] = info
        
        return results
    
    def get_pipeline_info(self, name_or_class) -> Optional[PipelineInfo]:
        """Get pipeline information by name or class."""
        if isinstance(name_or_class, str):
            return self._pipelines.get(name_or_class)
        elif isinstance(name_or_class, type):
            name = self._pipeline_to_name.get(name_or_class)
            return self._pipelines.get(name) if name else None
        else:
            return None


# Global registry instance
_global_pipeline_registry = PipelineRegistry()

def register_pipeline(name: str, 
                     category: str = "general",
                     description: str = "",
                     tags: Optional[list] = None,
                     input_type: Optional[Type] = None,
                     output_type: Optional[Type] = None):
    """
    Register a pipeline with the global registry.
    
    Args:
        name: Pipeline name
        category: Category for organization  
        description: Human-readable description
        tags: Optional tags for discovery
        input_type: Optional input type hint
        output_type: Optional output type hint
        
    Returns:
        Decorator function
        
    Example:
        @register_pipeline("perception", category="robotics",
                          description="Complete perception pipeline", 
                          tags=["vision", "detection"])
        class PerceptionPipeline(Pipeline):
            def __init__(self):
                camera = get_flow("camera")
                detector = get_flow("yolo_detector")
                super().__init__([camera, detector])
    """
    def decorator(cls):
        return _global_pipeline_registry.register(
            cls, name, category, description, tags, input_type, output_type)
    return decorator

def get_pipeline(name: str, **kwargs) -> Any:
    """Get a pipeline instance by name - PyTorch-style access."""
    return _global_pipeline_registry.get_pipeline(name, **kwargs)

def get_pipeline_class(name: str) -> Type:
    """Get pipeline class by name without instantiating."""
    return _global_pipeline_registry.get_pipeline_class(name)

def list_pipelines(category: Optional[str] = None) -> Dict[str, PipelineInfo]:
    """List all registered pipelines, optionally filtered by category."""
    return _global_pipeline_registry.list_pipelines(category)

def find_pipelines(input_type: Optional[Type] = None,
                  output_type: Optional[Type] = None, 
                  category: Optional[str] = None,
                  tags: Optional[list] = None) -> Dict[str, PipelineInfo]:
    """Find pipelines matching specific criteria."""
    return _global_pipeline_registry.find_pipelines(input_type, output_type, category, tags)

def get_global_pipeline_registry() -> PipelineRegistry:
    """Get the global pipeline registry instance."""
    return _global_pipeline_registry