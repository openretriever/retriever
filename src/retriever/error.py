"""
Retriever Error System.

Error codes are scoped by range:
- 1000-1999: Flow Layer (user API, declaration)
- 2000-2999: IR Layer (validation, transformation)
- 3000-3999: RT Layer (execution, scheduling)
- 4000-4999: Backend Layer (integration, deployment)
"""

from enum import IntEnum
from typing import Union, Optional, Dict


class ErrCode(IntEnum):
    """Hierarchical error codes indicating scope"""

    # ========================================================================
    # Flow Layer Errors (1000-1999)
    # ========================================================================

    # General Flow errors (1000-1099)
    FLOW_UNKNOWN = 1000
    FLOW_INVALID = 1001
    FLOW_NOT_IMPLEMENTED = 1002
    FLOW_CLOCK_INVALID = 1003
    FLOW_ADAPTER_INVALID = 1004
    FLOW_CONFIG_INVALID = 1005
    FLOW_INIT_FAILED = 1006
    FLOW_EXECUTION_FAILED = 1007

    # Type Errors (1100-1199)
    FLOW_TYPE_UNKNOWN = 1100
    FLOW_TYPE_INVALID = 1101
    FLOW_TYPE_MISSING = 1102
    FLOW_TYPE_NOT_COMPATIBLE = 1103

    # FlowIO Errors (1200-1299)
    FLOW_IO_UNKNOWN = 1200
    FLOW_IO_INVALID = 1201
    FLOW_IO_NOT_DATACLASS = 1202
    FLOW_IO_FIELD_NOT_FOUND = 1203
    FLOW_IO_INIT_UNEXPECTED = 1204
    FLOW_AMBIGUOUS_FIELD = 1205

    # PipelineGraph Errors (1300-1399)
    PIPELINE_GRAPH_NODE_NOT_FOUND = 1300
    PIPELINE_GRAPH_PORT_NOT_FOUND = 1301

    # PipelineBuilder Errors (1400-1499)
    PIPELINE_BUILDER_INACTIVE = 1400
    FLOW_CONNECTION_INVALID = 1401
    PIPELINE_BUILDER_NODE_NOT_FOUND = 1402

    # Service Errors (1500-1599)
    FLOW_SERVICE_UNKNOWN = 1500
    FLOW_SERVICE_INVALID = 1501
    FLOW_SERVICE_NOT_FOUND = 1502
    FLOW_SERVICE_TIMEOUT = 1503
    FLOW_SERVICE_ERROR = 1504
    FLOW_SERVICE_TYPE_MISMATCH = 1505
    FLOW_SERVICE_INVALID_SIGNATURE = 1506
    FLOW_SERVICE_SERIALIZATION_FAILED = 1507

    # ========================================================================
    # IR Layer Errors (2000-2999)
    # ========================================================================

    # General IR errors (2000-2099)
    IR_UNKNOWN = 2000

    # Validate Errors(2100-2199)
    IR_VAL_UNKNOWN = 2100
    IR_VAL_INVALID = 2101
    IR_VAL_TYPE_MISMATCH = 2102
    IR_VAL_PORT_NOT_FOUND = 2103
    IR_VAL_DUPLICATE_SERVICE = 2104
    IR_VAL_SERVICE_NOT_FOUND = 2105

    # ========================================================================
    # RT Layer Errors (3000-3999)
    # ========================================================================

    # General RT errors (3000-3099)
    RT_UNKNOWN = 3000
    RT_INVALID_YIELD = 3001
    RT_SCHEDULER_LAG = 3002

    # Serialization/Deserialization errors (3100-3199)
    RT_SERDE_UNKNOWN = 3100
    RT_SERDE_UNKNOWN_FORMAT = 3101
    RT_SERDE_SERIALIZE_FAILED = 3102
    RT_SERDE_DESERIALIZE_FAILED = 3103

    # ========================================================================
    # Backend Layer Errors (4000-4999)
    # ========================================================================

    # General Backend errors (4000-4099)
    BACKEND_UNKNOWN = 4000
    BACKEND_NOT_FOUND = 4001

    # Multiprocessing Backend errors (4100-4199)
    MP_UNKNOWN = 4100

    # Dora Backend errors (4200-4299)
    DORA_UNKNOWN = 4200
    DORA_EVENT_INVALID = 4201
    DORA_GET_INPUT_FAILED = 4202
    DORA_SET_OUTPUT_FAILED = 4203

    # ========================================================================
    # Hub Layer Errors (5000-5999)
    # ========================================================================

    # General Hub errors (5000-5099)
    HUB_UNKNOWN = 5000
    HUB_INVALID_REF = 5001
    HUB_MODULE_NOT_FOUND = 5002
    HUB_REPO_NOT_ACCESSIBLE = 5003
    HUB_NO_SEMVER_TAGS = 5004
    HUB_VERSION_NOT_FOUND = 5005
    HUB_FETCH_FAILED = 5006
    HUB_EXTRACT_FAILED = 5007
    HUB_PYPROJECT_MISSING = 5008
    HUB_PYPROJECT_INVALID = 5009
    HUB_MIN_VERSION_MISMATCH = 5010
    HUB_DEPENDENCY_MISSING = 5011
    HUB_DEPENDENCY_VERSION = 5012
    HUB_IMPORT_FAILED = 5013
    HUB_EXPORT_NOT_FOUND = 5014



# Built-in error messages
ERROR_MSGS: Dict[ErrCode, str] = {

    # Flow layer - General (1000-1099)
    ErrCode.FLOW_UNKNOWN: "Unknown Flow error",
    ErrCode.FLOW_INVALID: "Invalid Flow configuration or definition",
    ErrCode.FLOW_NOT_IMPLEMENTED: "Flow method not implemented",
    ErrCode.FLOW_CLOCK_INVALID: "Invalid clock configuration",
    ErrCode.FLOW_ADAPTER_INVALID: "Invalid adapter configuration",
    ErrCode.FLOW_CONFIG_INVALID: "Invalid flow configuration parameters",
    ErrCode.FLOW_INIT_FAILED: "Flow initialization failed",
    ErrCode.FLOW_EXECUTION_FAILED: "Flow execution failed",

    # Flow layer - Type Errors (1100-1199)
    ErrCode.FLOW_TYPE_UNKNOWN: "Unknown type error",
    ErrCode.FLOW_TYPE_INVALID: "Invalid type annotation",
    ErrCode.FLOW_TYPE_MISSING: "Type parameter missing from Flow[I, O]",
    ErrCode.FLOW_TYPE_NOT_COMPATIBLE: "Type not compatible with Flow requirements",

    # Flow layer - FlowIO (1200-1299)
    ErrCode.FLOW_IO_UNKNOWN: "Unknown FlowIO error",
    ErrCode.FLOW_IO_INVALID: "Invalid FlowIO configuration",
    ErrCode.FLOW_IO_NOT_DATACLASS: "@flow_io must be applied to a @dataclass",
    ErrCode.FLOW_IO_FIELD_NOT_FOUND: "Field not found in FlowIO type",
    ErrCode.FLOW_IO_INIT_UNEXPECTED: "Unexpected keyword argument in FlowIO __init__",
    ErrCode.FLOW_AMBIGUOUS_FIELD: "Ambiguous field access in composite input",

    # Flow layer - PipelineGraph (1300-1399)
    ErrCode.PIPELINE_GRAPH_NODE_NOT_FOUND: "Node not found in PipelineGraph",
    ErrCode.PIPELINE_GRAPH_PORT_NOT_FOUND: "Port not found in PipelineNode",

    # Flow layer - PipelineBuilder (1400-1499)
    ErrCode.PIPELINE_BUILDER_INACTIVE: "Operation requires active PipelineBuilder",
    ErrCode.FLOW_CONNECTION_INVALID: "Invalid flow connection parameters",
    ErrCode.PIPELINE_BUILDER_NODE_NOT_FOUND: "Node not found in PipelineBuilder",

    # Flow layer - Service (1500-1599)
    ErrCode.FLOW_SERVICE_UNKNOWN: "Unknown service error",
    ErrCode.FLOW_SERVICE_INVALID: "Invalid service declaration or reference",
    ErrCode.FLOW_SERVICE_NOT_FOUND: "Service not registered or no provider available",
    ErrCode.FLOW_SERVICE_TIMEOUT: "Service call timeout waiting for response",
    ErrCode.FLOW_SERVICE_ERROR: "Service handler raised exception",
    ErrCode.FLOW_SERVICE_TYPE_MISMATCH: "Request type does not match service signature",
    ErrCode.FLOW_SERVICE_INVALID_SIGNATURE: "Service method signature invalid",
    ErrCode.FLOW_SERVICE_SERIALIZATION_FAILED: "Failed to serialize/deserialize service payload",

    # IR layer - General (2000-2099)
    ErrCode.IR_UNKNOWN: "Unknown IR error",

    # IR layer - Validation (2100-2199)
    ErrCode.IR_VAL_UNKNOWN: "Unknown validation error",
    ErrCode.IR_VAL_INVALID: "Invalid IR structure",
    ErrCode.IR_VAL_TYPE_MISMATCH: "Type mismatch between connected ports",
    ErrCode.IR_VAL_PORT_NOT_FOUND: "Port not found during validation",
    ErrCode.IR_VAL_DUPLICATE_SERVICE: "Duplicate service provider",
    ErrCode.IR_VAL_SERVICE_NOT_FOUND: "Service not found during validation",

    # RT layer - General (3000-3099)
    ErrCode.RT_UNKNOWN: "Unknown runtime error",
    ErrCode.RT_INVALID_YIELD: "Flow.step() yielded unexpected value",
    ErrCode.RT_SCHEDULER_LAG: "Runtime scheduler cannot keep up with requested rate",

    # RT layer - Serialization/Deserialization (3100-3199)
    ErrCode.RT_SERDE_UNKNOWN: "Unknown serialization/deserialization error",
    ErrCode.RT_SERDE_UNKNOWN_FORMAT: "Unknown or unsupported data format for serialization",
    ErrCode.RT_SERDE_SERIALIZE_FAILED: "Failed to serialize value to Arrow format",
    ErrCode.RT_SERDE_DESERIALIZE_FAILED: "Failed to deserialize Arrow data to Python value",

    # Backend layer - General (4000-4099)
    ErrCode.BACKEND_UNKNOWN: "Unknown backend error",
    ErrCode.BACKEND_NOT_FOUND: "Backend not found",

    # Backend layer - Multiprocessing (4100-4199)
    ErrCode.MP_UNKNOWN: "Unknown multiprocessing backend error",

    # Backend layer - Dora (4200-4299)
    ErrCode.DORA_UNKNOWN: "Unknown dora backend error",
    ErrCode.DORA_EVENT_INVALID: "Invalid dora event structure or missing required fields",
    ErrCode.DORA_GET_INPUT_FAILED: "Failed to receive input from dora node",
    ErrCode.DORA_SET_OUTPUT_FAILED: "Failed to send output via dora node",

    # Hub layer (5000-5099)
    ErrCode.HUB_UNKNOWN: "Unknown hub error",
    ErrCode.HUB_INVALID_REF: "Invalid module reference format",
    ErrCode.HUB_MODULE_NOT_FOUND: "Module not found in hub index",
    ErrCode.HUB_REPO_NOT_ACCESSIBLE: "Module repository is not accessible",
    ErrCode.HUB_NO_SEMVER_TAGS: "No semver tags found in module repository",
    ErrCode.HUB_VERSION_NOT_FOUND: "Requested version not found",
    ErrCode.HUB_FETCH_FAILED: "Failed to download module",
    ErrCode.HUB_EXTRACT_FAILED: "Failed to extract module archive",
    ErrCode.HUB_PYPROJECT_MISSING: "Module is missing pyproject.toml",
    ErrCode.HUB_PYPROJECT_INVALID: "Module pyproject.toml is missing [tool.retriever.module]",
    ErrCode.HUB_MIN_VERSION_MISMATCH: "Module requires a newer version of retriever",
    ErrCode.HUB_DEPENDENCY_MISSING: "Required dependency is not installed",
    ErrCode.HUB_DEPENDENCY_VERSION: "Installed dependency version does not satisfy requirement",
    ErrCode.HUB_IMPORT_FAILED: "Failed to import module",
    ErrCode.HUB_EXPORT_NOT_FOUND: "Requested export not found in module",
}


class RetrieverError(Exception):
    """
    Base exception for all Retriever errors.

    Format: [ErrCode.name]: optional message
    """

    def __init__(
        self,
        code: Union[int, ErrCode],
        message: Optional[str] = None,
        data: Optional[Dict] = None
    ):
        """
        Create a Retriever error.

        Args:
            code: Your error code (error codes 1000 - 4999 are reserved)
            message: Optional readable error message (use built-in if None)
            data: Optional additional data dictionary associated with the error
        """
        if isinstance(code, int):
            try:
                code = ErrCode(code)
            except ValueError:
                pass  # Keep custom int code

        builtin = isinstance(code, ErrCode)
        code_name = code.name if builtin else str(code)
        default_msg = ERROR_MSGS.get(code, "Unknown error") if builtin else "Custom error"
        resolved_msg = message or default_msg

        self._code = code
        self._message = resolved_msg
        self._data = data or {}

        super().__init__(f"[{code_name}]: {resolved_msg}")

    @property
    def code(self) -> int:
        """Error code value indicating scope"""
        return int(self._code)

    @property
    def message(self) -> str:
        """A readable error message"""
        return self._message

    @property
    def data(self) -> Dict:
        """Additional error data"""
        return self._data

    @property
    def scope(self) -> str:
        """Error scope based on code range"""
        code_val = self.code
        if 1000 <= code_val < 2000:
            return "Flow"
        elif 2000 <= code_val < 3000:
            return "IR"
        elif 3000 <= code_val < 4000:
            return "RT"
        elif 4000 <= code_val < 5000:
            return "Backend"
        elif 5000 <= code_val < 6000:
            return "Hub"
        else:
            return "Custom"

    def with_data(self, **kwargs) -> 'RetrieverError':
        """Add additional data to the error"""
        self._data.update(kwargs)
        return self

    def __repr__(self) -> str:
        """String representation for debugging"""
        data_str = f", data={self._data}" if self._data else ""
        return f"RetrieverError(code={self.code}, message={self._message!r}{data_str})"

# ============================================================================
# Scoped Exception Classes
# ============================================================================

class FlowError(RetrieverError):
    """Flow layer errors (1000-1999)"""

    def __init__(self, code: Union[int, ErrCode], message: Optional[str] = None, **data):
        # Validate code is in flow range
        code_val = int(code)
        if not (1000 <= code_val < 2000):
            code = ErrCode.FLOW_UNKNOWN
        super().__init__(code, message, data)


class IRError(RetrieverError):
    """IR layer errors (2000-2999)"""

    def __init__(self, code: Union[int, ErrCode], message: Optional[str] = None, **data):
        code_val = int(code)
        if not (2000 <= code_val < 3000):
            code = ErrCode.IR_UNKNOWN
        super().__init__(code, message, data)


class RTError(RetrieverError):
    """RT layer errors (3000-3999)"""

    def __init__(self, code: Union[int, ErrCode], message: Optional[str] = None, **data):
        code_val = int(code)
        if not (3000 <= code_val < 4000):
            code = ErrCode.RT_UNKNOWN
        super().__init__(code, message, data)


class BackendError(RetrieverError):
    """Backend layer errors (4000-4999)"""

    def __init__(self, code: Union[int, ErrCode], message: Optional[str] = None, **data):
        code_val = int(code)
        if not (4000 <= code_val < 5000):
            code = ErrCode.BACKEND_UNKNOWN
        super().__init__(code, message, data)


class HubError(RetrieverError):
    """Hub layer errors (5000-5999)"""

    def __init__(self, code: Union[int, ErrCode], message: Optional[str] = None, **data):
        code_val = int(code)
        if not (5000 <= code_val < 6000):
            code = ErrCode.HUB_UNKNOWN
        super().__init__(code, message, data)


# ============================================================================
# Convenience Error Functions
# ============================================================================

def flow_error(code: ErrCode, message: Optional[str] = None, **data) -> FlowError:
    """Create a FlowError with optional data"""
    return FlowError(code, message, **data)


def ir_error(code: ErrCode, message: Optional[str] = None, **data) -> IRError:
    """Create an IRError with optional data"""
    return IRError(code, message, **data)


def rt_error(code: ErrCode, message: Optional[str] = None, **data) -> RTError:
    """Create a RTError with optional data"""
    return RTError(code, message, **data)


def backend_error(code: ErrCode, message: Optional[str] = None, **data) -> BackendError:
    """Create a BackendError with optional data"""
    return BackendError(code, message, **data)


def hub_error(code: ErrCode, message: Optional[str] = None, **data) -> HubError:
    """Create a HubError with optional data"""
    return HubError(code, message, **data)
