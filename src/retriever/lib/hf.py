from typing import Any, Optional, Dict, List, Union
import logging
from retriever.flow import Flow, io

try:
    import torch
    import torch.nn as nn
    from transformers import AutoModel, AutoTokenizer, Pipeline, pipeline
except ImportError:
    torch = None
    nn = None
    AutoModel = None
    AutoTokenizer = None
    Pipeline = None
    pipeline = None



logger = logging.getLogger(__name__)

@io
class TransformerInput:
    """Standard input for HFFlow."""
    text: Optional[Union[str, List[str]]] = None
    image: Optional[Any] = None
    kwargs: Optional[Dict[str, Any]] = None

@io
class TransformerOutput:
    """Standard output for HFFlow."""
    result: Any


class HFFlow(Flow[TransformerInput, TransformerOutput]):
    """
    A flexible Flow wrapper for Hugging Face Pipelines and Models.
    
    It delegates `run(x)` to `pipe(x)` or `model(x)`.
    """
    def __init__(self, target_obj, task=None, device=None, **kwargs):
        self.target = target_obj
        self.task = task
        self.device = device
        self.kwargs = kwargs
        self.is_pipeline = False
        
    def reset(self):
        if torch is None:
            raise ImportError("PyTorch/Transformers not installed.")
            
        # If target is a factory function, instantiate it
        if callable(self.target) and not isinstance(self.target, (nn.Module, Pipeline)):
            self.target = self.target()
            
        if isinstance(self.target, Pipeline):
            self.is_pipeline = True
            logger.info(f"[HF] Wrapped Pipeline: {self.target.task}")
        elif isinstance(self.target, nn.Module):
            self.target.eval()
            if self.device:
                self.target.to(self.device)
            logger.info(f"[HF] Wrapped Module: {type(self.target).__name__}")
            
    def step(self, inputs: TransformerInput) -> TransformerOutput:
        # If inputs is TransformerInput, unpack it
        if hasattr(inputs, "text") and hasattr(inputs, "image"):
             # It's likely TransformerInput
             text = getattr(inputs, "text", None)
             image = getattr(inputs, "image", None)
             kwargs = getattr(inputs, "kwargs", {}) or {}
             
             output = None
             if self.is_pipeline:
                 if text and image:
                     output = self.target(text, images=image, **kwargs)
                 elif text:
                     output = self.target(text, **kwargs)
                 elif image:
                     output = self.target(image, **kwargs)
             else:
                 # Model mode with TransformerInput not fully implemented in this flexible wrapper
                 # Fallback to passing inputs directly if it's not our dataclass
                 pass
                 
             return TransformerOutput(result=output)

        if self.is_pipeline:
            # Fallback for raw inputs if somehow passed without typing enforcement
            return TransformerOutput(result=self.target(inputs, **self.kwargs))

        else:
            # Model inference
            # Assumption: Inputs is already a dict of tensors or compatible
            if isinstance(inputs, dict):
                # This path is unlikely to be hit if type checking is strict
                inputs_tensor = {k: v.to(self.device) if hasattr(v, 'to') else v for k, v in inputs.items()}
                with torch.no_grad():
                    return TransformerOutput(result=self.target(**inputs_tensor))
            else:
                 with torch.no_grad():
                    return TransformerOutput(result=self.target(inputs))

def from_hf(obj: Any, **kwargs) -> Flow:
    """
    Check if object is a Hugging Face Pipeline or Model and wrap it.
    """
    return HFFlow(obj, **kwargs)
