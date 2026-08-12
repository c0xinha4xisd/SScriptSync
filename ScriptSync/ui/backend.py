"""
Backend — QObject exposed to JavaScript via QWebChannel.
All Resolve API calls and core logic happen here.
"""
import copy
import json
import logging
import os
import time

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from core.export_io import export_bundle
from core.project_io import (
    apply_sidecar_lines,
    load_sidecar,
    merge_text_preserving_links,
    reconcile_clip_indices,
    rematch_links_to_timeline,
    save_sidecar,
)
from core.resolve_bridge import ResolveBridge
from core.sync_store import load_session, save_session
from core.text_parser import TextParser
from core.timecode import Timecode

log = logging.getLogger("sscriptsync_v1")
MAX_LINK_UNDO = 50


class Backend(QObject):
    # ── Python → JavaScript signals ───────────────────────────────────────────
    connection_changed = Signal(bool, str)
    status_changed = Signal(str, str)
    script_loaded = Signal(str)
    lines_updated = Signal(str)
    clips_updated = Signal(str)
    thumbnail_ready = Signal(str, str)
    timeline_info = Signal(str)
    timecode_changed = Signal(str)
    active_line_changed = Signal(int)
    sync_completed = Signal(bool, str)
    session_loaded = Signal(str)
    playback_mode_changed = Signal(bool)

    def __init__(self, window, resolve=None, comp=None, parent=None):
        super().__init__(parent)
        self._win = window
        self._comp = comp
        self._resolve = resolve
        self._bridge = ResolveBridge(resolve)
        self._watcher = None
        self._js_ready = False
        self._fps = 24.0
        self._current_script = ""
        self._current_format = "auto"
        self._sync_mode = "linear"
        self._parsed_lines: list[dict] = []
        self._is_synced = False
        self._is_connected = False
        self._last_active_line = -1
        self._last_line_track_at = 0.0
        self._import_path = ""
        self._project_name = ""
        self._timeline_name = ""
        self._last_clips_json = ""
        self._thumb_queue: list[dict] = []
        self._thumb_busy = False
        self._cached_clips: list[dict] = []
        self._link_undo: list[list[dict]] = []
        self._link_redo: list[list[dict]] = []
        self._playback_active = False
        self._tc_burst = 0
        self._last_tc_mono = 0.0
        self._connect_pending = False
        self._ctx_cache: dict = {}
        if resolve:
            QTimer.singleShot(50, self.check_connection)

    def _reconnect_resolve_if_stale(self) -> bool:
        """Re-acquire scriptapp when the handle goes stale (NoneType API errors)."""
        try:
            from core.resolve_connection import get_resolve

            fresh = get_resolve()
            if not fresh:
                return False
            self._resolve = fresh
            self._bridge = ResolveBridge(fresh)
            log.info("Resolve handle refreshed")
            return self._bridge.connect()
        except Exception as e:
            log.debug("Resolve reconnect failed: %s", e)
            return False

    def _sync_ui_after_connect(self):
        """Push timeline/clips/lines to JS — safe after connect or js_ready."""
        if self._parsed_lines:
            self._emit_lines()
        if self._cached_clips:
            self.clips_updated.emit(json.dumps(self._cached_clips))
        elif self._timeline:
            self._load_clips(force=True)
        self._emit_timeline_info()
        self._announce_connection()

    def attach_resolve(self, resolve):
        """Deferred Resolve handle — after UI is visible."""
        if not resolve:
            return
        self._resolve = resolve
        self._bridge = ResolveBridge(resolve)
        log.info("Resolve attached")
        QTimer.singleShot(50, self.check_connection)

    @Slot()
    def check_connection(self):
        if self._resolve:
            if self._connect_pending:
                return
            self._connect_pending = True
            if self._js_ready:
                self.status_changed.emit("Conectando ao Resolve…", "#9ccfd8")
            # Resolve API must run on Qt main thread — defer one tick so window paints first.
            QTimer.singleShot(0, self._connect_sync)
            return

        if self._comp and not self._resolve:
            self._is_connected = False
            self._announce_connection()
            log.info("Fusion comp only — no timeline API")
            return

        self._is_connected = False
        self._announce_connection()
        log.info("Standalone mode")

    def _connect_sync(self):
        """Main-thread Resolve connect — required for scriptapp objects."""
        self._connect_pending = False
        try:
            self._bridge = ResolveBridge(self._resolve)
            if not self._bridge.connect():
                if self._reconnect_resolve_if_stale() and self._bridge.connect():
                    log.info("Resolve reconnected after stale handle")
                else:
                    self._is_connected = bool(self._resolve)
                    log.warning("Resolve connected but no timeline open")
                    self._sync_ui_after_connect()
                    QTimer.singleShot(3000, self._retry_connect)
                    return

            self._refresh_context(force=True)
            self._is_connected = True
            self._try_load_session()
            self._load_clips(force=True)
            self.update_timeline_info()
            self._start_watcher()
            self._sync_ui_after_connect()
            log.info("Resolve timeline connected: %s", self._timeline_name)
        except Exception as e:
            log.error("Resolve connect error: %s", e)
            if self._reconnect_resolve_if_stale():
                QTimer.singleShot(0, self._connect_sync)
                return
            self._is_connected = bool(self._resolve)
            self._sync_ui_after_connect()
            QTimer.singleShot(3000, self._retry_connect)

    def _retry_connect(self):
        if not self._resolve or self._connect_pending:
            if self._resolve:
                QTimer.singleShot(3000, self._retry_connect)
            return
        if self._bridge.timeline:
            return
        self.check_connection()

    def _emit_timeline_info(self, ctx: dict | None = None):
        if ctx:
            self._ctx_cache = ctx
        elif self._bridge.timeline:
            ctx = self._bridge.get_context()
            self._ctx_cache = ctx
        else:
            ctx = self._ctx_cache
        if not ctx:
            return
        info = {
            "name": ctx.get("timeline_name", self._timeline_name),
            "project_name": ctx.get("project_name", self._project_name),
            "fps": ctx.get("fps", self._fps),
            "start_frame": ctx.get("start_frame"),
            "end_frame": ctx.get("end_frame"),
            "duration_tc": ctx.get("duration_tc"),
            "current_timecode": ctx.get("current_timecode"),
            "line_count": len(self._parsed_lines),
            "is_synced": self._is_synced,
            "sync_mode": self._sync_mode,
        }
        self.timeline_info.emit(json.dumps(info))

    @property
    def _timeline(self):
        return self._bridge.timeline

    def _set_resolve(self, resolve):
        self._resolve = resolve
        self._bridge = ResolveBridge(resolve)

    def _announce_connection(self):
        if not self._js_ready:
            return
        if self._resolve and self._is_connected:
            if self._bridge.timeline or self._timeline_name:
                self.connection_changed.emit(True, "Connected to Resolve Studio")
                self.status_changed.emit("Resolve Studio — timeline active", "#9ccfd8")
            else:
                self.connection_changed.emit(True, "Connected to Resolve Studio")
                self.status_changed.emit("Resolve Studio — open a timeline", "#f6c177")
        elif self._comp:
            self.connection_changed.emit(True, "Fusion mode")
            self.status_changed.emit("Fusion only — timeline sync unavailable", "#f6c177")
        else:
            self.connection_changed.emit(False, "Standalone mode")
            self.status_changed.emit("Standalone — no Resolve", "#6e6a86")

    @Slot()
    def js_ready(self):
        """Called by JS once QWebChannel is ready (required on Qt 6.7+)."""
        self._js_ready = True
        log.info("JavaScript ready")
        if self._resolve and not self._bridge.timeline and not self._connect_pending:
            self.check_connection()
        elif self._bridge.timeline:
            self._sync_ui_after_connect()
        else:
            self._announce_connection()

    def _start_watcher(self):
        if not self._resolve:
            return
        try:
            from core.resolve_connection import ResolveWatcher
            if self._watcher:
                self._watcher.stop()
            self._watcher = ResolveWatcher(self._resolve, parent=self)
            self._watcher.timeline_changed.connect(self._on_timeline_changed)
            self._watcher.timecode_changed.connect(self._on_timecode_changed)
            self._watcher.disconnected.connect(self._on_disconnected)
            self._watcher.start()
        except Exception as e:
            log.error("Watcher start failed: %s", e)

    def _on_timeline_changed(self, _name):
        self._last_clips_json = ""
        self._refresh_context()
        self.update_timeline_info()
        self._load_clips(force=True)

    def _on_timecode_changed(self, tc):
        now = time.monotonic()
        if tc and now - self._last_tc_mono < 0.45:
            self._tc_burst += 1
        else:
            self._tc_burst = 0
        self._last_tc_mono = now
        if not self._playback_active and self._tc_burst >= 2:
            self.set_playback_mode(True)

        if self._playback_active:
            return

        self.timecode_changed.emit(tc)
        if not self._parsed_lines or not tc:
            return
        from core.link_model import line_has_links

        if not self._is_synced and not any(
            line_has_links(l) or l.get("start_tc") for l in self._parsed_lines
        ):
            return

        now = time.monotonic()
        if now - self._last_line_track_at < 0.4:
            return

        idx = Timecode.find_line_at_playhead(
            self._parsed_lines, tc, self._fps, self._cached_clips
        )
        if idx != self._last_active_line:
            self._last_active_line = idx
            self._last_line_track_at = now
            self.active_line_changed.emit(idx)

    @Slot(bool)
    def set_playback_mode(self, active: bool):
        """Pause heavy Resolve API work during playback — keep UI responsive."""
        active = bool(active)
        if self._playback_active == active:
            return
        self._playback_active = active
        log.debug("playback_mode=%s", active)
        if self._watcher:
            self._watcher.set_playback_mode(active)
        if active:
            self._thumb_queue.clear()
            self._thumb_busy = False
        else:
            self._tc_burst = 0
            QTimer.singleShot(150, self._on_playback_stopped)
        self.playback_mode_changed.emit(active)

    def _on_playback_stopped(self):
        if self._playback_active:
            return
        if not self._bridge.connect() and self._resolve:
            self._reconnect_resolve_if_stale()
        self._refresh_context(force=True)
        self.update_timeline_info()
        self._load_clips(force=True)
        if self._timeline and self._parsed_lines:
            tc = self._bridge.get_current_timecode()
            if tc:
                self.timecode_changed.emit(tc)
                idx = Timecode.find_line_at_playhead(
                    self._parsed_lines, tc, self._fps, self._cached_clips
                )
                if idx >= 0:
                    self._last_active_line = idx
                    self.active_line_changed.emit(idx)

    def _on_disconnected(self):
        log.warning("Resolve disconnected")
        self._is_connected = False
        self._announce_connection()

    def _session_key_ok(self) -> bool:
        return bool(self._project_name and self._timeline_name)

    def _persist_session(self):
        if not self._session_key_ok():
            return
        try:
            save_session(
                self._project_name,
                self._timeline_name,
                lines=self._parsed_lines,
                import_path=self._import_path,
                fmt=self._current_format,
                is_synced=self._is_synced,
                sync_mode=self._sync_mode,
            )
        except Exception as e:
            log.error("Persist session error: %s", e)

    def _save_sidecar_if_path(self):
        if not self._import_path or self._import_path.lower().endswith(".ssync.json"):
            return
        try:
            save_sidecar(
                self._import_path,
                lines=self._parsed_lines,
                fmt=self._current_format,
                sync_mode=self._sync_mode,
                is_synced=self._is_synced,
            )
        except Exception as e:
            log.debug("Sidecar save skipped: %s", e)

    def _try_load_session(self):
        if not self._session_key_ok() or self._parsed_lines:
            return
        data = load_session(self._project_name, self._timeline_name)
        if not data:
            return
        try:
            self._parsed_lines = data.get("lines", [])
            self._current_format = data.get("format", "auto")
            self._is_synced = data.get("is_synced", False)
            self._sync_mode = data.get("sync_mode", "linear")
            self._import_path = data.get("import_path", "")
            clips = self._bridge.get_timeline_clips("video", 0) if self._timeline else []
            reconcile_clip_indices(self._parsed_lines, clips)
            self._current_script = TextParser.to_text(self._parsed_lines, "txt")
            self._emit_lines()
            self.update_timeline_info()
            self.session_loaded.emit(
                f"Restored {len(self._parsed_lines)} lines for {self._timeline_name}"
            )
            self.status_changed.emit(
                f"Session restored: {self._timeline_name}", "#9ccfd8"
            )
        except Exception as e:
            log.error("Load session error: %s", e)

    def _emit_lines(self):
        self.lines_updated.emit(json.dumps(TextParser.normalize_for_ui(self._parsed_lines)))

    def _push_link_undo(self) -> None:
        self._link_undo.append(copy.deepcopy(self._parsed_lines))
        if len(self._link_undo) > MAX_LINK_UNDO:
            self._link_undo.pop(0)
        self._link_redo.clear()

    def _restore_link_state(self, lines: list[dict]) -> None:
        self._parsed_lines = copy.deepcopy(lines)
        self._is_synced = any(
            l.get("start_tc") or l.get("link_id") for l in self._parsed_lines
        )
        self._current_script = TextParser.to_text(self._parsed_lines, "txt")
        self._emit_lines()
        self._persist_session()
        self._save_sidecar_if_path()

    def _parse_sync_options(self, options_json: str) -> dict[str, bool]:
        try:
            raw = json.loads(options_json or "{}")
        except json.JSONDecodeError:
            raw = {}
        return TextParser.parse_sync_options(raw if isinstance(raw, dict) else {})

    def _run_auto_sync(
        self,
        *,
        mode: str,
        sync_opts: dict[str, bool],
        start_idx: int | None = None,
        end_idx: int | None = None,
    ) -> None:
        if mode == "clips":
            clips = self._bridge.get_timeline_clips("video", 0)
            if clips:
                self._parsed_lines = TextParser.associate_by_clips(
                    self._parsed_lines,
                    clips,
                    self._fps,
                    preserve_manual=True,
                    sync_opts=sync_opts,
                    start_idx=start_idx,
                    end_idx=end_idx,
                )
                return
            log.warning("No clips on timeline — falling back to linear sync")
            mode = "linear"

        start_frame = self._timeline.GetStartFrame()
        end_frame = self._timeline.GetEndFrame()
        total_frames = max(1, end_frame - start_frame)
        self._parsed_lines = TextParser.associate_timecodes(
            self._parsed_lines,
            total_frames,
            self._fps,
            start_frame,
            preserve_manual=True,
            sync_opts=sync_opts,
            start_idx=start_idx,
            end_idx=end_idx,
        )

    def update_timeline_info(self):
        if not self._timeline:
            return
        self._emit_timeline_info()

    @Slot()
    def refresh_clips(self):
        self._load_clips(force=False)

    def _load_clips(self, force: bool = False):
        if self._playback_active and not force:
            return
        if not self._timeline:
            self.clips_updated.emit("[]")
            return
        try:
            self._refresh_context(force=force)
            clips = self._bridge.get_timeline_clips(track_index=0, include_audio=True)
            reconcile_clip_indices(self._parsed_lines, clips)
            self._cached_clips = clips
            payload = json.dumps(clips)
            if not force and payload == self._last_clips_json:
                return
            self._last_clips_json = payload
            self.clips_updated.emit(payload)
        except Exception as e:
            log.debug("refresh_clips error: %s", e)

    @Slot()
    def resync_timeline(self):
        """Manual re-sync: re-read timeline clips and remap script links."""
        if not self._resolve:
            self.status_changed.emit("Re-sync failed: not connected", "#eb6f92")
            return
        if self._playback_active:
            self.status_changed.emit("Pare o playback no Resolve para re-sync", "#f6c177")
            return
        try:
            self._last_clips_json = ""
            self._refresh_context()
            clips = self._bridge.get_timeline_clips(track_index=0, include_audio=True)
            rematched = rematch_links_to_timeline(self._parsed_lines, clips, self._fps)
            reconcile_clip_indices(self._parsed_lines, clips)
            self._cached_clips = clips
            self._emit_lines()
            self._persist_session()
            self._save_sidecar_if_path()
            payload = json.dumps(clips)
            self._last_clips_json = payload
            self.clips_updated.emit(payload)
            self.update_timeline_info()
            self._queue_clip_thumbnails(clips)
            self.status_changed.emit(
                f"Re-synced {len(clips)} clip(s) — {rematched} line(s) updated",
                "#9ccfd8",
            )
            log.info("Manual re-sync: %d clips, %d links rematched", len(clips), rematched)
        except Exception as e:
            log.error("resync_timeline: %s", e)
            self.status_changed.emit(f"Re-sync failed: {e}", "#eb6f92")

    def _queue_clip_thumbnails(self, clips: list[dict]):
        self._thumb_queue = list(clips)[:24]
        if not self._thumb_busy and self._thumb_queue:
            self._thumb_busy = True
            QTimer.singleShot(80, self._fetch_next_thumbnail)

    def _fetch_next_thumbnail(self):
        if self._playback_active or not self._thumb_queue or not self._timeline:
            self._thumb_busy = False
            return
        clip = self._thumb_queue.pop(0)
        try:
            from core.thumbnail_cache import ThumbnailService, clip_cache_key

            svc = ThumbnailService(self._bridge)
            uri = svc.get_thumbnail_uri(clip)
            if uri:
                self.thumbnail_ready.emit(clip_cache_key(clip), uri)
        except Exception as e:
            log.debug("Thumbnail fetch error: %s", e)
        if self._thumb_queue:
            QTimer.singleShot(120, self._fetch_next_thumbnail)
        else:
            self._thumb_busy = False

    @Slot(str)
    def request_clip_thumbnail(self, clip_json: str):
        """On-demand thumbnail for a single linked clip."""
        if self._playback_active or not self._timeline:
            return
        try:
            clip = json.loads(clip_json)
            if clip.get("is_audio") or clip.get("track_type") == "audio":
                return
            from core.thumbnail_cache import ThumbnailService, clip_cache_key

            uri = ThumbnailService(self._bridge).get_thumbnail_uri(clip)
            if uri:
                self.thumbnail_ready.emit(clip_cache_key(clip), uri)
        except Exception as e:
            log.debug("request_clip_thumbnail: %s", e)

    def _refresh_context(self, force: bool = False):
        if self._playback_active and not force:
            return
        if not self._bridge.connect() and self._resolve:
            self._reconnect_resolve_if_stale()
        self._bridge.connect()
        ctx = self._bridge.get_context()
        self._ctx_cache = ctx
        self._fps = ctx.get("fps", 24.0)
        self._project_name = ctx.get("project_name", "")
        self._timeline_name = ctx.get("timeline_name", "")

    # ── File I/O ──────────────────────────────────────────────────────────────

    def _load_file(self, file_path: str, fmt: str = "auto"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._import_path = file_path
        self._current_script = content
        self._current_format = fmt if fmt != "auto" else TextParser.detect_format(content)
        self._parsed_lines = TextParser.parse(content, self._current_format, self._fps)

        sidecar = load_sidecar(file_path)
        if sidecar and sidecar.get("lines"):
            self._parsed_lines = apply_sidecar_lines(
                self._parsed_lines, sidecar["lines"]
            )
            self._sync_mode = sidecar.get("sync_mode", self._sync_mode)
            self._is_synced = sidecar.get(
                "is_synced",
                any(l.get("link_id") or l.get("start_tc") for l in self._parsed_lines),
            )
        else:
            self._is_synced = any(
                line.get("start_tc") or line.get("timecode") or line.get("link_id")
                for line in self._parsed_lines
            )

        if self._timeline:
            reconcile_clip_indices(
                self._parsed_lines,
                self._bridge.get_timeline_clips("video", 0),
            )

        plain = TextParser.to_text(self._parsed_lines, "txt")
        self.script_loaded.emit(plain)
        self._emit_lines()
        self.update_timeline_info()
        self._persist_session()

        name = os.path.basename(file_path)
        self.status_changed.emit(f"Imported: {name}", "#9ccfd8")
        log.info("Imported %s (%d lines)", name, len(self._parsed_lines))

    @Slot()
    def open_import_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self._win,
            "Import Script",
            "",
            "Script Files (*.txt *.srt *.csv *.ssync.json);;All Files (*.*)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".ssync.json"):
                self._load_project_file(path)
            else:
                self._load_file(path, "auto")
        except Exception as e:
            log.error("Import error: %s", e)
            self.status_changed.emit(f"Import failed: {e}", "#eb6f92")

    def _load_project_file(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._parsed_lines = data.get("lines", [])
        self._current_format = data.get("format", "auto")
        self._sync_mode = data.get("sync_mode", "linear")
        self._is_synced = data.get("is_synced", False)
        self._import_path = path
        self._current_script = TextParser.to_text(self._parsed_lines, "txt")
        if self._timeline:
            reconcile_clip_indices(
                self._parsed_lines,
                self._bridge.get_timeline_clips("video", 0),
            )
        self.script_loaded.emit(self._current_script)
        self._emit_lines()
        self.update_timeline_info()
        self._persist_session()
        self.status_changed.emit(
            f"Project loaded: {os.path.basename(path)}", "#9ccfd8"
        )

    @Slot(str)
    def import_script(self, file_path):
        if not file_path:
            self.open_import_dialog()
            return
        try:
            self._load_file(file_path)
        except Exception as e:
            log.error("Import error: %s", e)
            self.status_changed.emit(f"Import failed: {e}", "#eb6f92")

    @Slot(str, str)
    def save_script(self, content, fmt="txt"):
        path, _ = QFileDialog.getSaveFileName(
            self._win,
            "Save Script",
            self._import_path or "sscriptsync_v1_export.txt",
            "Text (*.txt);;SRT (*.srt);;CSV (*.csv);;Project JSON (*.ssync.json)",
        )
        if not path:
            return
        try:
            self._refresh_context()
            use_fmt = fmt if fmt != "auto" else self._current_format
            if path.lower().endswith(".ssync.json"):
                from core.sync_store import save_session as save_project_file

                save_project_file(
                    self._project_name or "project",
                    self._timeline_name or "timeline",
                    lines=self._parsed_lines,
                    import_path=self._import_path,
                    fmt=use_fmt,
                    is_synced=self._is_synced,
                    sync_mode=self._sync_mode,
                )
                # Also write to chosen path
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "schema_version": 1,
                            "format": use_fmt,
                            "sync_mode": self._sync_mode,
                            "is_synced": self._is_synced,
                            "lines": self._parsed_lines,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                self.status_changed.emit(
                    f"Project saved (links preserved): {os.path.basename(path)}",
                    "#9ccfd8",
                )
                self._persist_session()
                return

            # Merge editor text into lines — keeps all link metadata
            self._parsed_lines = merge_text_preserving_links(self._parsed_lines, content)
            self._current_script = TextParser.to_text(self._parsed_lines, "txt")

            if self._parsed_lines and use_fmt != "txt":
                out = TextParser.to_text(self._parsed_lines, use_fmt)
            else:
                out = self._current_script

            with open(path, "w", encoding="utf-8") as f:
                f.write(out)

            self._import_path = path
            save_sidecar(
                path,
                lines=self._parsed_lines,
                fmt=use_fmt,
                sync_mode=self._sync_mode,
                is_synced=self._is_synced,
            )
            self._emit_lines()
            self._persist_session()
            self.status_changed.emit(
                f"Saved + links: {os.path.basename(path)}", "#9ccfd8"
            )
            log.info("Saved script with sidecar: %s", path)
        except Exception as e:
            log.error("Save error: %s", e)
            self.status_changed.emit(f"Save failed: {e}", "#eb6f92")

    # ── Sync ──────────────────────────────────────────────────────────────────

    @Slot(str, str, str, str)
    def sync_timeline(self, content="", fmt="auto", mode="linear", options_json="{}"):
        log.info("Syncing with timeline (mode=%s)", mode)

        if not self._is_connected or not self._resolve:
            self.sync_completed.emit(False, "Not connected to Resolve")
            self.status_changed.emit("Sync failed: not connected", "#eb6f92")
            return

        if not self._timeline:
            self.sync_completed.emit(False, "No timeline open in Resolve")
            self.status_changed.emit("Sync failed: open a timeline in Edit page", "#eb6f92")
            return

        text = content.strip() or self._current_script.strip()
        if not text:
            self.sync_completed.emit(False, "No script loaded")
            self.status_changed.emit("Sync failed: no script", "#eb6f92")
            return

        self._sync_mode = mode if mode in ("linear", "clips") else "linear"
        sync_opts = self._parse_sync_options(options_json)

        try:
            self._refresh_context()
            if self._parsed_lines and content.strip():
                self._parsed_lines = merge_text_preserving_links(
                    self._parsed_lines, content
                )
            elif content.strip() and not self._parsed_lines:
                use_fmt = fmt if fmt != "auto" else self._current_format
                self._parsed_lines = TextParser.parse(content, use_fmt, self._fps)
            elif not self._parsed_lines:
                self.sync_completed.emit(False, "No script loaded")
                self.status_changed.emit("Sync failed: no script", "#eb6f92")
                return

            linked_before = sum(
                1 for l in self._parsed_lines if TextParser.is_manually_linked(l)
            )

            self._run_auto_sync(mode=self._sync_mode, sync_opts=sync_opts)

            self._is_synced = any(
                l.get("start_tc") or l.get("link_id") for l in self._parsed_lines
            )
            self._last_active_line = -1
            self._current_script = TextParser.to_text(self._parsed_lines, "txt")

            self._emit_lines()
            self.update_timeline_info()
            self.refresh_clips()
            self._persist_session()
            self._save_sidecar_if_path()

            linked_after = sum(
                1 for l in self._parsed_lines if TextParser.is_manually_linked(l)
            )
            msg = f"Auto-sync ({self._sync_mode}): {len(self._parsed_lines)} lines"
            if linked_before:
                msg += f" — {linked_after}/{linked_before} manual links kept"
            self.sync_completed.emit(True, msg)
            self.status_changed.emit(msg, "#9ccfd8")
            log.info(msg)

        except Exception as e:
            log.error("Sync error: %s", e)
            self.sync_completed.emit(False, str(e))
            self.status_changed.emit(f"Sync failed: {e}", "#eb6f92")

    @Slot(str, str, str, str, str)
    def sync_timeline_range(
        self,
        content="",
        mode="linear",
        start_index="0",
        end_index="0",
        options_json="{}",
    ):
        """Re-run auto-sync only between first/last mark indices (inclusive)."""
        if not self._is_connected or not self._timeline:
            self.sync_completed.emit(False, "Not connected or no timeline")
            return
        try:
            start_idx = max(0, int(start_index))
            end_idx = max(start_idx, int(end_index))
            sync_opts = self._parse_sync_options(options_json)
            self._sync_mode = mode if mode in ("linear", "clips") else "linear"

            if content.strip() and self._parsed_lines:
                self._parsed_lines = merge_text_preserving_links(
                    self._parsed_lines, content
                )

            self._refresh_context()
            self._run_auto_sync(
                mode=self._sync_mode,
                sync_opts=sync_opts,
                start_idx=start_idx,
                end_idx=end_idx,
            )
            self._is_synced = any(
                l.get("start_tc") or l.get("link_id") for l in self._parsed_lines
            )
            self._current_script = TextParser.to_text(self._parsed_lines, "txt")
            self._emit_lines()
            self._persist_session()
            self._save_sidecar_if_path()
            msg = f"Range sync L{start_idx + 1}–L{end_idx + 1} ({self._sync_mode})"
            self.sync_completed.emit(True, msg)
            self.status_changed.emit(msg, "#9ccfd8")
        except Exception as e:
            log.error("Range sync error: %s", e)
            self.sync_completed.emit(False, str(e))
            self.status_changed.emit(f"Range sync failed: {e}", "#eb6f92")

    # ── Line editing ──────────────────────────────────────────────────────────

    @Slot(int, str)
    def update_line(self, index: int, text: str):
        if index < 0 or index >= len(self._parsed_lines):
            return
        self._parsed_lines[index]["text"] = text
        self._current_script = TextParser.to_text(self._parsed_lines, "txt")
        self._persist_session()
        self._save_sidecar_if_path()

    @Slot(str)
    def sync_lines_text(self, lines_json: str):
        """Batch sync from editor without re-render storm."""
        try:
            pairs = json.loads(lines_json)
            for index, text in pairs:
                idx = int(index)
                if 0 <= idx < len(self._parsed_lines):
                    self._parsed_lines[idx]["text"] = str(text)
            self._current_script = TextParser.to_text(self._parsed_lines, "txt")
            self._persist_session()
            self._save_sidecar_if_path()
        except Exception as e:
            log.debug("sync_lines_text: %s", e)

    @Slot(str)
    def sync_lines_from_ui(self, lines_json: str):
        """Full editor sync (insert/delete/text) — preserves link fields from payload."""
        try:
            incoming = json.loads(lines_json)
            if not isinstance(incoming, list):
                return
            merged: list[dict] = []
            for i, row in enumerate(incoming):
                item = dict(row) if isinstance(row, dict) else {"text": str(row)}
                item["line_number"] = i + 1
                merged.append(item)
            self._parsed_lines = merged
            self._current_script = TextParser.to_text(self._parsed_lines, "txt")
            self._is_synced = any(
                l.get("start_tc") or l.get("link_id") for l in self._parsed_lines
            )
            self._persist_session()
            self._save_sidecar_if_path()
        except Exception as e:
            log.debug("sync_lines_from_ui: %s", e)

    @Slot()
    def new_script(self):
        """Blank screenplay-style script for writing from scratch."""
        self._parsed_lines = [
            {"text": "INT. LOCACAO - DIA", "line_number": 1},
            {"text": "", "line_number": 2},
            {"text": "PERSONAGEM", "line_number": 3},
            {"text": "(escreva o dialogo aqui)", "line_number": 4},
            {"text": "", "line_number": 5},
        ]
        self._current_script = TextParser.to_text(self._parsed_lines, "txt")
        self._current_format = "txt"
        self._import_path = ""
        self._is_synced = False
        self._last_active_line = -1
        self.script_loaded.emit(self._current_script)
        self._emit_lines()
        self._persist_session()
        self.status_changed.emit("New script — write and link clips", "#9ccfd8")

    @Slot(int, str)
    def insert_line(self, after_index: int, text: str = ""):
        idx = max(-1, min(after_index, len(self._parsed_lines) - 1))
        insert_at = idx + 1
        self._parsed_lines.insert(insert_at, {"text": text, "line_number": insert_at + 1})
        for i in range(insert_at, len(self._parsed_lines)):
            self._parsed_lines[i]["line_number"] = i + 1
        self._current_script = TextParser.to_text(self._parsed_lines, "txt")
        self._persist_session()
        self._save_sidecar_if_path()

    @Slot(int)
    def delete_line(self, index: int):
        if index < 0 or index >= len(self._parsed_lines):
            return
        if len(self._parsed_lines) <= 1:
            self.status_changed.emit("Cannot delete last line", "#eb6f92")
            return
        self._parsed_lines.pop(index)
        for i, line in enumerate(self._parsed_lines):
            line["line_number"] = i + 1
        self._current_script = TextParser.to_text(self._parsed_lines, "txt")
        self._emit_lines()
        self._persist_session()
        self._save_sidecar_if_path()

    # ── Manual linking (AVID ScriptSync style) ────────────────────────────────

    @Slot(str, str)
    def link_lines_to_clip(self, indices_json: str, clip_json: str):
        """Link selected script lines to a timeline clip."""
        if not self._resolve or not self._timeline:
            self.status_changed.emit("Link failed: no timeline", "#eb6f92")
            return
        try:
            indices = json.loads(indices_json)
            clip = json.loads(clip_json)
            self._push_link_undo()
            self._refresh_context()
            from core.script_link import apply_clip_to_lines

            preview = " | ".join(
                self._parsed_lines[i]["text"][:40]
                for i in sorted(indices)
                if 0 <= i < len(self._parsed_lines)
            )[:120]
            apply_clip_to_lines(self._parsed_lines, indices, clip, self._fps)
            if self._cached_clips:
                reconcile_clip_indices(self._parsed_lines, self._cached_clips)
            if clip.get("clip_index") is not None:
                for idx in indices:
                    if 0 <= idx < len(self._parsed_lines):
                        self._parsed_lines[idx]["clip_end_frame"] = clip.get("end_frame")
            self._bridge.add_marker(
                clip["start_frame"],
                f"SS: {clip.get('name', 'Clip')[:30]}",
                note=preview,
                color="Green",
                custom_data=f"sscriptsync|clip|{clip.get('clip_index', 0)}",
            )
            self._is_synced = True
            self._emit_lines()
            self._persist_session()
            self._save_sidecar_if_path()
            self.status_changed.emit(
                f"Linked {len(indices)} line(s) → {clip.get('track_label', 'V1')} {clip.get('name', 'Clip')}",
                "#4ade80",
            )
            QTimer.singleShot(300, lambda c=clip: self.request_clip_thumbnail(json.dumps(c)))
            log.info("Linked lines %s to clip %s", indices, clip.get("name"))
        except Exception as e:
            log.error("link_lines_to_clip: %s", e)
            self.status_changed.emit(f"Link failed: {e}", "#eb6f92")

    @Slot(str)
    def link_lines_to_playhead(self, indices_json: str):
        """Link lines to current playhead — creates marker if no clip."""
        if not self._resolve or not self._timeline:
            self.status_changed.emit("Link failed: no timeline", "#eb6f92")
            return
        try:
            indices = json.loads(indices_json)
            self._push_link_undo()
            self._refresh_context()
            tc = self._bridge.get_current_timecode()
            if not tc:
                self.status_changed.emit("Link failed: no playhead", "#eb6f92")
                return
            frame = Timecode.timecode_to_frames(tc, self._fps)
            from core.script_link import apply_marker_to_lines

            preview = " | ".join(
                self._parsed_lines[i]["text"][:40]
                for i in sorted(indices)
                if 0 <= i < len(self._parsed_lines)
            )[:120]
            apply_marker_to_lines(self._parsed_lines, indices, frame, self._fps)
            self._bridge.add_marker(
                frame,
                "SS: Script",
                note=preview,
                color="Yellow",
                custom_data="sscriptsync|marker",
            )
            self._is_synced = True
            self._emit_lines()
            self._persist_session()
            self._save_sidecar_if_path()
            self.status_changed.emit(f"Linked {len(indices)} line(s) → marker @ {tc}", "#facc15")
        except Exception as e:
            log.error("link_lines_to_playhead: %s", e)
            self.status_changed.emit(f"Link failed: {e}", "#eb6f92")

    @Slot(str)
    def unlink_lines(self, indices_json: str):
        try:
            indices = json.loads(indices_json)
            self._push_link_undo()
            from core.script_link import unlink_lines as _unlink

            _unlink(self._parsed_lines, indices)
            self._is_synced = any(l.get("start_tc") for l in self._parsed_lines)
            self._emit_lines()
            self._persist_session()
            self._save_sidecar_if_path()
            self.status_changed.emit(f"Unlinked {len(indices)} line(s)", "#6e6a86")
        except Exception as e:
            log.error("unlink_lines: %s", e)

    # ── Click-to-jump ─────────────────────────────────────────────────────────

    @Slot(str)
    def jump_to_timecode(self, timecode: str):
        log.info("Jumping to timecode: %s", timecode)

        if not self._is_connected or not self._timeline:
            self.status_changed.emit("Cannot jump: not connected", "#eb6f92")
            return

        if not Timecode.is_valid_timecode(timecode):
            self.status_changed.emit(f"Invalid timecode: {timecode}", "#eb6f92")
            return

        try:
            self._refresh_context(force=True)
            if self._bridge.set_playhead(timecode):
                self.timecode_changed.emit(timecode)
                idx = Timecode.find_line_at_playhead(
                    self._parsed_lines, timecode, self._fps, self._cached_clips
                )
                if idx >= 0:
                    self._last_active_line = idx
                    self.active_line_changed.emit(idx)
                self.status_changed.emit(f"Jumped to {timecode}", "#9ccfd8")
            else:
                self.status_changed.emit(
                    "Jump may have failed — use Edit/Cut/Color page", "#f6c177"
                )
        except Exception as e:
            log.error("Jump error: %s", e)
            self.status_changed.emit(f"Jump failed: {e}", "#eb6f92")

    @Slot(int)
    def jump_to_line(self, index: int):
        if index < 0 or index >= len(self._parsed_lines):
            return
        line = self._parsed_lines[index]
        tc = line.get("start_tc") or line.get("timecode")
        if tc:
            self.jump_to_timecode(tc)
        else:
            self.status_changed.emit("Line not synced — run Sync Timeline first", "#f6c177")

    @Slot(str)
    def jump_to_clip(self, start_tc: str):
        """Jump to clip start timecode from clips panel (playhead only)."""
        if start_tc:
            self.jump_to_timecode(start_tc)

    @Slot(str)
    def focus_clip(self, clip_json: str):
        """Jump + highlight clip on Resolve timeline (marks + selection if API allows)."""
        if not self._is_connected or not self._timeline:
            self.status_changed.emit("Cannot focus: not connected", "#eb6f92")
            return
        try:
            clip = json.loads(clip_json)
            self._refresh_context(force=True)
            result = self._bridge.focus_clip(clip)
            tc = clip.get("start_tc")
            if tc:
                self.timecode_changed.emit(tc)
                idx = Timecode.find_line_at_playhead(
                    self._parsed_lines, tc, self._fps, self._cached_clips
                )
                if idx >= 0:
                    self._last_active_line = idx
                    self.active_line_changed.emit(idx)
            label = clip.get("track_label") or "Clip"
            name = clip.get("name") or "Clip"
            parts = [f"Focused {label} · {name[:28]}"]
            if result.get("marks"):
                parts.append("range marked")
            elif result.get("playhead"):
                parts.append("playhead moved")
            if not result.get("playhead") and not result.get("marks"):
                self.status_changed.emit(
                    "Focus failed — use Edit/Cut/Color page", "#f6c177"
                )
                return
            self.status_changed.emit(" · ".join(parts), "#9ccfd8")
        except Exception as e:
            log.error("focus_clip: %s", e)
            self.status_changed.emit(f"Focus failed: {e}", "#eb6f92")

    @Slot()
    def get_timeline_info(self):
        if self._timeline:
            self.update_timeline_info()
        elif self._ctx_cache:
            self._emit_timeline_info()
        else:
            self.timeline_info.emit(json.dumps({}))

    # ── Undo / notes / export / SRT ─────────────────────────────────────────

    @Slot()
    def undo_link(self):
        if not self._link_undo:
            self.status_changed.emit("Nothing to undo", "#6e6a86")
            return
        self._link_redo.append(copy.deepcopy(self._parsed_lines))
        self._restore_link_state(self._link_undo.pop())
        self.status_changed.emit("Undo link", "#9ccfd8")

    @Slot()
    def redo_link(self):
        if not self._link_redo:
            self.status_changed.emit("Nothing to redo", "#6e6a86")
            return
        self._link_undo.append(copy.deepcopy(self._parsed_lines))
        self._restore_link_state(self._link_redo.pop())
        self.status_changed.emit("Redo link", "#9ccfd8")

    @Slot(int, str)
    def set_line_note(self, index: int, note: str):
        if index < 0 or index >= len(self._parsed_lines):
            return
        self._parsed_lines[index]["note"] = note.strip()
        self._emit_lines()
        self._persist_session()
        self._save_sidecar_if_path()

    @Slot(int, str)
    def set_sync_node_label(self, index: int, label: str):
        """Custom display label for the sync node / primary clip link on a line."""
        if index < 0 or index >= len(self._parsed_lines):
            return
        from core.link_model import get_line_links, set_line_links

        line = self._parsed_lines[index]
        links = get_line_links(line)
        if not links:
            return
        primary = next((l for l in links if l.get("link_type") == "clip"), links[0])
        text = label.strip()
        if text:
            primary["link_label"] = text
        else:
            primary.pop("link_label", None)
        set_line_links(line, links)
        self._emit_lines()
        self._persist_session()
        self._save_sidecar_if_path()
        self.status_changed.emit(
            f"Sync renomeado: {text or primary.get('clip_name', 'Clip')[:32]}",
            "#9ccfd8",
        )

    @Slot(str)
    def export_bundle(self, content: str = ""):
        if not self._parsed_lines:
            self.status_changed.emit("Export failed: no script", "#eb6f92")
            return
        default = self._import_path or "roteiro.txt"
        path, _ = QFileDialog.getSaveFileName(
            self._win,
            "Export script + links",
            default,
            "Text (*.txt);;All Files (*.*)",
        )
        if not path:
            return
        try:
            script_text = content.strip() or TextParser.to_text(self._parsed_lines, "txt")
            paths = export_bundle(
                path,
                script_text=script_text,
                lines=self._parsed_lines,
                fmt=self._current_format,
                sync_mode=self._sync_mode,
                is_synced=self._is_synced,
                fps=self._fps,
                project_name=self._project_name,
                timeline_name=self._timeline_name,
            )
            self._import_path = paths["txt"]
            self.status_changed.emit(
                f"Exported: {os.path.basename(paths['txt'])} + sidecar + EDL",
                "#9ccfd8",
            )
            log.info("Export bundle: %s", paths)
        except Exception as e:
            log.error("Export error: %s", e)
            self.status_changed.emit(f"Export failed: {e}", "#eb6f92")

    @Slot()
    def import_srt_map(self):
        """Import external SRT/Rev and map cues onto script lines."""
        if not self._parsed_lines:
            self.status_changed.emit("Load a script first", "#eb6f92")
            return
        path, _ = QFileDialog.getOpenFileName(
            self._win,
            "Import SRT / Rev transcript",
            "",
            "Subtitles (*.srt);;All Files (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            srt_lines = TextParser.parse_srt(content, self._fps)
            if not srt_lines:
                self.status_changed.emit("SRT empty or invalid", "#eb6f92")
                return
            self._push_link_undo()
            self._parsed_lines = TextParser.associate_srt_to_lines(
                self._parsed_lines, srt_lines, self._fps, preserve_manual=True
            )
            mapped = sum(1 for l in self._parsed_lines if l.get("srt_source"))
            self._is_synced = any(
                l.get("start_tc") or l.get("link_id") for l in self._parsed_lines
            )
            self._current_script = TextParser.to_text(self._parsed_lines, "txt")
            self._emit_lines()
            self._persist_session()
            self._save_sidecar_if_path()
            self.status_changed.emit(
                f"SRT mapped: {mapped} line(s) from {os.path.basename(path)}",
                "#9ccfd8",
            )
        except Exception as e:
            log.error("SRT import error: %s", e)
            self.status_changed.emit(f"SRT import failed: {e}", "#eb6f92")

    @Slot()
    def clear_script(self):
        self._parsed_lines = []
        self._current_script = ""
        self._is_synced = False
        self._last_active_line = -1
        self._emit_lines()
        self.script_loaded.emit("")
        self.active_line_changed.emit(-1)
        self._persist_session()
        self.status_changed.emit("Editor cleared", "#6e6a86")
