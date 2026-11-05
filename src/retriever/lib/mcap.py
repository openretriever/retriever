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
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np

_LOSSLESS_SCHEMA = "retriever.recording.json-v1"
_LOSSLESS_CODEC = "retriever.mcap.json-v1"


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
    """Serialize supported recording values without losing array shape or bytes."""
    if isinstance(value, np.ndarray):
        import io

        buf = io.BytesIO()
        np.save(buf, value, allow_pickle=False)
        return buf.getvalue()
    if is_dataclass(value) and not isinstance(value, type):
        return _serialize_dataclass(value)
    from retriever.recording import _encode_recorded_value

    return json.dumps(_encode_recorded_value(value, lossless=True)).encode("utf-8")


def _deserialize_value(data: bytes, schema_name: str) -> Any:
    """Deserialize bytes back to Python value."""
    if schema_name == _LOSSLESS_SCHEMA:
        return _decode_lossless_payload(json.loads(data.decode("utf-8")))
    if schema_name == "numpy.ndarray":
        import io

        buf = io.BytesIO(data)
        return np.load(buf, allow_pickle=False)
    elif schema_name == "retriever.dataclass":
        return _restore_numpy(json.loads(data.decode("utf-8")))
    elif schema_name == "json":
        return json.loads(data.decode("utf-8"))
    elif schema_name.startswith("retriever.") or schema_name.startswith("foxglove."):
        # New JSON format - try to parse as JSON with numpy restoration
        try:
            obj = json.loads(data.decode("utf-8"))
            return _restore_numpy(obj)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError(
                f"Legacy pickled MCAP payload for schema `{schema_name}` is no longer supported. "
                "Re-record this artifact with the current Retriever build."
            ) from exc
    else:
        # Stable session artifacts should be JSON-compatible.
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError(
                f"Unsupported non-JSON MCAP payload for schema `{schema_name}`. "
                "Re-record this artifact with the current Retriever build."
            ) from exc


def _restore_numpy(obj: Any) -> Any:
    """Restore legacy array markers without interpreting ordinary bytes/tuple keys."""
    if isinstance(obj, dict):
        if obj.get("__numpy__"):
            from retriever.recording import _restore_recorded_value

            return _restore_recorded_value(obj)
        return {key: _restore_numpy(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_restore_numpy(value) for value in obj]
    return obj


def _decode_lossless_payload(envelope: Any) -> Any:
    from retriever.recording import _restore_recorded_value

    if not isinstance(envelope, dict) or envelope.get("codec") != _LOSSLESS_CODEC:
        raise ValueError("Unsupported lossless MCAP recording codec.")
    return _restore_recorded_value(envelope["value"], lossless=True)


def _serialize_dataclass(obj: Any) -> bytes:
    """Serialize typed values with an explicit lossless codec envelope."""
    from retriever.recording import _encode_recorded_value

    envelope = {
        "codec": _LOSSLESS_CODEC,
        "value": _encode_recorded_value(obj, lossless=True),
    }
    return json.dumps(envelope).encode("utf-8")


def _deserialize_dataclass(data: bytes) -> Dict[str, Any]:
    """Read versioned values or legacy dataclass JSON with array markers."""
    obj = json.loads(data.decode("utf-8"))
    if (
        isinstance(obj, dict)
        and obj.get("codec") == _LOSSLESS_CODEC
        and set(obj) == {"codec", "value"}
    ):
        return _decode_lossless_payload(obj)
    return _restore_numpy(obj)


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
                topic, _LOSSLESS_SCHEMA, obj_schema
            )

            # Convert output to JSON-safe format
            data = self._to_json(output)
            self._writer.add_message(
                channel_id=channel_id,
                log_time=timestamp_ns,
                data=data,
                publish_time=timestamp_ns,
            )

    def write_stream_spec(self, spec: Any, *, timestamp_ns: int = 0) -> None:
        """Write one shared stream-spec manifest message."""
        topic = f"/retriever/streams/{spec.node_id}/spec"
        schema_data = json.dumps(
            {
                "type": "object",
                "properties": {
                    "stream_id": {"type": "string"},
                    "node_id": {"type": "string"},
                    "io_kind": {"type": "string"},
                    "clock_domain": {"type": "string"},
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "version": {"type": "string"},
                            "encoding": {"type": "string"},
                        },
                    },
                },
            }
        ).encode("utf-8")
        channel_id = self._get_channel_id(topic, "retriever.StreamSpec", schema_data)
        payload = json.dumps(
            {
                "stream_id": str(spec.stream_id),
                "node_id": spec.node_id,
                "io_kind": spec.io_kind,
                "clock_domain": spec.clock_domain.name,
                "schema": {
                    "name": spec.schema.name,
                    "version": spec.schema.version,
                    "encoding": spec.schema.encoding,
                },
            }
        ).encode("utf-8")
        self._writer.add_message(
            channel_id=channel_id,
            log_time=timestamp_ns,
            data=payload,
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
        """Encode arrays, bytes and typed values with the shared recording codec."""
        from retriever.recording import _encode_recorded_value

        try:
            encoded = _encode_recorded_value(obj, lossless=True)
        except TypeError as exc:
            raise TypeError(
                f"Unsupported value for stable MCAP recording: {type(obj)!r}. "
                "Use @io dataclasses, numpy arrays, bytes, or JSON-like values."
            ) from exc
        return json.dumps({"codec": _LOSSLESS_CODEC, "value": encoded}).encode("utf-8")


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

    def read_node_stream(self, node_id: str) -> List[Tuple[float, Any]]:
        """
        Read time-series stream for a specific node.

        Args:
            node_id: Node ID to read (e.g. "camera")

        Returns:
            List of (timestamp, value) tuples
        """
        topic = f"/retriever/flows/{node_id}/output"
        buffer: List[Tuple[float, Any]] = []

        # Filter by topic
        for schema, channel, message in self._reader.iter_messages(topics=[topic]):
            val = _deserialize_value(message.data, schema.name)
            ts = message.log_time / 1e9
            buffer.append((ts, val))

        return buffer


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

            if hasattr(rr, "set_time"):
                rr.set_time("recording", timestamp=timestamp_s)
            else:
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
