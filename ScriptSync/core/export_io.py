"""
Export script + links — plain text, enriched sidecar, simple EDL of marks.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from core.link_model import get_line_links
from core.project_io import SCHEMA_VERSION


def export_edl_marks(
    lines: list[dict[str, Any]],
    *,
    title: str = "SScriptSync",
    fps: float = 24.0,
) -> str:
    """Simple tabular EDL-style list of linked marks (not a full CMX3600 parser)."""
    rows = [
        f"TITLE: {title}",
        f"* SScriptSync marks export @ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"* FPS reference: {fps}",
        "FCM: NON-DROP FRAME",
        "",
        "Event  In           Out          Reel     Comment",
    ]
    event = 1
    for i, line in enumerate(lines):
        text = (line.get("text") or "").strip().replace("\t", " ")
        note = (line.get("note") or "").strip()
        links = get_line_links(line)
        if not links and line.get("start_tc"):
            links = [line]
        for link in links:
            tc_in = link.get("start_tc") or line.get("start_tc")
            if not tc_in:
                continue
            tc_out = link.get("end_tc") or tc_in
            reel = (link.get("clip_name") or link.get("track_label") or "AX")[:8]
            comment = text[:48]
            if note:
                comment = f"{comment} | {note[:24]}"
            rows.append(
                f"{event:03d}  {tc_in}  {tc_out}  C  {reel:<8}  L{i + 1}: {comment}"
            )
            event += 1
    return "\n".join(rows) + "\n"


def export_enriched_sidecar(
    text_path: str,
    *,
    lines: list[dict[str, Any]],
    fmt: str = "txt",
    sync_mode: str = "linear",
    is_synced: bool = False,
    project_name: str = "",
    timeline_name: str = "",
) -> str:
    """Save sidecar with export metadata and per-line notes."""
    path = f"{text_path}.ssync.json"
    linked = sum(1 for ln in lines if get_line_links(ln))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "format": fmt,
        "sync_mode": sync_mode,
        "is_synced": is_synced,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project_name": project_name,
        "timeline_name": timeline_name,
        "stats": {
            "line_count": len(lines),
            "linked_lines": linked,
            "notes": sum(1 for ln in lines if (ln.get("note") or "").strip()),
        },
        "lines": lines,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def export_bundle(
    base_path: str,
    *,
    script_text: str,
    lines: list[dict[str, Any]],
    fmt: str = "txt",
    sync_mode: str = "linear",
    is_synced: bool = False,
    fps: float = 24.0,
    project_name: str = "",
    timeline_name: str = "",
) -> dict[str, str]:
    """
    Write roteiro.txt, roteiro.txt.ssync.json (enriched), roteiro.edl.
    Returns dict of kind → path.
    """
    root, ext = os.path.splitext(base_path)
    if not ext:
        base_path = base_path + ".txt"
        root, ext = os.path.splitext(base_path)

    txt_path = base_path
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(script_text)

    sidecar_path = export_enriched_sidecar(
        txt_path,
        lines=lines,
        fmt=fmt,
        sync_mode=sync_mode,
        is_synced=is_synced,
        project_name=project_name,
        timeline_name=timeline_name,
    )
    edl_path = root + ".edl"
    with open(edl_path, "w", encoding="utf-8") as f:
        f.write(
            export_edl_marks(
                lines,
                title=os.path.basename(root),
                fps=fps,
            )
        )

    return {"txt": txt_path, "sidecar": sidecar_path, "edl": edl_path}
