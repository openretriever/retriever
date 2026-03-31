"""Module reference string parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from retriever.error import ErrCode, HubError

_REF_PATTERN = re.compile(
    r"^(?P<org>[a-zA-Z0-9_-]+)"
    r"/(?P<name>[a-zA-Z0-9_-]+)"
    r"(?::(?P<attr>[a-zA-Z_]\w*))?"
    r"(?:@(?P<version>.+))?$"
)


@dataclass(frozen=True)
class ModuleRef:
    """Parsed module reference."""

    org: str
    name: str
    attribute: Optional[str] = None
    version: Optional[str] = None


def parse_ref(ref: str) -> ModuleRef:
    """Parse a module reference string.

    Format: {org}/{name}[:{attribute}][@{version}]

    Examples:
        "company-abc/lidar-slam"
        "company-abc/lidar-slam:LidarSlamFlow"
        "company-abc/lidar-slam:LidarSlamFlow@0.1.0"
    """
    m = _REF_PATTERN.match(ref)
    if m is None:
        raise HubError(
            ErrCode.HUB_INVALID_REF,
            f"Invalid module reference '{ref}'. "
            "Expected format: '{org}/{name}[:{attribute}][@{version}]'",
        )
    return ModuleRef(
        org=m.group("org"),
        name=m.group("name"),
        attribute=m.group("attr"),
        version=m.group("version"),
    )
