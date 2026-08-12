"""
Multi-take link model — one line ↔ many clips, one clip ↔ many lines.
"""

from __future__ import annotations

from typing import Any

_LINK_KEYS = (
    "link_id",
    "link_type",
    "link_color",
    "link_label",
    "clip_uid",
    "clip_index",
    "clip_name",
    "clip_start_frame",
    "clip_end_frame",
    "track_index",
    "track_label",
    "start_tc",
    "end_tc",
    "marker_frame",
)


def get_line_links(line: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all takes/links on a line (migrates legacy flat fields)."""
    raw = line.get("links")
    if isinstance(raw, list) and raw:
        return [dict(x) for x in raw if isinstance(x, dict)]

    if line.get("link_id") or line.get("start_tc") or line.get("timecode"):
        entry: dict[str, Any] = {}
        for key in _LINK_KEYS:
            if line.get(key) is not None:
                entry[key] = line[key]
        if line.get("timecode") and not entry.get("start_tc"):
            entry["start_tc"] = line["timecode"]
        if entry:
            entry.setdefault("link_type", "clip" if entry.get("clip_uid") else "marker")
            return [entry]
    return []


def set_line_links(line: dict[str, Any], links: list[dict[str, Any]]) -> None:
    line["links"] = links
    sync_flat_from_links(line)


def sync_flat_from_links(line: dict[str, Any]) -> None:
    """Mirror primary link into flat keys for UI / legacy code."""
    links = get_line_links(line)
    for key in _LINK_KEYS:
        line.pop(key, None)
    line.pop("timecode", None)

    if not links:
        line["synced"] = False
        return

    primary = links[-1]
    for key in _LINK_KEYS:
        if primary.get(key) is not None:
            line[key] = primary[key]

    line["synced"] = True


def line_has_links(line: dict[str, Any]) -> bool:
    return bool(get_line_links(line))


def clip_uids_on_line(line: dict[str, Any]) -> set[str]:
    uids: set[str] = set()
    for lk in get_line_links(line):
        uid = lk.get("clip_uid")
        if uid:
            uids.add(str(uid))
    return uids


def append_clip_link(line: dict[str, Any], link: dict[str, Any]) -> None:
    links = get_line_links(line)
    uid = link.get("clip_uid")
    links = [lk for lk in links if lk.get("clip_uid") != uid]
    links.append(link)
    set_line_links(line, links)
