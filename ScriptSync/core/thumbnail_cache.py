"""
Clip frame thumbnails via Resolve Project.ExportCurrentFrameAsStill().
Cached under ~/.sscriptsync_v1/thumbnails/
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Optional

from core.timecode import Timecode

log = logging.getLogger("sscriptsync_v1")

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".sscriptsync_v1", "thumbnails")


def cache_path(timeline_id: str, key: str | int) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in timeline_id)[:64]
    key_safe = str(key).replace("/", "_").replace("\\", "_")[:80]
    return os.path.join(CACHE_DIR, f"{safe}_{key_safe}.jpg")


def file_to_data_uri(path: str, mime: str = "image/jpeg") -> str:
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def clip_cache_key(clip: dict[str, Any]) -> str:
    uid = clip.get("clip_uid")
    if uid:
        return str(uid)
    return f"v{clip.get('track_index', 1)}_{clip.get('start_frame', 0)}"


class ThumbnailService:
    """Fetch and cache still frames for timeline clips."""

    def __init__(self, bridge):
        self._bridge = bridge
        os.makedirs(CACHE_DIR, exist_ok=True)

    def get_thumbnail_uri(self, clip: dict[str, Any]) -> Optional[str]:
        timeline = self._bridge.timeline
        project = self._bridge.project
        if not timeline or not project:
            return None

        start = int(clip.get("start_frame", 0))
        end = int(clip.get("end_frame", start + 1))
        frame = start + max(0, (end - start) // 2)

        try:
            timeline_id = timeline.GetUniqueId() or "timeline"
        except Exception:
            timeline_id = "timeline"

        cache_key = clip.get("clip_uid") or f"v{clip.get('track_index', 1)}_{frame}"
        path = cache_path(timeline_id, cache_key)
        if os.path.isfile(path) and os.path.getsize(path) > 100:
            return file_to_data_uri(path)

        saved_tc: Optional[str] = None
        try:
            saved_tc = timeline.GetCurrentTimecode()
        except Exception:
            pass

        tc = Timecode.frames_to_timecode(frame, self._bridge.fps)
        try:
            timeline.SetCurrentTimecode(tc)
            time.sleep(0.1)
            ok = project.ExportCurrentFrameAsStill(path)
            if not ok or not os.path.isfile(path):
                # Fallback: Color page thumbnail API (may work when clip is active)
                thumb = self._try_color_thumbnail(path)
                if not thumb:
                    return None
            return file_to_data_uri(path)
        except Exception as e:
            log.debug("Thumbnail export failed for frame %s: %s", frame, e)
            return None
        finally:
            if saved_tc:
                try:
                    timeline.SetCurrentTimecode(saved_tc)
                except Exception:
                    pass

    def _try_color_thumbnail(self, save_path: str) -> bool:
        timeline = self._bridge.timeline
        if not timeline:
            return False
        try:
            data = timeline.GetCurrentClipThumbnailImage()
            if not data or not data.get("data"):
                return False
            raw = base64.b64decode(data["data"])
            with open(save_path, "wb") as f:
                f.write(raw)
            return os.path.getsize(save_path) > 100
        except Exception:
            return False
