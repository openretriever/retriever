"""
Serialization and Deserialization for Dora Backend.

Provides Apache Arrow-based serialization with metadata.
"""

import json
import pickle
import dataclasses
import importlib
from typing import Any, Dict, Tuple

import pyarrow as pa
import numpy as np

import logging
logger = logging.getLogger(__name__)


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
