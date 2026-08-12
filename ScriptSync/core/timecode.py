"""
SMPTE timecode utilities.
Ported from timecode.js — pure Python, no Resolve dependency.
"""

from __future__ import annotations

import re
from typing import Optional


class Timecode:
    """Frame-accurate SMPTE timecode conversions."""

    _TC_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}:\d{2}$")

    @staticmethod
    def timecode_to_frames(timecode: Optional[str], fps: float = 24.0) -> int:
        if not timecode or timecode == "--:--:--:--":
            return 0

        parts = timecode.split(":")
        if len(parts) != 4:
            return 0

        try:
            hours, minutes, seconds, frames = (int(p) for p in parts)
        except ValueError:
            return 0

        fps_int = int(round(fps))
        return (hours * 3600 + minutes * 60 + seconds) * fps_int + frames

    @staticmethod
    def frames_to_timecode(total_frames: int, fps: float = 24.0) -> str:
        if total_frames < 0:
            total_frames = 0

        fps_int = max(1, int(round(fps)))
        total_seconds = total_frames // fps_int
        frames = total_frames % fps_int

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

    @staticmethod
    def timecode_to_seconds(timecode: str, fps: float = 24.0) -> float:
        return Timecode.timecode_to_frames(timecode, fps) / fps

    @staticmethod
    def seconds_to_timecode(total_seconds: float, fps: float = 24.0) -> str:
        fps_int = max(1, int(round(fps)))
        total_frames = round(total_seconds * fps_int)
        return Timecode.frames_to_timecode(total_frames, fps)

    @staticmethod
    def add_timecodes(tc1: str, tc2: str, fps: float = 24.0) -> str:
        frames = Timecode.timecode_to_frames(tc1, fps) + Timecode.timecode_to_frames(tc2, fps)
        return Timecode.frames_to_timecode(frames, fps)

    @staticmethod
    def subtract_timecodes(tc1: str, tc2: str, fps: float = 24.0) -> str:
        frames = max(
            0,
            Timecode.timecode_to_frames(tc1, fps) - Timecode.timecode_to_frames(tc2, fps),
        )
        return Timecode.frames_to_timecode(frames, fps)

    @staticmethod
    def get_duration(start_tc: str, end_tc: str, fps: float = 24.0) -> str:
        return Timecode.subtract_timecodes(end_tc, start_tc, fps)

    @staticmethod
    def is_valid_timecode(timecode: Optional[str]) -> bool:
        return bool(timecode and Timecode._TC_PATTERN.match(timecode))

    @staticmethod
    def parse_srt_timestamp(
        srt_time: str, fps: float = 24.0
    ) -> Optional[dict[str, str]]:
        parts = srt_time.split(" --> ")
        if len(parts) != 2:
            return None

        def _convert(srt: str) -> str:
            time_part, ms_part = srt.split(",")
            h, m, s = (int(x) for x in time_part.split(":"))
            fps_int = max(1, int(round(fps)))
            frames = round((int(ms_part) / 1000.0) * fps_int)
            base = (h * 3600 + m * 60 + s) * fps_int + frames
            return Timecode.frames_to_timecode(base, fps)

        return {"start": _convert(parts[0]), "end": _convert(parts[1])}

    @staticmethod
    def get_timeline_fps(timeline) -> float:
        """Read FPS from a Resolve Timeline object."""
        try:
            setting = timeline.GetSetting("timelineFrameRate")
            if setting:
                return float(setting)
        except Exception:
            pass
        return 24.0

    @staticmethod
    def find_line_at_timecode(
        lines: list[dict], timecode: str, fps: float = 24.0
    ) -> int:
        """Return index of the line whose range contains timecode, or -1."""
        current = Timecode.timecode_to_frames(timecode, fps)
        for i, line in enumerate(lines):
            start_tc = line.get("start_tc")
            end_tc = line.get("end_tc")
            if not start_tc:
                single = line.get("timecode")
                if single and Timecode.timecode_to_frames(single, fps) == current:
                    return i
                continue
            start_f = Timecode.timecode_to_frames(start_tc, fps)
            end_f = Timecode.timecode_to_frames(end_tc, fps) if end_tc else start_f
            if start_f <= current <= end_f:
                return i
        return -1

    @staticmethod
    def find_line_at_playhead(
        lines: list[dict],
        timecode: str,
        fps: float = 24.0,
        timeline_clips: list[dict] | None = None,
    ) -> int:
        """
        Find active script line for playhead — uses all video tracks (V1–Vn).
        Prefers lines linked to clips under the playhead on the timeline.
        """
        from core.link_model import get_line_links

        current = Timecode.timecode_to_frames(timecode, fps)
        active_uids: set[str] = set()
        if timeline_clips:
            for clip in timeline_clips:
                try:
                    sf = int(clip.get("start_frame", 0))
                    ef = int(clip.get("end_frame", sf))
                except (TypeError, ValueError):
                    continue
                if sf <= current < ef:
                    uid = clip.get("clip_uid") or f"v{clip.get('track_index', 1)}_{sf}"
                    active_uids.add(str(uid))

        candidates: list[tuple[int, int, int]] = []
        for i, line in enumerate(lines):
            for link in get_line_links(line):
                uid = link.get("clip_uid")
                if uid and active_uids and str(uid) not in active_uids:
                    continue

                start_tc = link.get("start_tc")
                end_tc = link.get("end_tc") or start_tc
                if start_tc:
                    start_f = Timecode.timecode_to_frames(start_tc, fps)
                    end_f = (
                        Timecode.timecode_to_frames(end_tc, fps)
                        if end_tc
                        else start_f
                    )
                    if start_f <= current <= end_f:
                        span = max(0, end_f - start_f)
                        track_bonus = 0 if uid and str(uid) in active_uids else 1000000
                        candidates.append((track_bonus + span, i, span))
                        continue

                csf = link.get("clip_start_frame")
                cef = link.get("clip_end_frame")
                if csf is not None and cef is not None:
                    if int(csf) <= current < int(cef):
                        span = int(cef) - int(csf)
                        track_bonus = 0 if uid and str(uid) in active_uids else 1000000
                        candidates.append((track_bonus + span, i, span))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return Timecode.find_line_at_timecode(lines, timecode, fps)
