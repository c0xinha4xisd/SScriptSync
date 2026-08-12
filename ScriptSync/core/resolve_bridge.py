"""
DaVinci Resolve API bridge — timeline clips, project context.
All Resolve object calls are isolated here for testability and docs.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.timecode import Timecode

log = logging.getLogger("sscriptsync_v1")


class ResolveBridge:
    """Thin wrapper around Resolve Scripting API objects."""

    def __init__(self, resolve=None):
        self._resolve = resolve
        self._project = None
        self._timeline = None
        self._fps = 24.0

    @property
    def resolve(self):
        return self._resolve

    @property
    def project(self):
        return self._project

    @property
    def timeline(self):
        return self._timeline

    @property
    def fps(self) -> float:
        return self._fps

    def connect(self) -> bool:
        """Refresh project/timeline handles from Resolve."""
        if not self._resolve:
            return False
        try:
            pm_fn = getattr(self._resolve, "GetProjectManager", None)
            if not callable(pm_fn):
                log.debug("ResolveBridge.connect: GetProjectManager unavailable")
                self._timeline = None
                return False
            pm = pm_fn()
            if not pm:
                self._timeline = None
                return False
            get_project = getattr(pm, "GetCurrentProject", None)
            self._project = get_project() if callable(get_project) else None
            if self._project:
                get_tl = getattr(self._project, "GetCurrentTimeline", None)
                self._timeline = get_tl() if callable(get_tl) else None
            else:
                self._timeline = None
            if self._timeline:
                self._fps = Timecode.get_timeline_fps(self._timeline)
                return True
        except Exception as e:
            log.debug("ResolveBridge.connect error: %s", e)
        self._timeline = None
        return False

    def get_context(self) -> dict[str, Any]:
        """Project + timeline metadata for persistence keys and UI."""
        ctx = {
            "connected": self._timeline is not None,
            "project_name": "",
            "timeline_name": "",
            "fps": self._fps,
        }
        try:
            if self._project:
                ctx["project_name"] = self._project.GetName() or "Untitled Project"
            if self._timeline:
                ctx["timeline_name"] = self._timeline.GetName() or "Untitled Timeline"
                ctx["fps"] = self._fps
                ctx["start_frame"] = self._timeline.GetStartFrame()
                ctx["end_frame"] = self._timeline.GetEndFrame()
                ctx["start_timecode"] = self._timeline.GetStartTimecode()
                ctx["current_timecode"] = self._timeline.GetCurrentTimecode()
                ctx["duration_tc"] = Timecode.frames_to_timecode(
                    ctx["end_frame"] - ctx["start_frame"], self._fps
                )
        except Exception as e:
            log.debug("get_context error: %s", e)
        return ctx

    def get_timeline_clips(
        self,
        track_type: str = "video",
        track_index: int = 0,
        include_audio: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Return clips on timeline track(s), sorted by start frame.
        track_index=0 → all tracks of each requested type (V1…Vn, optionally A1…An).
        """
        if not self._timeline:
            return []

        clips: list[dict[str, Any]] = []
        try:
            types = ["video", "audio"] if include_audio else [track_type]
            for tt in types:
                if track_index == 0:
                    track_count = self._track_count(tt)
                    for i in range(1, track_count + 1):
                        clips.extend(self._items_on_track(tt, i))
                    if not clips and tt == "video":
                        clips.extend(self._items_on_track(tt, 1))
                else:
                    clips.extend(self._items_on_track(tt, track_index))

            clips.sort(key=lambda c: (c["start_frame"], c.get("track_type") != "video"))
            for i, c in enumerate(clips):
                c["clip_index"] = i
        except Exception as e:
            log.error("get_timeline_clips error: %s", e)

        return clips

    def _track_count(self, track_type: str = "video") -> int:
        """Resolve may return 0 when only V1 has clips — always scan at least V1."""
        if not self._timeline:
            return 1
        try:
            n = int(self._timeline.GetTrackCount(track_type) or 0)
        except Exception:
            n = 0
        return max(1, n)

    _video_track_count = _track_count

    def _items_on_track(self, track_type: str, track_index: int) -> list[dict]:
        items: list[dict] = []
        try:
            track_items = self._timeline.GetItemListInTrack(track_type, track_index)
            if not track_items:
                return items

            for i, item in enumerate(track_items):
                try:
                    start = int(item.GetStart())
                    end = int(item.GetEnd())
                    name = item.GetName() or "Clip"
                    uid_prefix = "a" if track_type == "audio" else "v"
                    track_label = (
                        f"A{track_index}" if track_type == "audio" else f"V{track_index}"
                    )
                    items.append(
                        {
                            "clip_index": 0,
                            "clip_uid": f"{uid_prefix}{track_index}_{start}",
                            "name": name,
                            "start_frame": start,
                            "end_frame": end,
                            "duration_frames": max(1, end - start),
                            "start_tc": Timecode.frames_to_timecode(start, self._fps),
                            "end_tc": Timecode.frames_to_timecode(end, self._fps),
                            "track_type": track_type,
                            "track_index": track_index,
                            "track_label": track_label,
                            "is_audio": track_type == "audio",
                        }
                    )
                except Exception as e:
                    log.debug("Skip clip item: %s", e)
        except Exception as e:
            log.debug("Track %s/%d error: %s", track_type, track_index, e)
        return items

    def set_playhead(self, timecode: str, max_attempts: int = 8) -> bool:
        """Set playhead via SetCurrentTimecode with retry loop."""
        if not self._timeline:
            return False
        import time

        for attempt in range(max_attempts):
            try:
                ok = self._timeline.SetCurrentTimecode(timecode)
                current = self._timeline.GetCurrentTimecode()
                if current == timecode:
                    return True
                if ok:
                    time.sleep(0.05)
                    if self._timeline.GetCurrentTimecode() == timecode:
                        return True
            except Exception as e:
                log.warning("SetCurrentTimecode attempt %d: %s", attempt + 1, e)
            time.sleep(0.05)
        return False

    def find_timeline_item(self, clip: dict[str, Any]):
        """Locate a TimelineItem from clip metadata (track + start frame)."""
        if not self._timeline or not clip:
            return None
        track_type = clip.get("track_type") or ("audio" if clip.get("is_audio") else "video")
        track_index = int(clip.get("track_index") or 1)
        start_f = int(clip.get("start_frame", -1))
        uid = clip.get("clip_uid") or ""
        try:
            items = self._timeline.GetItemListInTrack(track_type, track_index) or []
            for item in items:
                try:
                    if int(item.GetStart()) == start_f:
                        return item
                except Exception:
                    continue
            if uid:
                for item in items:
                    try:
                        guess = f"{'a' if track_type == 'audio' else 'v'}{track_index}_{int(item.GetStart())}"
                        if guess == uid:
                            return item
                    except Exception:
                        continue
        except Exception as e:
            log.debug("find_timeline_item: %s", e)
        return None

    def _try_select_timeline_item(self, item) -> bool:
        """Best-effort timeline/bin selection (API varies by Resolve version)."""
        timeline = self._timeline
        if not timeline or not item:
            return False
        for method_name in ("SetSelectedClips", "SelectClips"):
            fn = getattr(timeline, method_name, None)
            if not callable(fn):
                continue
            for args in (([item],), (item,), ([item], True)):
                try:
                    if fn(*args):
                        log.info("Timeline selection via %s OK", method_name)
                        return True
                except Exception as e:
                    log.debug("%s failed: %s", method_name, e)
        try:
            mpi = item.GetMediaPoolItem()
            mp = self._project.GetMediaPool() if self._project else None
            if mpi and mp and hasattr(mp, "SetSelectedClip"):
                if mp.SetSelectedClip(mpi):
                    log.info("Media pool selection OK for clip focus")
                    return True
        except Exception as e:
            log.debug("SetSelectedClip fallback: %s", e)
        return False

    def focus_clip(self, clip: dict[str, Any]) -> dict[str, Any]:
        """
        Focus a clip in Resolve: playhead + in/out marks (visual range) + selection if supported.
        """
        result = {"playhead": False, "marks": False, "selection": False}
        if not self._timeline or not clip:
            return result

        start_tc = clip.get("start_tc")
        start_f = int(clip.get("start_frame", 0))
        end_f = int(clip.get("end_frame", start_f + 1))
        track_type = clip.get("track_type") or ("audio" if clip.get("is_audio") else "video")

        if start_tc:
            result["playhead"] = self.set_playhead(start_tc)

        item = self.find_timeline_item(clip)
        if item:
            result["selection"] = self._try_select_timeline_item(item)

        mark_type = "audio" if track_type == "audio" else "video"
        try:
            ok = self._timeline.SetMarkInOut(start_f, end_f, mark_type)
            if not ok:
                ok = self._timeline.SetMarkInOut(start_f, end_f, "all")
            result["marks"] = bool(ok)
        except Exception as e:
            log.debug("SetMarkInOut failed: %s", e)

        log.info(
            "focus_clip %s (%s): playhead=%s marks=%s selection=%s",
            clip.get("name"),
            clip.get("track_label"),
            result["playhead"],
            result["marks"],
            result["selection"],
        )
        return result

    def add_marker(
        self,
        frame: int,
        name: str,
        note: str = "",
        color: str = "Green",
        custom_data: str = "",
        duration: int = 1,
    ) -> bool:
        """Add timeline marker at frame (Resolve API)."""
        if not self._timeline:
            return False
        try:
            ok = self._timeline.AddMarker(
                int(frame), color, name, note, duration, custom_data
            )
            log.info("AddMarker frame=%s name=%s ok=%s", frame, name, ok)
            return bool(ok)
        except Exception as e:
            log.error("AddMarker failed: %s", e)
            return False

    def delete_marker_at_frame(self, frame: int) -> bool:
        if not self._timeline:
            return False
        try:
            return bool(self._timeline.DeleteMarkerAtFrame(int(frame)))
        except Exception:
            return False

    def get_current_timecode(self) -> Optional[str]:
        if not self._timeline:
            return None
        try:
            return self._timeline.GetCurrentTimecode()
        except Exception:
            return None


def try_connect_resolve() -> Optional[Any]:
    """
    Attempt scriptapp('Resolve') from external process.
    Requires Resolve Studio + External scripting = Local.
    """
    try:
        import DaVinciResolveScript as dvr_script

        resolve = dvr_script.scriptapp("Resolve")
        if resolve:
            log.info("Connected via DaVinciResolveScript.scriptapp('Resolve')")
            return resolve
    except ImportError:
        log.debug("DaVinciResolveScript module not on PYTHONPATH")
    except Exception as e:
        log.debug("scriptapp failed: %s", e)
    return None


def add_resolve_module_path():
    """Add Resolve's Fusion/Scripts/Modules to sys.path (Studio 18–21)."""
    import os
    import sys

    candidates = []
    if sys.platform == "win32":
        candidates += [
            os.path.expandvars(
                r"%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
            ),
            os.path.expandvars(
                r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Modules"
            ),
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Modules",
        ]
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        candidates += [
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
            f"{home}/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Modules",
        ]
    else:
        candidates += [
            "/opt/resolve/Developer/Scripting/Modules",
            os.path.expanduser("~/.local/share/DaVinciResolve/Fusion/Scripts/Modules"),
        ]

    for path in candidates:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)
            log.debug("Added Resolve modules path: %s", path)
