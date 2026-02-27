"""
Lightweight Dora runtime telemetry writer.

The telemetry writer is intentionally best-effort and fully opt-in. It should
never raise into runtime execution paths.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional


CONTRACT_VERSION = "dora_telemetry.v1"

_WRITE_LOCK = threading.Lock()


def _resolve_telemetry_path() -> Optional[Path]:
    raw = str(
        os.getenv("RETRIEVER_DORA_TELEMETRY_JSONL")
        or os.getenv("RETRIEVER_DORA_TAP_JSONL")
        or ""
    ).strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _payload_to_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return {}
    return {"value": str(payload)}


class DoraTelemetryWriter:
    """Append-only JSONL telemetry writer for Dora runtime events."""

    def __init__(self) -> None:
        self._path = _resolve_telemetry_path()

    @property
    def enabled(self) -> bool:
        return self._path is not None

    def emit(self, *, event: str, node_id: str, payload: Any = None) -> bool:
        path = self._path
        if path is None:
            return False
        row = {
            "timestamp": time.time(),
            "contract_version": CONTRACT_VERSION,
            "event": str(event),
            "run_id": str(os.getenv("RETRIEVER_RUN_ID") or ""),
            "pipeline_id": str(os.getenv("RETRIEVER_PIPELINE_ID") or ""),
            "node_id": str(node_id),
            "payload": _payload_to_dict(payload),
        }
        try:
            line = json.dumps(row, sort_keys=True, default=str)
            with _WRITE_LOCK:
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.write("\n")
            return True
        except Exception:
            return False
