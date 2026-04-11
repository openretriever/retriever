"""Tarball download and extraction."""

from __future__ import annotations

import io
import logging
import os
import tarfile
import tempfile
from pathlib import Path

from retriever.error import ErrCode, HubError
from retriever.hub._http import fetch_bytes

logger = logging.getLogger(__name__)


def _is_path_safe(member: tarfile.TarInfo, dest: Path) -> bool:
    """Check that a tar member doesn't escape the destination directory."""
    target = (dest / member.name).resolve()
    return str(target).startswith(str(dest.resolve()))


def download_and_extract(
    owner: str, repo: str, commit_sha: str, dest_dir: Path
) -> Path:
    """Download a tarball for a commit and extract to dest_dir.

    Returns path to the extracted module root (directory containing pyproject.toml).
    """
    url = f"https://github.com/{owner}/{repo}/archive/{commit_sha}.tar.gz"
    logger.debug("Downloading %s", url)

    data = fetch_bytes(url)

    # Extract to a temp dir first, then rename atomically
    parent = dest_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(dir=parent, prefix=f"{commit_sha[:12]}.tmp."))
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            # Safety check all members
            for member in tf.getmembers():
                if not _is_path_safe(member, tmp_dir):
                    raise HubError(
                        ErrCode.HUB_EXTRACT_FAILED,
                        f"Tar member '{member.name}' would escape destination directory.",
                    )
                if member.issym() or member.islnk():
                    link_target = (tmp_dir / member.linkname).resolve()
                    if not str(link_target).startswith(str(tmp_dir.resolve())):
                        raise HubError(
                            ErrCode.HUB_EXTRACT_FAILED,
                            f"Tar member '{member.name}' has a symlink escaping destination.",
                        )
            tf.extractall(tmp_dir)

        # GitHub tarballs have a top-level dir like {repo}-{sha}/
        children = list(tmp_dir.iterdir())
        if len(children) == 1 and children[0].is_dir():
            inner = children[0]
        else:
            inner = tmp_dir

        # Move contents to dest_dir
        if dest_dir.exists():
            # Another process may have raced us; use existing
            return dest_dir

        os.rename(str(inner), str(dest_dir))
    except HubError:
        raise
    except Exception as exc:
        raise HubError(
            ErrCode.HUB_EXTRACT_FAILED,
            f"Failed to extract module archive: {exc}",
        ) from exc
    finally:
        # Clean up temp dir if it still exists
        if tmp_dir.exists():
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return dest_dir
