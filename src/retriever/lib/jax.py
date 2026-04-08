
import logging
import pickle
import codecs
import time
from typing import Any, Type, Optional, Union, Dict, Tuple, Callable

try:
    import jax
    import jax.numpy as jnp
    import flax.linen as nn
    from flax.training import train_state
    import optax
except ImportError:
    jax = None
    jnp = None
    nn = None
    train_state = None
    optax = None

from retriever.flow import Flow, io

logger = logging.getLogger(__name__)

# ============================================================================
# PART 1: INFERENCE WRAPPERS
# ============================================================================

@io
class JaxIO:
    inp: Any # jax.numpy.ndarray (Auto zero-copy if backend supports it)

class JaxFlow(Flow[JaxIO, JaxIO]):
    """
    Top-level Flow class for wrapping Flax modules.
    
    Since Flax is functional, this class manages the state (params) internally.
    It accepts a module class/instance and an initialization input shape/data.
    """
    def __init__(
        self, 
        module: Optional["nn.Module"] = None, 
        init_req: Optional[Any] = None,
        _pickled_module_def: Optional[str] = None,
        _pickled_init_req: Optional[str] = None,
        _pickled_params: Optional[str] = None
    ):
        self._module_def = module
        self._init_req = init_req
        self._pickled_module_def = _pickled_module_def
        self._pickled_init_req = _pickled_init_req
        self._pickled_params = _pickled_params
        
        self.params = None
        self.module = None
        
        # If created via from_init_config (backend), deserialize
        if module is None and _pickled_module_def is not None:
            self._module_def = pickle.loads(codecs.decode(_pickled_module_def.encode(), "base64"))
            
        if _pickled_init_req is not None:
            self._init_req = pickle.loads(codecs.decode(_pickled_init_req.encode(), "base64"))
            
        if _pickled_params is not None:
             self.params = pickle.loads(codecs.decode(_pickled_params.encode(), "base64"))

    def init_config(self) -> dict:
        # Serialize the module definition and params to pass to backend
        config = {}
        if self._module_def is not None:
            pickled_def = codecs.encode(pickle.dumps(self._module_def), "base64").decode()
            config["_pickled_module_def"] = pickled_def
            
        if self._init_req is not None:
             pickled_req = codecs.encode(pickle.dumps(self._init_req), "base64").decode()
             config["_pickled_init_req"] = pickled_req
            
        if self.params is not None:
            pickled_params = codecs.encode(pickle.dumps(self.params), "base64").decode()
            config["_pickled_params"] = pickled_params
            
        return config

    def init(self):
        if self._module_def is None:
            raise RuntimeError("JaxFlow has no module definition.")
            
        # Instantiate the module (Flax modules are usually dataclasses/frozen)
        self.module = self._module_def
        
        # Initialize params if not already present (and we have input to infer shape)
        if self.params is None and self._init_req is not None:
            rng = jax.random.PRNGKey(int(time.time()))
            self.params = self.module.init(rng, self._init_req)
            logger.info(f"[{self.module.__class__.__name__}] Wrapper initialized params with shape inference.")
        elif self.params is not None:
            logger.info(f"[{self.module.__class__.__name__}] Wrapper initialized with existing params.")
        else:
             logger.warning(f"[{self.module.__class__.__name__}] Wrapper initialized WITHOUT params (waiting for sync or runtime init).")

        # JIT compile the apply function for performance
        self._apply_fn = jax.jit(self.module.apply)

    def run(self, input_data: JaxIO) -> Optional[JaxIO]:
        if input_data.inp is None:
            return None
        
        if self.params is None:
            raise RuntimeError("Cannot run JaxFlow: Params not initialized.")
            
        # Run inference
        # Input is expected to be a JAX array or compatible numpy array
        out = self._apply_fn(self.params, input_data.inp)
        
        return JaxIO(inp=out)


def from_jax(module: Any, sample_input: Any = None, **kwargs) -> Flow[JaxIO, JaxIO]:
    """
    Creates a Flow INSTANCE that wraps a Flax Module or compatible JAX object.
    """
    if jax is None:
        raise ImportError("JAX/Flax not installed. Cannot use from_jax.")
        
    return JaxFlow(module=module, init_req=sample_input, **kwargs)

# Alias for backward compatibility
from_flax = from_jax


# ============================================================================
# PART 2: SPLIT LEARNING HELPERS
# ============================================================================

class JaxSplitOptimizer:
    """Helper for the SOURCE node in split learning (handles update step)."""
    def __init__(self, optimizer: "optax.GradientTransformation", params: Any):
        if jax is None: raise ImportError("JAX is required")
        
        self.tx = optimizer
        self.opt_state = self.tx.init(params)
        self.params = params
        
        # We need a way to store "vjp" functions or similar if we were doing
        # single-process split, but for async multi-process, we just receive gradients.
        # Since Flax is functional, we update params explicitly.
        
        @jax.jit
        def apply_updates(params, updates, opt_state):
            updates, new_opt_state = self.tx.update(updates, opt_state, params)
            new_params = optax.apply_updates(params, updates)
            return new_params, new_opt_state
            
        self._apply_updates = apply_updates

    def step(self, grad_tree: Any) -> Any:
        # Update params using the received gradients
        self.params, self.opt_state = self._apply_updates(self.params, grad_tree, self.opt_state)
        return self.params


class JaxRemoteGrad:
    """
    Helper for the COMPUTE node in split learning.
    Since JAX is functional, we can't just "attach" gradients like PyTorch.
    We need to define a function that takes hidden_state -> loss
    and differentiate it with respect to hidden_state.
    """
    
    @staticmethod
    def value_and_grad_wrt_input(
        apply_fn: Callable, 
        params: Any, 
        hidden_state: Any, 
        target: Any
    ) -> Tuple[Any, Any]:
        """
        Computes loss and gradient with respect to the INPUT (hidden_state),
        not the params (since params are fixed on this node usually, or updated separately).
        
        If we are doing split learning where Compute node ALSO has params (part B),
        we might need grad wrt params AND input. 
        """
        
        def loss_fn(h):
            pred = apply_fn(params, h)
            # Simple MSE for demonstration, or user provides loss fn
            return jnp.mean((pred - target) ** 2)
            
        grad_fn = jax.value_and_grad(loss_fn)
        loss, input_grad = grad_fn(hidden_state)
        return loss, input_grad
