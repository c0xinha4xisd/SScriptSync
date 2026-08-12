"""
Text format parsers (TXT, SRT, CSV).
Ported from textParser.js — uses core.timecode only.
"""

from __future__ import annotations

import re
from typing import Any

from core.timecode import Timecode


class TextParser:
    """Parse scripts/subtitles and associate timecodes with lines."""

    _SRT_PATTERN = re.compile(
        r"^\d+\s*\n\s*\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}",
        re.MULTILINE,
    )

    @staticmethod
    def detect_format(content: str) -> str:
        if TextParser._SRT_PATTERN.search(content):
            return "srt"
        if re.search(r"^([^,\n]+,){2,}", content, re.MULTILINE):
            return "csv"
        return "txt"

    @staticmethod
    def parse_txt(content: str) -> list[dict[str, Any]]:
        lines = []
        for i, raw in enumerate(content.split("\n"), start=1):
            text = raw.strip()
            if text:
                lines.append({"text": text, "line_number": i, "timecode": None})
        return lines

    @staticmethod
    def parse_srt(content: str, fps: float = 24.0) -> list[dict[str, Any]]:
        blocks = content.strip().split("\n\n")
        subtitles: list[dict[str, Any]] = []

        for index, block in enumerate(blocks):
            lines = block.strip().split("\n")
            if len(lines) < 2:
                continue

            try:
                sequence = int(lines[0])
            except ValueError:
                sequence = index + 1

            timestamp = lines[1]
            text = "\n".join(lines[2:]).strip()
            tc_data = Timecode.parse_srt_timestamp(timestamp, fps)

            entry: dict[str, Any] = {
                "sequence": sequence,
                "text": text,
                "line_number": index + 1,
            }
            if tc_data:
                entry["start_tc"] = tc_data["start"]
                entry["end_tc"] = tc_data["end"]
            subtitles.append(entry)

        return subtitles

    @staticmethod
    def parse_csv(content: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        lines = content.split("\n")

        start_index = 0
        if lines and (
            "timecode" in lines[0].lower() or "speaker" in lines[0].lower()
        ):
            start_index = 1

        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            parts = line.split(",")
            if len(parts) < 2:
                continue

            timecode = parts[0].strip()
            speaker = parts[1].strip() if len(parts) > 2 else None
            text = parts[1].strip() if len(parts) == 2 else ",".join(parts[2:]).strip()

            entry: dict[str, Any] = {
                "text": text,
                "line_number": i + 1,
                "speaker": speaker,
            }
            if Timecode.is_valid_timecode(timecode):
                entry["timecode"] = timecode
                entry["start_tc"] = timecode
            rows.append(entry)

        return rows

    @staticmethod
    def parse(content: str, fmt: str = "auto", fps: float = 24.0) -> list[dict[str, Any]]:
        detected = TextParser.detect_format(content) if fmt == "auto" else fmt

        if detected == "srt":
            return TextParser.parse_srt(content, fps)
        if detected == "csv":
            return TextParser.parse_csv(content)
        return TextParser.parse_txt(content)

    @staticmethod
    def to_text(data: list[dict[str, Any]], fmt: str = "txt") -> str:
        if fmt == "srt":
            blocks = []
            for i, item in enumerate(data, start=1):
                start = item.get("start_tc", "00:00:00:00")
                end = item.get("end_tc", start)
                blocks.append(f"{i}\n{start} --> {end}\n{item.get('text', '')}\n")
            return "\n".join(blocks)

        if fmt == "csv":
            out = []
            for item in data:
                tc = item.get("timecode") or item.get("start_tc") or ""
                speaker = item.get("speaker")
                prefix = f"{speaker}," if speaker else ""
                out.append(f"{tc},{prefix}{item.get('text', '')}")
            return "\n".join(out)

        return "\n".join(item.get("text", "") for item in data)

    @staticmethod
    def extract_dialogue(content: str) -> list[dict[str, Any]]:
        dialogues: list[dict[str, Any]] = []
        current_speaker = None

        for index, raw in enumerate(content.split("\n"), start=1):
            trimmed = raw.strip()
            if (
                trimmed
                and trimmed == trimmed.upper()
                and len(trimmed) < 50
                and "." not in trimmed
            ):
                current_speaker = trimmed
            elif trimmed and current_speaker:
                dialogues.append(
                    {
                        "speaker": current_speaker,
                        "text": trimmed,
                        "line_number": index,
                        "timecode": None,
                    }
                )

        return dialogues

    @staticmethod
    def is_manually_linked(line: dict[str, Any]) -> bool:
        from core.link_model import get_line_links

        return bool(get_line_links(line))

    _SCENE_RE = re.compile(
        r"^(INT[\.\s/]|EXT[\.\s/]|INT/EXT|I/E[\.\s]|CENA\s+\d|SCENE\s+\d)",
        re.IGNORECASE,
    )

    @staticmethod
    def parse_sync_options(raw: dict[str, Any] | None) -> dict[str, bool]:
        opts = raw or {}
        return {
            "skip_caps": bool(opts.get("skip_caps", True)),
            "skip_parens": bool(opts.get("skip_parens", True)),
            "skip_scene_headers": bool(opts.get("skip_scene_headers", True)),
        }

    @staticmethod
    def should_sync_line(text: str, sync_opts: dict[str, bool] | None = None) -> bool:
        """Filter screenplay lines for auto-sync (CAPS names, parens, scene headers)."""
        opts = TextParser.parse_sync_options(sync_opts)
        t = (text or "").strip()
        if not t:
            return False
        if opts["skip_scene_headers"] and TextParser._SCENE_RE.match(t):
            return False
        if opts["skip_caps"]:
            if (
                t.isupper()
                and len(t) < 50
                and "." not in t
                and not t.startswith(("(", "["))
            ):
                return False
        if opts["skip_parens"] and t.startswith(("(", "[")):
            return False
        return True

    @staticmethod
    def _auto_sync_targets(
        lines: list[dict[str, Any]],
        *,
        preserve_manual: bool,
        sync_opts: dict[str, bool] | None,
        start_idx: int | None = None,
        end_idx: int | None = None,
    ) -> list[int]:
        lo = 0 if start_idx is None else max(0, start_idx)
        hi = len(lines) - 1 if end_idx is None else min(len(lines) - 1, end_idx)
        targets: list[int] = []
        for i, line in enumerate(lines):
            if i < lo or i > hi:
                continue
            if preserve_manual and TextParser.is_manually_linked(line):
                continue
            if not TextParser.should_sync_line(line.get("text", ""), sync_opts):
                continue
            targets.append(i)
        return targets

    @staticmethod
    def _apply_clip_span_to_line(
        result: list[dict[str, Any]],
        idx: int,
        clip: dict[str, Any],
        frame: float,
        end_frame: int,
        fps: float,
    ) -> None:
        start_tc = Timecode.frames_to_timecode(int(frame), fps)
        end_tc = Timecode.frames_to_timecode(end_frame, fps)
        row = result[idx]
        row["start_tc"] = start_tc
        row["end_tc"] = end_tc
        row["clip_name"] = clip.get("name")
        row["clip_start_frame"] = clip["start_frame"]
        row["clip_end_frame"] = clip["end_frame"]
        row["clip_index"] = clip.get("clip_index")
        row["clip_uid"] = clip.get("clip_uid") or (
            f"v{clip.get('track_index', 1)}_{clip['start_frame']}"
        )
        row["track_index"] = clip.get("track_index", 1)
        row["track_label"] = clip.get("track_label", f"V{clip.get('track_index', 1)}")
        row["synced"] = True
        for key in (
            "link_id",
            "link_type",
            "link_color",
            "links",
            "marker_frame",
        ):
            row.pop(key, None)

    @staticmethod
    def associate_timecodes(
        lines: list[dict[str, Any]],
        total_duration_frames: int,
        fps: float = 24.0,
        start_frame: int = 0,
        preserve_manual: bool = True,
        sync_opts: dict[str, bool] | None = None,
        start_idx: int | None = None,
        end_idx: int | None = None,
    ) -> list[dict[str, Any]]:
        """Distribute eligible lines evenly across timeline duration."""
        if not lines:
            return []

        result = [dict(line) for line in lines]
        targets = TextParser._auto_sync_targets(
            result,
            preserve_manual=preserve_manual,
            sync_opts=sync_opts,
            start_idx=start_idx,
            end_idx=end_idx,
        )
        if not targets:
            return result

        duration_per_line = total_duration_frames / len(targets)
        current_frame = start_frame
        for idx in targets:
            start_tc = Timecode.frames_to_timecode(int(current_frame), fps)
            current_frame += duration_per_line
            end_tc = Timecode.frames_to_timecode(int(current_frame), fps)
            row = result[idx]
            row["start_tc"] = start_tc
            row["end_tc"] = end_tc
            row["synced"] = True
            for key in ("link_id", "link_type", "link_color", "links", "marker_frame"):
                row.pop(key, None)
        return result

    @staticmethod
    def associate_by_clips(
        lines: list[dict[str, Any]],
        clips: list[dict[str, Any]],
        fps: float = 24.0,
        preserve_manual: bool = True,
        sync_opts: dict[str, bool] | None = None,
        start_idx: int | None = None,
        end_idx: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Map eligible script lines to timeline clips by proportional duration.
        Manually linked lines (link_id) are never overwritten.
        """
        if not lines:
            return []
        if not clips:
            return [dict(line) for line in lines]

        result = [dict(line) for line in lines]
        unlinked = TextParser._auto_sync_targets(
            result,
            preserve_manual=preserve_manual,
            sync_opts=sync_opts,
            start_idx=start_idx,
            end_idx=end_idx,
        )
        if not unlinked:
            return result

        clips = sorted(clips, key=lambda c: c["start_frame"])
        n = len(unlinked)
        durations = [max(1, c["end_frame"] - c["start_frame"]) for c in clips]
        total = sum(durations)

        counts: list[int] = []
        remaining = n
        for i, dur in enumerate(durations):
            clips_left = len(durations) - i
            if i == len(durations) - 1:
                counts.append(remaining)
            else:
                share = max(1, round(n * dur / total)) if remaining > clips_left else 1
                share = min(share, remaining - (clips_left - 1))
                counts.append(share)
                remaining -= share

        line_i = 0
        for clip, count in zip(clips, counts):
            if count <= 0 or line_i >= n:
                continue
            clip_span = max(1, clip["end_frame"] - clip["start_frame"])
            per_line = clip_span / count
            frame = float(clip["start_frame"])

            for _ in range(count):
                if line_i >= n:
                    break
                idx = unlinked[line_i]
                frame += per_line
                end_frame = min(int(frame), clip["end_frame"])
                TextParser._apply_clip_span_to_line(
                    result, idx, clip, frame - per_line, end_frame, fps
                )
                line_i += 1

        return result

    @staticmethod
    def _norm_match_text(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").lower().strip())

    @staticmethod
    def associate_srt_to_lines(
        script_lines: list[dict[str, Any]],
        srt_lines: list[dict[str, Any]],
        fps: float = 24.0,
        preserve_manual: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Map external SRT/Rev cues onto script lines (text match, then order fallback).
        Does not use phonetic indexing.
        """
        if not script_lines or not srt_lines:
            return [dict(line) for line in script_lines]

        result = [dict(line) for line in script_lines]
        used_srt: set[int] = set()
        used_script: set[int] = set()

        for si, sline in enumerate(srt_lines):
            s_text = TextParser._norm_match_text(sline.get("text", ""))
            if not s_text:
                continue
            best_i = -1
            best_score = 0
            for li, line in enumerate(result):
                if li in used_script:
                    continue
                if preserve_manual and TextParser.is_manually_linked(line):
                    continue
                l_text = TextParser._norm_match_text(line.get("text", ""))
                if not l_text:
                    continue
                if s_text == l_text:
                    best_i = li
                    best_score = 100
                    break
                if s_text in l_text or l_text in s_text:
                    score = min(len(s_text), len(l_text))
                    if score > best_score:
                        best_score = score
                        best_i = li
            if best_i < 0:
                continue
            used_srt.add(si)
            used_script.add(best_i)
            row = result[best_i]
            row["start_tc"] = sline.get("start_tc")
            row["end_tc"] = sline.get("end_tc")
            row["synced"] = True
            row["srt_source"] = True

        script_pool = [
            i
            for i, line in enumerate(result)
            if i not in used_script
            and (line.get("text") or "").strip()
            and not (preserve_manual and TextParser.is_manually_linked(line))
        ]
        srt_pool = [
            i for i, s in enumerate(srt_lines) if i not in used_srt and s.get("start_tc")
        ]
        for li, si in zip(script_pool, srt_pool):
            row = result[li]
            sline = srt_lines[si]
            row["start_tc"] = sline.get("start_tc")
            row["end_tc"] = sline.get("end_tc")
            row["synced"] = True
            row["srt_source"] = True

        return result

    @staticmethod
    def build_scene_index(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scenes: list[dict[str, Any]] = []
        for i, line in enumerate(lines):
            text = (line.get("text") or "").strip()
            if not text:
                continue
            if TextParser._SCENE_RE.match(text) or (
                text.isupper() and len(text) < 60 and (" - " in text or " – " in text)
            ):
                scenes.append(
                    {
                        "index": i,
                        "number": len(scenes) + 1,
                        "title": text[:72],
                    }
                )
        return scenes

    @staticmethod
    def build_page_index(
        lines: list[dict[str, Any]], lines_per_page: int = 54
    ) -> list[dict[str, Any]]:
        if not lines:
            return []
        pages: list[dict[str, Any]] = []
        for start in range(0, len(lines), lines_per_page):
            pages.append(
                {
                    "index": start,
                    "number": len(pages) + 1,
                    "title": f"Page {len(pages) + 1}",
                }
            )
        return pages

    @staticmethod
    def normalize_for_ui(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure every line dict has consistent keys for JSON → UI."""
        from core.link_model import get_line_links, line_has_links

        normalized = []
        for i, line in enumerate(lines):
            links = get_line_links(line)
            normalized.append(
                {
                    "text": line.get("text", ""),
                    "line_number": line.get("line_number", i + 1),
                    "start_tc": line.get("start_tc") or line.get("timecode"),
                    "end_tc": line.get("end_tc"),
                    "speaker": line.get("speaker"),
                    "clip_name": line.get("clip_name"),
                    "clip_index": line.get("clip_index"),
                    "clip_uid": line.get("clip_uid"),
                    "track_index": line.get("track_index"),
                    "track_label": line.get("track_label"),
                    "links": links,
                    "link_id": line.get("link_id"),
                    "link_color": line.get("link_color"),
                    "link_type": line.get("link_type"),
                    "marker_frame": line.get("marker_frame"),
                    "note": line.get("note") or "",
                    "synced": line_has_links(line)
                    or bool(line.get("start_tc") or line.get("timecode")),
                }
            )
        return normalized
