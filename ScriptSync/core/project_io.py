"""
Project / sidecar I/O — preserve script links when saving plain text files.
Sidecar: `roteiro.txt` → `roteiro.txt.ssync.json`
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

log = logging.getLogger("sscriptsync_v1")

SIDECAR_SUFFIX = ".ssync.json"
SCHEMA_VERSION = 1


def sidecar_path(text_path: str) -> str:
    return f"{text_path}{SIDECAR_SUFFIX}"


def save_sidecar(
    text_path: str,
    *,
    lines: list[dict[str, Any]],
    fmt: str = "txt",
    sync_mode: str = "linear",
    is_synced: bool = False,
) -> str:
    path = sidecar_path(text_path)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "format": fmt,
        "sync_mode": sync_mode,
        "is_synced": is_synced,
        "lines": lines,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("Sidecar saved: %s", path)
    return path


def load_sidecar(text_path: str) -> Optional[dict[str, Any]]:
    path = sidecar_path(text_path)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("schema_version") != SCHEMA_VERSION:
            log.warning("Sidecar schema mismatch: %s", path)
        log.info("Sidecar loaded: %s", path)
        return data
    except Exception as e:
        log.error("Failed to load sidecar %s: %s", path, e)
        return None


def merge_text_preserving_links(
    existing: list[dict[str, Any]], content: str
) -> list[dict[str, Any]]:
    """
    Update line text from plain content while keeping link/timecode metadata.
    Grows or shrinks line list as needed.
    """
    texts = content.split("\n")
    # Drop trailing empty line from editor join artifact
    while len(texts) > 1 and texts[-1] == "" and texts[-2] == "":
        texts.pop()

    result: list[dict[str, Any]] = []
    for i, text in enumerate(texts):
        if i < len(existing):
            row = dict(existing[i])
            row["text"] = text
            row["line_number"] = i + 1
        else:
            row = {"text": text, "line_number": i + 1}
        result.append(row)
    return result


def apply_sidecar_lines(
    parsed: list[dict[str, Any]], sidecar_lines: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Restore link metadata from sidecar onto freshly parsed lines."""
    if not sidecar_lines:
        return parsed

    by_index: dict[int, dict] = {}
    by_text: dict[str, dict] = {}
    for i, row in enumerate(sidecar_lines):
        by_index[i] = row
        t = (row.get("text") or "").strip()
        if t:
            by_text[t] = row

    merged: list[dict[str, Any]] = []
    for i, line in enumerate(parsed):
        src = by_index.get(i)
        if not src:
            t = (line.get("text") or "").strip()
            src = by_text.get(t)
        if not src:
            merged.append(dict(line))
            continue

        out = dict(line)
        for key in (
            "start_tc",
            "end_tc",
            "clip_name",
            "clip_start_frame",
            "clip_end_frame",
            "clip_index",
            "clip_uid",
            "track_index",
            "track_label",
            "links",
            "link_id",
            "link_color",
            "link_type",
            "marker_frame",
            "speaker",
            "synced",
        ):
            if src.get(key) is not None:
                out[key] = src[key]
        merged.append(out)
    return merged


def reconcile_clip_indices(
    lines: list[dict[str, Any]], clips: list[dict[str, Any]]
) -> None:
    """Remap clip_index using track + start_frame (stable across refreshes)."""
    if not clips:
        return

    from core.link_model import get_line_links, set_line_links, sync_flat_from_links

    def _uid(c: dict) -> str:
        if c.get("clip_uid"):
            return str(c["clip_uid"])
        tt = c.get("track_type") or ("audio" if c.get("is_audio") else "video")
        prefix = "a" if tt == "audio" else "v"
        return f"{prefix}{c.get('track_index', 1)}_{c['start_frame']}"

    by_uid = {_uid(c): i for i, c in enumerate(clips)}
    meta_by_uid = {_uid(c): c for c in clips}

    def _patch_link(link: dict) -> None:
        stored = link.get("clip_uid")
        if stored and stored in by_uid:
            link["clip_index"] = by_uid[stored]
            clip = meta_by_uid.get(stored)
            if clip:
                link.setdefault("track_index", clip.get("track_index", 1))
                link.setdefault("track_label", clip.get("track_label", "V1"))
            return
        tid = link.get("track_index", 1)
        sf = link.get("clip_start_frame")
        if sf is not None:
            tt = link.get("track_type") or (
                "audio" if str(link.get("track_label") or "").upper().startswith("A") else "video"
            )
            prefix = "a" if tt == "audio" else "v"
            key = f"{prefix}{tid}_{int(sf)}"
            if key in by_uid:
                link["clip_index"] = by_uid[key]
                link["clip_uid"] = key
                clip = meta_by_uid.get(key)
                if clip:
                    link["track_label"] = clip.get("track_label", f"V{tid}")

    for line in lines:
        links = get_line_links(line)
        if links:
            for link in links:
                if link.get("link_type") == "clip":
                    _patch_link(link)
            set_line_links(line, links)
            sync_flat_from_links(line)
            continue

        if line.get("link_type") != "clip":
            continue
        _patch_link(line)
        if line.get("clip_uid") and line["clip_uid"] in by_uid:
            line["clip_index"] = by_uid[line["clip_uid"]]


def rematch_links_to_timeline(
    lines: list[dict[str, Any]],
    clips: list[dict[str, Any]],
    fps: float = 24.0,
) -> int:
    """
    Re-attach manual links after clips moved/reordered on the timeline.
    Re-subdivides timecodes per link group (link_id). Returns lines updated.
    """
    if not clips:
        return 0

    from core.link_model import get_line_links, set_line_links, sync_flat_from_links
    from core.script_link import apply_clip_to_lines

    def _find_clip(link: dict) -> tuple[int, dict] | None:
        name = (link.get("clip_name") or "").strip().lower()
        tid = int(link.get("track_index") or 1)
        old_dur = None
        csf, cef = link.get("clip_start_frame"), link.get("clip_end_frame")
        if csf is not None and cef is not None:
            old_dur = max(1, int(cef) - int(csf))

        on_track = [
            (i, c)
            for i, c in enumerate(clips)
            if int(c.get("track_index") or 1) == tid
            and (c.get("name") or "").strip().lower() == name
        ]
        if len(on_track) == 1:
            return on_track[0]
        if len(on_track) > 1 and old_dur:
            on_track.sort(
                key=lambda x: abs(
                    max(1, int(x[1]["end_frame"]) - int(x[1]["start_frame"])) - old_dur
                )
            )
            return on_track[0]

        by_name = [
            (i, c)
            for i, c in enumerate(clips)
            if (c.get("name") or "").strip().lower() == name
        ]
        if len(by_name) == 1:
            return by_name[0]
        if len(by_name) > 1 and old_dur:
            by_name.sort(
                key=lambda x: abs(
                    max(1, int(x[1]["end_frame"]) - int(x[1]["start_frame"])) - old_dur
                )
            )
            return by_name[0]
        return None

    groups: dict[str, dict] = {}
    for i, line in enumerate(lines):
        for link in get_line_links(line):
            if link.get("link_type") != "clip":
                continue
            lid = link.get("link_id") or f"__solo_{i}_{link.get('clip_uid', '')}"
            if lid not in groups:
                groups[lid] = {
                    "indices": [],
                    "color": link.get("link_color"),
                    "sample": link,
                }
            if i not in groups[lid]["indices"]:
                groups[lid]["indices"].append(i)

    updated_lines = 0
    for lid, group in groups.items():
        hit = _find_clip(group["sample"])
        if not hit:
            continue
        _idx, clip = hit
        indices = sorted(group["indices"])

        for line_i in indices:
            kept = [
                lk
                for lk in get_line_links(lines[line_i])
                if lk.get("link_id") != lid
            ]
            if kept:
                set_line_links(lines[line_i], kept)
            else:
                lines[line_i].pop("links", None)
                for key in (
                    "start_tc",
                    "end_tc",
                    "clip_name",
                    "clip_start_frame",
                    "clip_end_frame",
                    "clip_index",
                    "clip_uid",
                    "track_index",
                    "track_label",
                    "link_id",
                    "link_color",
                    "link_type",
                ):
                    lines[line_i].pop(key, None)
                lines[line_i]["synced"] = False

        apply_clip_to_lines(
            lines,
            indices,
            clip,
            fps,
            link_color=group["color"],
            link_id=lid,
        )
        updated_lines += len(indices)

    return updated_lines
