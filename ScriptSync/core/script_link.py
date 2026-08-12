"""
Manual script ↔ timeline linking (AVID ScriptSync style).
"""

from __future__ import annotations

import uuid
from typing import Any

from core.timecode import Timecode
from core.link_model import append_clip_link, get_line_links, set_line_links, sync_flat_from_links

# Distinct link colors (AVID-style markup)
LINK_COLORS = [
    "#4ade80",  # green
    "#facc15",  # yellow
    "#f472b6",  # pink
    "#60a5fa",  # blue
    "#c084fc",  # purple
    "#fb923c",  # orange
    "#2dd4bf",  # teal
]


def next_link_color(existing_lines: list[dict]) -> str:
    used = {l.get("link_color") for l in existing_lines if l.get("link_color")}
    for c in LINK_COLORS:
        if c not in used:
            return c
    return LINK_COLORS[len(existing_lines) % len(LINK_COLORS)]


def new_link_id() -> str:
    return f"link_{uuid.uuid4().hex[:8]}"


def apply_clip_to_lines(
    lines: list[dict],
    indices: list[int],
    clip: dict[str, Any],
    fps: float,
    link_color: str | None = None,
    link_id: str | None = None,
) -> str:
    """
    Bind selected line indices to a timeline clip.
    Subdivides clip duration evenly across selected lines (AVID block behaviour).
    Returns link_id used.
    """
    if not indices:
        return ""

    lid = link_id or new_link_id()
    color = link_color or next_link_color(lines)
    sorted_idx = sorted(i for i in indices if 0 <= i < len(lines))
    if not sorted_idx:
        return ""

    start_f = int(clip["start_frame"])
    end_f = int(clip["end_frame"])
    span = max(1, end_f - start_f)
    n = len(sorted_idx)
    per_line = span / n

    for i, idx in enumerate(sorted_idx):
        sf = int(start_f + i * per_line)
        ef = int(start_f + (i + 1) * per_line) if i < n - 1 else end_f
        link_entry = {
            "start_tc": Timecode.frames_to_timecode(sf, fps),
            "end_tc": Timecode.frames_to_timecode(ef, fps),
            "clip_name": clip.get("name", "Clip"),
            "clip_start_frame": start_f,
            "clip_end_frame": end_f,
            "clip_index": clip.get("clip_index"),
            "clip_uid": clip.get("clip_uid") or (
                f"{'a' if clip.get('is_audio') or clip.get('track_type') == 'audio' else 'v'}"
                f"{clip.get('track_index', 1)}_{start_f}"
            ),
            "track_index": clip.get("track_index", 1),
            "track_type": clip.get("track_type", "audio" if clip.get("is_audio") else "video"),
            "track_label": clip.get("track_label") or (
                f"A{clip.get('track_index', 1)}"
                if clip.get("is_audio") or clip.get("track_type") == "audio"
                else f"V{clip.get('track_index', 1)}"
            ),
            "link_id": lid,
            "link_color": color,
            "link_type": "clip",
            "marker_frame": None,
        }
        append_clip_link(lines[idx], link_entry)
    return lid


def apply_marker_to_lines(
    lines: list[dict],
    indices: list[int],
    frame: int,
    fps: float,
    marker_name: str = "ScriptSync",
    link_color: str | None = None,
    link_id: str | None = None,
) -> str:
    """Link lines to a timeline marker frame (no clip on V1)."""
    if not indices:
        return ""

    lid = link_id or new_link_id()
    color = link_color or next_link_color(lines)
    tc = Timecode.frames_to_timecode(frame, fps)
    sorted_idx = sorted(i for i in indices if 0 <= i < len(lines))

    for idx in sorted_idx:
        link_entry = {
            "start_tc": tc,
            "end_tc": tc,
            "clip_name": None,
            "clip_index": None,
            "clip_uid": None,
            "link_id": lid,
            "link_color": color,
            "link_type": "marker",
            "marker_frame": frame,
        }
        append_clip_link(lines[idx], link_entry)
    return lid


def unlink_lines(lines: list[dict], indices: list[int]) -> None:
    for idx in indices:
        if 0 <= idx < len(lines):
            lines[idx].pop("links", None)
            for key in _LINK_KEYS:
                lines[idx].pop(key, None)
            lines[idx]["synced"] = False
