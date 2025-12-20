"""
Serialization and Deserialization for Dora Backend.

Provides Apache Arrow-based serialization with metadata.
"""

import json
import pickle
import dataclasses
import importlib
import warnings
from typing import Any, Dict, Tuple

import pyarrow as pa
import numpy as np

import logging
logger = logging.getLogger(__name__)

# Optional libraries for Zero-Copy support
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from dora.cuda import torch_to_ipc_buffer, ipc_buffer_to_ipc_handle, cudabuffer_to_torch
    HAS_DORA_CUDA = True
except ImportError:
    HAS_DORA_CUDA = False


# ============================================================================
# Serialization
# ============================================================================

def serialize_arrow(value: Any) -> Tuple[pa.Array, Dict[str, Any]]:
    """
    Serialize Python value to Arrow array with metadata.

    Handles:
    - Primitives (bool, int, float, str, bytes)
    - Collections (list, tuple, dict)
    - Numpy arrays
    - Fallback to pickle for complex types

    Args:
        value: Python value to serialize

    Returns:
        (pyarrow.Array, metadata_dict)

    Metadata format:
        {
            "_type": "null" | "bool" | "int" | "float" | "str" | "bytes" |
                     "list" | "tuple" | "dict" | "ndarray" | "pickle",
            "_shape": [...],  # For ndarray only
            "_original": "ClassName"  # For pickle only
        }
    """
    # Handle None
    if value is None:
        return pa.array([None], type=pa.null()), {"_type": "null"}

    # Handle primitive scalar types
    if isinstance(value, bool):
        return pa.array([value], type=pa.bool_()), {"_type": "bool"}

    elif isinstance(value, int):
        return pa.array([value]), {"_type": "int"}

    elif isinstance(value, float):
        return pa.array([value]), {"_type": "float"}

    elif isinstance(value, str):
        return pa.array([value]), {"_type": "str"}

    elif isinstance(value, bytes):
        return pa.array([value], type=pa.binary()), {"_type": "bytes"}

    # Handle lists
    elif isinstance(value, list):
        try:
            return pa.array(value), {"_type": "list"}
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            pass # Fallback to pickle

    # Handle tuples
    elif isinstance(value, tuple):
        try:
            return pa.array(list(value)), {"_type": "tuple"}
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            pass # Fallback to pickle

    # Handle dicts
    elif isinstance(value, dict):
        try:
            json_str = json.dumps(value)
            return pa.array([json_str]), {"_type": "dict"}
        except (TypeError, ValueError):
            pass # Fallback to pickle

    # Handle dataclass instances (including @flow_io dataclasses)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        try:
            payload = dataclasses.asdict(value)
            wrapped = {
                "__dataclass__": {
                    "module": value.__class__.__module__,
                    "name": value.__class__.__name__,
                },
                "data": payload,
            }
            json_str = json.dumps(wrapped)
            return pa.array([json_str]), {"_type": "dataclass"}
        except (TypeError, ValueError):
            pass  # Fallback to pickle

    # Handle numpy arrays
    elif isinstance(value, np.ndarray):
        # Prefer a stable cross-language format: bytes + dtype + shape.
        # This is friendlier for future Rust-native nodes.
        if value.dtype == object:
            # Object arrays are not portable; fall back to pickle.
            pass
        else:
            arr = np.ascontiguousarray(value)
            data = arr.tobytes(order="C")
            return pa.array([data], type=pa.binary()), {
                "_type": "ndarray",
                "_shape": list(arr.shape),
                "_dtype": str(arr.dtype),
            }

    # Handle PyArrow Array (Pass-through for Zero Copy)
    elif isinstance(value, pa.Array):
        return value, {"_type": "arrow_array"}

    # Handle PyArrow Buffer (Wrap in Array)
    elif isinstance(value, pa.Buffer):
        # We must wrap buffer in an array to send via dora
        # We treat it as a binary array of length 1 containing this buffer
        return pa.array([value], type=pa.binary()), {"_type": "arrow_buffer"}

    # Handle PyTorch Tensors (Native Zero-Copy Integration)
    elif HAS_TORCH and isinstance(value, torch.Tensor):
        # -- CUDA Support --
        if value.device.type == "cuda" and HAS_DORA_CUDA:
            try:
                # Get IPC Handle (Zero Copy GPU->GPU)
                ipc_buffer, meta = torch_to_ipc_buffer(value)
                handle_bytes = ipc_buffer_to_ipc_handle(ipc_buffer)
                
                # Send handle as binary
                return pa.array([handle_bytes], type=pa.binary()), {
                    "_type": "torch_tensor",
                    "_device": "cuda",
                    "_meta": json.dumps(meta) # Encode metadata (dtype, shape, strides)
                }
            except Exception as e:
                logger.warning(f"CUDA IPC failed, falling back: {e}")
                # Fallthrough to CPU transfer
                value = value.cpu()
        
        # -- CPU Support --
        # Convert to Numpy (Zero Copy View) -> Arrow
        # We flatten because Arrow arrays are 1D lists of values. 
        # We reconstruct shape on receive.
        if value.device.type != "cpu":
             value = value.cpu()
            
        np_view = value.detach().numpy().reshape(-1) # Flat view
        
        # Create Arrow Array from Numpy (Zero Copy if types match)
        # Note: pa.array(np_array) is generally zero-copy for numerical types
        arrow_arr = pa.array(np_view)
        
        return arrow_arr, {
            "_type": "torch_tensor",
            "_device": "cpu",
            "_dtype": str(value.dtype),
            "_shape": list(value.shape)
        }

    # Fallback: pickle for complex types
    logger.debug(f"Using pickle for type: {type(value)}")
    pickled = pickle.dumps(value)
    return pa.array([pickled], type=pa.binary()), {
        "_type": "pickle",
        "_original": type(value).__name__,
        "_module": type(value).__module__,
    }


# ============================================================================
# Deserialization
# ============================================================================

def deserialize_arrow(arrow_array: pa.Array, metadata: Dict[str, Any]) -> Any:
    """
    Deserialize Arrow array to Python value using metadata.

    Args:
        arrow_array: Arrow array from dora event
        metadata: Metadata dict describing serialization format

    Returns:
        Deserialized Python value
    """
    type_info = metadata.get("_type", "unknown")

    # Handle null
    if type_info == "null":
        return None

    # Handle primitives
    elif type_info in ("bool", "int", "float", "str", "bytes"):
        return arrow_array[0].as_py()

    # Handle lists
    elif type_info == "list":
        return arrow_array.to_pylist()

    # Handle tuples
    elif type_info == "tuple":
        lst = arrow_array.to_pylist()
        return tuple(lst)

    # Handle dicts
    elif type_info == "dict":
        json_str = arrow_array[0].as_py()
        return json.loads(json_str)
    
    # Handle numpy arrays
    elif type_info == "ndarray":
        shape = tuple(metadata.get("_shape", ()))
        dtype = metadata.get("_dtype")

        # New encoding: binary bytes + dtype
        if dtype is not None:
            raw = arrow_array[0].as_py()
            arr = np.frombuffer(raw, dtype=np.dtype(dtype))
            return arr.reshape(shape)

        # Backward-compatible encoding: numeric Arrow array
        flat = arrow_array.to_numpy()
        return flat.reshape(shape)

    # Handle dataclasses encoded as json
    elif type_info == "dataclass":
        json_str = arrow_array[0].as_py()
        wrapped = json.loads(json_str)
        info = wrapped.get("__dataclass__", {})
        data = wrapped.get("data", {})

        mod_name = info.get("module")
        cls_name = info.get("name")

        if isinstance(mod_name, str) and isinstance(cls_name, str):
            try:
                mod = importlib.import_module(mod_name)
                cls = getattr(mod, cls_name)
                if dataclasses.is_dataclass(cls):
                    return cls(**data)
            except Exception:
                # Fall through to returning the dict payload
                pass

        return data

    # Handle pass-through Arrow Array
    elif type_info == "arrow_array":
        return arrow_array

    # Handle pass-through Arrow Buffer
    elif type_info == "arrow_buffer":
        # Extract the single buffer from the binary array
        return arrow_array[0].as_buffer()

    # Handle PyTorch Tensors
    elif type_info == "torch_tensor":
        if not HAS_TORCH:
            raise ImportError("Received torch_tensor but torch is not installed.")
            
        device_type = metadata.get("_device", "cpu")
        
        if device_type == "cuda" and HAS_DORA_CUDA and torch.cuda.is_available():
            # CUDA IPC Reconstruct
            meta = json.loads(metadata.get("_meta", "{}"))
            handle_bytes = arrow_array[0].as_py() # Extract bytes
            
            ctx = pa.cuda.context()
            ipc_buf = ctx.open_ipc_buffer(handle_bytes)
            return cudabuffer_to_torch(ipc_buf, meta)
            
        else:
            # CPU Reconstruct (or CUDA fallback to CPU if local has no GPU)
            # Arrow -> Numpy -> Torch
            # .to_numpy() on Arrow array is zero-copy in many cases
            np_arr = arrow_array.to_numpy()
            
            # Reshape
            shape_list = metadata.get("_shape", [])
            if shape_list:
                np_arr = np_arr.reshape(shape_list)
                
            # Convert to Torch (Share memory)
            # Note: Arrow arrays are read-only. Torch might complain if we try to mutate.
            # We copy if we need to ensure writeability, but for input execution it's usually fine.
            # safe path:
                # Create a tensor from numpy.
                # Suppress warning about non-writable tensors (we want zero-copy read-only).
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning, message="The given NumPy array is not writable")
                    try:
                        tensor = torch.from_numpy(np_arr)
                    except ValueError:
                        # Fallback for very strict numpy versions
                         tensor = torch.from_numpy(np_arr.copy())

                # If buffer is not writable, we must copy
                tensor = torch.from_numpy(np_arr.copy())
                
            # If original was CUDA but we are on CPU/No-Dora-Cuda, we just keep it on CPU.
            return tensor

    # Handle pickled objects
    elif type_info == "pickle":
        pickled = arrow_array[0].as_py()
        return pickle.loads(pickled)

    # Unknown type - raise error
    else:
        from retriever.error import rt_error, ErrCode
        raise rt_error(
            ErrCode.RT_SERDE_UNKNOWN_FORMAT,
            f"Unknown metadata type: {type_info}"
        )
