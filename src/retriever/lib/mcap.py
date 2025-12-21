"""
MCAP Recording Support for Retriever.

MCAP is Foxglove's open-source container format for multimodal data.
It works with both Rerun (0.25+) and Foxglove Studio for visualization.

Usage:
    from retriever.lib.mcap import MCAPWriter, MCAPReader

    # Writing
    with MCAPWriter("session.mcap") as writer:
        for step in range(100):
            result = pipeline.step()
            writer.write_step(result, step)

    # Reading
    with MCAPReader("session.mcap") as reader:
        for step_result in reader:
            # replay logic

    # Visualization
    $ rerun session.mcap
    $ foxglove session.mcap
"""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

import numpy as np


def _ensure_mcap():
    """Lazy import mcap."""
    try:
        import mcap
        from mcap.reader import make_reader
        from mcap.writer import Writer

        return mcap, Writer, make_reader
    except ImportError:
        raise ImportError(
            "mcap not installed. Install with: pixi install (or pip install mcap)"
        ) from None


# =============================================================================
# Serialization Helpers
# =============================================================================


def _serialize_value(value: Any) -> bytes:
    """Serialize a Python value to bytes for MCAP storage."""
    if isinstance(value, np.ndarray):
        # Use numpy's native format for arrays
        import io

        buf = io.BytesIO()
        np.save(buf, value, allow_pickle=False)
        return buf.getvalue()
    elif is_dataclass(value) and not isinstance(value, type):
        # Serialize dataclass as JSON with special handling for numpy
        return _serialize_dataclass(value)
    elif isinstance(value, (dict, list, tuple, str, int, float, bool, type(None))):
        return json.dumps(value).encode("utf-8")
    else:
        # Fallback to pickle for complex types
        return pickle.dumps(value)


def _deserialize_value(data: bytes, schema_name: str) -> Any:
    """Deserialize bytes back to Python value."""
    if schema_name == "numpy.ndarray":
        import io

        buf = io.BytesIO(data)
        return np.load(buf, allow_pickle=False)
    elif schema_name == "retriever.dataclass":
        return _deserialize_dataclass(data)
    elif schema_name == "json":
        return json.loads(data.decode("utf-8"))
    elif schema_name.startswith("retriever.") or schema_name.startswith("foxglove."):
        # New JSON format - try to parse as JSON with numpy restoration
        try:
            obj = json.loads(data.decode("utf-8"))
            return _restore_numpy(obj)
        except json.JSONDecodeError:
            return pickle.loads(data)
    else:
        # Try JSON first, fallback to pickle
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return pickle.loads(data)


def _restore_numpy(obj: Any) -> Any:
    """Restore numpy arrays from JSON format."""
    if isinstance(obj, dict):
        if obj.get("__numpy__"):
            return np.array(obj["data"], dtype=obj["dtype"])
        return {k: _restore_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_restore_numpy(x) for x in obj]
    return obj


def _serialize_dataclass(obj: Any) -> bytes:
    """Serialize a dataclass, handling numpy arrays specially."""

    def convert(v):
        if isinstance(v, np.ndarray):
            return {"__numpy__": True, "data": v.tolist(), "dtype": str(v.dtype)}
        elif is_dataclass(v) and not isinstance(v, type):
            return {k: convert(getattr(v, k)) for k in v.__dataclass_fields__}
        elif isinstance(v, (list, tuple)):
            return [convert(x) for x in v]
        elif isinstance(v, dict):
            return {k: convert(val) for k, val in v.items()}
        return v

    result = {"__class__": type(obj).__name__}
    for field in obj.__dataclass_fields__:
        result[field] = convert(getattr(obj, field))

    return json.dumps(result).encode("utf-8")


def _deserialize_dataclass(data: bytes) -> Dict[str, Any]:
    """Deserialize dataclass JSON, restoring numpy arrays."""
    obj = json.loads(data.decode("utf-8"))

    def restore(v):
        if isinstance(v, dict):
            if v.get("__numpy__"):
                return np.array(v["data"], dtype=v["dtype"])
            return {k: restore(val) for k, val in v.items()}
        elif isinstance(v, list):
            return [restore(x) for x in v]
        return v

    return restore(obj)


# =============================================================================
# MCAP Writer
# =============================================================================


class MCAPWriter:
    """
    Write pipeline step results to MCAP format.

    Usage:
        with MCAPWriter("session.mcap") as writer:
            for step in range(100):
                result = pipeline.step()
                writer.write_step(result, step)
    """

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self._file = None
        self._writer = None
        self._channels: Dict[str, int] = {}
        self._schemas: Dict[str, int] = {}

    def __enter__(self) -> "MCAPWriter":
        _, Writer, _ = _ensure_mcap()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "wb")
        self._writer = Writer(self._file)
        self._writer.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._writer:
            self._writer.finish()
        if self._file:
            self._file.close()

    def _get_schema_id(self, schema_name: str, schema_data: bytes = b"") -> int:
        """Get or create schema ID."""
        if schema_name in self._schemas:
            return self._schemas[schema_name]

        # Use jsonschema encoding for Rerun/Foxglove compatibility
        schema_id = self._writer.register_schema(
            name=schema_name,
            encoding="jsonschema",
            data=schema_data,
        )
        self._schemas[schema_name] = schema_id
        return schema_id

    def _get_channel_id(
        self, topic: str, schema_name: str, schema_data: bytes = b""
    ) -> int:
        """Get or create channel ID."""
        if topic in self._channels:
            return self._channels[topic]

        schema_id = self._get_schema_id(schema_name, schema_data)
        channel_id = self._writer.register_channel(
            schema_id=schema_id,
            topic=topic,
            message_encoding="json",
        )
        self._channels[topic] = channel_id
        return channel_id

    def write_step(self, result: Any, step_idx: int) -> None:
        """
        Write a StepResult to MCAP.

        Args:
            result: StepResult from Pipeline.step()
            step_idx: Step index for sequencing
        """
        import base64

        # Get timestamp from result
        timestamp_ns = int((result.now or 0) * 1e9)

        # Write metadata about this step
        step_schema = json.dumps(
            {
                "type": "object",
                "properties": {
                    "step": {"type": "integer"},
                    "now": {"type": "number"},
                    "executed": {"type": "array", "items": {"type": "string"}},
                },
            }
        ).encode("utf-8")
        meta_topic = "/retriever/step"
        meta_channel = self._get_channel_id(meta_topic, "retriever.Step", step_schema)
        meta_data = json.dumps(
            {
                "step": step_idx,
                "now": result.now,
                "executed": result.executed,
            }
        ).encode("utf-8")
        self._writer.add_message(
            channel_id=meta_channel,
            log_time=timestamp_ns,
            data=meta_data,
            publish_time=timestamp_ns,
        )

        # Write each flow's outputs
        for flow_name, output in (result.outputs or {}).items():
            if output is None:
                continue

            # Look for image in dataclass fields
            if is_dataclass(output) and not isinstance(output, type):
                for field_name in output.__dataclass_fields__:
                    field_val = getattr(output, field_name)
                    if isinstance(field_val, np.ndarray) and field_val.ndim == 3:
                        # This is likely an image - use Foxglove RawImage
                        self._write_image(
                            flow_name, field_name, field_val, timestamp_ns
                        )

            # Always write the full output as JSON for replay
            topic = f"/retriever/flows/{flow_name}/output"
            obj_schema = json.dumps({"type": "object"}).encode("utf-8")
            channel_id = self._get_channel_id(
                topic, f"retriever.{flow_name}", obj_schema
            )

            # Convert output to JSON-safe format
            data = self._to_json(output)
            self._writer.add_message(
                channel_id=channel_id,
                log_time=timestamp_ns,
                data=data,
                publish_time=timestamp_ns,
            )

    def _write_image(
        self, flow_name: str, field_name: str, image: np.ndarray, timestamp_ns: int
    ) -> None:
        """Write an image using Foxglove RawImage schema."""
        import base64

        # Foxglove RawImage JSON schema
        raw_image_schema = json.dumps(
            {
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "object",
                        "properties": {
                            "sec": {"type": "integer"},
                            "nsec": {"type": "integer"},
                        },
                    },
                    "frame_id": {"type": "string"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "encoding": {"type": "string"},
                    "step": {"type": "integer"},
                    "data": {"type": "string", "contentEncoding": "base64"},
                },
            }
        ).encode("utf-8")

        topic = f"/camera/{flow_name}/{field_name}"
        channel_id = self._get_channel_id(topic, "foxglove.RawImage", raw_image_schema)

        h, w = image.shape[:2]
        if image.ndim == 3 and image.shape[2] == 3:
            encoding = "rgb8"
        elif image.ndim == 3 and image.shape[2] == 4:
            encoding = "rgba8"
        else:
            encoding = "mono8"

        # Base64 encode the image data
        data_b64 = base64.b64encode(image.tobytes()).decode("ascii")

        msg = {
            "timestamp": {
                "sec": timestamp_ns // 1_000_000_000,
                "nsec": timestamp_ns % 1_000_000_000,
            },
            "frame_id": f"{flow_name}_{field_name}",
            "width": w,
            "height": h,
            "encoding": encoding,
            "step": w * (3 if encoding == "rgb8" else 4 if encoding == "rgba8" else 1),
            "data": data_b64,
        }

        self._writer.add_message(
            channel_id=channel_id,
            log_time=timestamp_ns,
            data=json.dumps(msg).encode("utf-8"),
            publish_time=timestamp_ns,
        )

    def _to_json(self, obj: Any) -> bytes:
        """Convert object to JSON bytes, handling numpy and dataclasses."""

        def convert(v):
            if isinstance(v, np.ndarray):
                return {
                    "__numpy__": True,
                    "shape": list(v.shape),
                    "dtype": str(v.dtype),
                    "data": v.tolist(),
                }
            elif is_dataclass(v) and not isinstance(v, type):
                return {k: convert(getattr(v, k)) for k in v.__dataclass_fields__}
            elif isinstance(v, (list, tuple)):
                return [convert(x) for x in v]
            elif isinstance(v, dict):
                return {k: convert(val) for k, val in v.items()}
            return v

        return json.dumps(convert(obj)).encode("utf-8")


# =============================================================================
# MCAP Reader
# =============================================================================


class MCAPReader:
    """
    Read pipeline step results from MCAP format.

    Usage:
        with MCAPReader("session.mcap") as reader:
            for step_result in reader:
                # replay logic
    """

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self._file = None
        self._reader = None

    def __enter__(self) -> "MCAPReader":
        _, _, make_reader = _ensure_mcap()
        self._file = open(self.path, "rb")
        self._reader = make_reader(self._file)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            self._file.close()

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over step results."""
        # Group messages by step
        messages_by_step: Dict[int, Dict[str, Any]] = {}

        for schema, channel, message in self._reader.iter_messages():
            topic = channel.topic

            if topic == "/retriever/step":
                meta = json.loads(message.data.decode("utf-8"))
                step_idx = meta["step"]
                if step_idx not in messages_by_step:
                    messages_by_step[step_idx] = {
                        "step": step_idx,
                        "now": meta["now"],
                        "executed": meta["executed"],
                        "inputs": {},
                        "outputs": {},
                    }
            elif "/output" in topic:
                # Extract flow name from topic
                parts = topic.split("/")
                flow_name = parts[3]  # /retriever/flows/{flow_name}/output

                # Find step by timestamp
                for step_data in messages_by_step.values():
                    if abs((step_data["now"] or 0) * 1e9 - message.log_time) < 1e6:
                        step_data["outputs"][flow_name] = _deserialize_value(
                            message.data, schema.name
                        )
                        break
            elif "/input" in topic:
                parts = topic.split("/")
                flow_name = parts[3]

                for step_data in messages_by_step.values():
                    if abs((step_data["now"] or 0) * 1e9 - message.log_time) < 1e6:
                        step_data["inputs"][flow_name] = _deserialize_value(
                            message.data, schema.name
                        )
                        break

        # Yield in step order
        for step_idx in sorted(messages_by_step.keys()):
            yield messages_by_step[step_idx]

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all step results into a list."""
        return list(self)


# =============================================================================
# Convenience Functions
# =============================================================================


def view_in_rerun(path: Union[str, Path], spawn: bool = True) -> None:
    """
    Load MCAP file and visualize in Rerun.

    Since Rerun doesn't natively support our MCAP schema,
    this function reads the MCAP and logs to Rerun via SDK.

    Args:
        path: Path to .mcap file
        spawn: If True, spawn a new Rerun viewer
    """
    import base64

    try:
        import rerun as rr
    except ImportError:
        raise ImportError("rerun-sdk not installed. Run: pixi install") from None

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MCAP file not found: {path}")

    # Initialize Rerun
    rr.init(f"mcap_viewer_{path.stem}", spawn=spawn)

    # Read and log each message
    with MCAPReader(path) as reader:
        for schema, channel, message in reader._reader.iter_messages():
            topic = channel.topic
            timestamp_s = message.log_time / 1e9

            rr.set_time_seconds("recording", timestamp_s)

            # Handle image channels
            if channel.schema_id and schema.name == "foxglove.RawImage":
                try:
                    data = json.loads(message.data.decode("utf-8"))
                    img_data = base64.b64decode(data["data"])
                    w, h = data["width"], data["height"]
                    encoding = data.get("encoding", "rgb8")

                    if encoding == "rgb8":
                        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w, 3)
                    elif encoding == "rgba8":
                        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w, 4)
                    else:
                        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w)

                    rr.log(topic.replace("/", "_"), rr.Image(img))
                except Exception:
                    pass  # Skip malformed messages

            # Handle step metadata
            elif topic == "/retriever/step":
                try:
                    data = json.loads(message.data.decode("utf-8"))
                    rr.log(
                        "step", rr.TextLog(f"Step {data['step']}: {data['executed']}")
                    )
                except Exception:
                    pass

    print(f"[Rerun] Finished loading {path}")
