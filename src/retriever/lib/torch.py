
import logging
import pickle
import codecs
from typing import Any, Type, Optional, Union, Dict

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
except ImportError:
    torch = None
    nn = None
    optim = None

from retriever.flow import Flow, io

logger = logging.getLogger(__name__)

# ============================================================================
# PART 1: INFERENCE WRAPPERS
# ============================================================================

@io
class TorchIO:
    inp: Any

class TorchModuleFlow(Flow[TorchIO, TorchIO]):
    """
    Top-level Flow class for wrapping PyTorch modules.
    Accepts a module instance, serializes it via pickle for transport.
    """
    def __init__(self, module: Optional["nn.Module"] = None, _pickled_module: Optional[str] = None):
        self._module_ref = module
        self._pickled_module = _pickled_module
        
        # If created via from_init_config (backend), we might only have string
        if module is None and _pickled_module is not None:
            self._module_ref = pickle.loads(codecs.decode(_pickled_module.encode(), "base64"))

    def init_config(self) -> dict:
        # Serialize the module to pass to backend
        if self._module_ref is None:
            return {}
            
        pickled = codecs.encode(pickle.dumps(self._module_ref), "base64").decode()
        return {"_pickled_module": pickled}

    def reset(self):
        if self._module_ref is None:
            raise RuntimeError("TorchModuleFlow has no module properly initialized.")
            
        # Auto-device selection
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
            
        self.model = self._module_ref.to(self.device)
        self.model.eval()
        
        logger.info(f"[{self.model.__class__.__name__}] Wrapper initialized on {self.device}")

    def step(self, input_data: TorchIO) -> Optional[TorchIO]:
        if input_data.inp is None:
            return None
        
        with torch.no_grad():
            x = input_data.inp
            if isinstance(x, torch.Tensor):
                x = x.to(self.device)
            out = self.model(x)
            
        return TorchIO(inp=out)


def from_torch(module: Union["nn.Module", Any]) -> Flow[TorchIO, TorchIO]:
    """
    Creates a Flow INSTANCE that wraps a PyTorch Module.
    """
    if torch is None:
        raise ImportError("PyTorch not installed. Cannot use from_torch.")
        
    return TorchModuleFlow(module=module)


# ============================================================================
# PART 2: SPLIT LEARNING HELPERS
# ============================================================================

class SplitOptimizer:
    """Helper for the SOURCE node in split learning."""
    def __init__(self, optimizer: "optim.Optimizer", verbose: bool = False):
        if torch is None: raise ImportError("torch is required")
        self.optimizer = optimizer
        self.saved_tensors: Dict[int, Any] = {}
        self.verbose = verbose

    def forward_pass(self, batch_index: int, output_tensor: "torch.Tensor") -> "torch.Tensor":
        self.saved_tensors[batch_index] = output_tensor
        return output_tensor.detach()

    def backward_pass(self, batch_index: int, grad_tensor: "torch.Tensor") -> bool:
        if batch_index not in self.saved_tensors:
            if self.verbose:
                logger.warning(f"Batch {batch_index} not found. Ignoring gradient.")
            return False
        saved_output = self.saved_tensors.pop(batch_index)
        if grad_tensor.device != saved_output.device:
            grad_tensor = grad_tensor.to(saved_output.device)
        self.optimizer.zero_grad()
        saved_output.backward(grad_tensor)
        self.optimizer.step()
        return True

class RemoteAutograd:
    """Helper for the COMPUTE node in split learning."""
    @staticmethod
    def attach(tensor: "torch.Tensor") -> "torch.Tensor":
        tensor.requires_grad_(True)
        return tensor

    @staticmethod
    def backward_and_return_grad(loss: "torch.Tensor", input_tensor: "torch.Tensor") -> "torch.Tensor":
        loss.backward()
        if input_tensor.grad is None:
            raise RuntimeError("No gradient computed for input tensor.")
        return input_tensor.grad
