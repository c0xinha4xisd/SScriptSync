"""
Session persistence — save/load script sync state per project + timeline.
Stored under ~/.sscriptsync_v1/projects/
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("sscriptsync_v1")

SCHEMA_VERSION = 1
DATA_ROOT = os.path.join(os.path.expanduser("~"), ".sscriptsync_v1", "projects")


def _safe_name(value: str) -> str:
    value = (value or "untitled").strip()
    value = re.sub(r'[<>:"/\\|?*]', "_", value)
    value = re.sub(r"\s+", "_", value)
    return value[:120] or "untitled"


def session_path(project_name: str, timeline_name: str) -> str:
    key = f"{_safe_name(project_name)}__{_safe_name(timeline_name)}.json"
    return os.path.join(DATA_ROOT, key)


def save_session(
    project_name: str,
    timeline_name: str,
    *,
    lines: list[dict[str, Any]],
    import_path: str = "",
    fmt: str = "auto",
    is_synced: bool = False,
    sync_mode: str = "linear",
) -> str:
    os.makedirs(DATA_ROOT, exist_ok=True)
    path = session_path(project_name, timeline_name)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "project": project_name,
        "timeline": timeline_name,
        "import_path": import_path,
        "format": fmt,
        "is_synced": is_synced,
        "sync_mode": sync_mode,
        "lines": lines,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("Session saved: %s", path)
    return path


def load_session(
    project_name: str, timeline_name: str
) -> Optional[dict[str, Any]]:
    path = session_path(project_name, timeline_name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("schema_version") != SCHEMA_VERSION:
            log.warning("Session schema mismatch: %s", path)
        log.info("Session loaded: %s", path)
        return data
    except Exception as e:
        log.error("Failed to load session %s: %s", path, e)
        return None


def list_sessions() -> list[dict[str, str]]:
    if not os.path.isdir(DATA_ROOT):
        return []
    out = []
    for name in os.listdir(DATA_ROOT):
        if name.endswith(".json"):
            out.append({"file": name, "path": os.path.join(DATA_ROOT, name)})
    return out
