"""
Resolve connection for SScriptSync_v1.
Based on MFlow's resolve_connection.py (probe + timeout + watcher).
"""
import importlib
import importlib.util
import logging
import os
import sys
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal

_LOG = "sscriptsync_v1"


def _run_with_timeout(fn, args=(), timeout=6.0, name="worker"):
    log = logging.getLogger(_LOG)
    box = {"value": None, "error": None, "done": False}

    def _worker():
        try:
            box["value"] = fn(*args)
        except Exception as e:
            box["error"] = e
        finally:
            box["done"] = True

    try:
        t = threading.Thread(target=_worker, name=f"SScriptSync-{name}", daemon=True)
        t.start()
        t.join(timeout)
    except Exception as e:
        log.warning("[%s] Could not run with timeout guard: %s", name, e)
        return None, None, True

    if not box["done"]:
        log.warning("[%s] Timed out after %.1fs", name, timeout)
        return None, None, True
    if box["error"] is not None:
        log.warning("[%s] Raised: %s", name, box["error"])
        return None, box["error"], False
    return box["value"], None, False


def _diagnose_scriptapp_failure(log, dvr_module, fsp):
    log.warning("[get_resolve] ── Diagnostics ──")
    try:
        import struct
        bits = struct.calcsize("P") * 8
        log.warning("[get_resolve] Python: %s (%d-bit) at %s", sys.version.split()[0], bits, sys.executable)
    except Exception as e:
        log.warning("[get_resolve] Python bitness: %s", e)

    if dvr_module is not None:
        log.warning("[get_resolve] DaVinciResolveScript: %s", getattr(dvr_module, "__file__", "?"))
    else:
        log.warning("[get_resolve] DaVinciResolveScript: not imported")

    if fsp and os.path.isfile(fsp):
        log.warning("[get_resolve] fusionscript.dll: %s", fsp)
    else:
        log.warning("[get_resolve] fusionscript.dll not found: %s", fsp)

    for var in ("RESOLVE_SCRIPT_API", "RESOLVE_SCRIPT_LIB", "PYTHONPATH"):
        log.warning("[get_resolve] env %s = %s", var, os.environ.get(var, "(unset)"))

    if sys.platform == "win32":
        try:
            import subprocess
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Resolve.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            log.warning("[get_resolve] Resolve.exe running: %s", "Resolve.exe" in (out.stdout or ""))
        except Exception as e:
            log.warning("[get_resolve] tasklist failed: %s", e)


def get_resolve(custom_path: str = ""):
    log = logging.getLogger(_LOG)
    resolve_dirs = []

    if sys.platform == "win32":
        parts = os.environ.get("PATH", "").split(os.pathsep)
        os.environ["PATH"] = os.pathsep.join(
            p for p in parts if "WindowsApps" not in p and "windowsapps" not in p.lower()
        )
        resolve_dirs = [
            r"C:\Program Files\Blackmagic Design\DaVinci Resolve",
            r"C:\Program Files (x86)\Blackmagic Design\DaVinci Resolve",
        ]
        if custom_path and os.path.isdir(custom_path):
            resolve_dirs.insert(0, custom_path)
        for rdir in resolve_dirs:
            if os.path.isdir(rdir):
                log.info("[get_resolve] Resolve dir: %s", rdir)
                if rdir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = rdir + os.pathsep + os.environ["PATH"]
                try:
                    os.add_dll_directory(rdir)
                except (AttributeError, OSError):
                    pass
                break

    import builtins
    from collections import OrderedDict as _OD
    if not hasattr(builtins, "OrderedDict"):
        builtins.OrderedDict = _OD

    for _k in ("DaVinciResolveScript", "fusionscript"):
        sys.modules.pop(_k, None)

    for p in [
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting",
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
    ]:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)

    _dvr_ref = None
    try:
        import DaVinciResolveScript as _dvr
        _dvr_ref = _dvr
        log.info("[get_resolve] DaVinciResolveScript imported")
        t0 = time.monotonic()
        r = _dvr.scriptapp("Resolve")
        elapsed = time.monotonic() - t0
        if r:
            log.info("[get_resolve] scriptapp OK in %.2fs", elapsed)
            return r
        log.warning(
            "[get_resolve] scriptapp returned None (%.2fs). "
            "Set External scripting using = Local in Resolve Preferences.",
            elapsed,
        )
    except ImportError as e:
        log.warning("[get_resolve] DaVinciResolveScript import failed: %s", e)
    except Exception as e:
        log.error("[get_resolve] scriptapp error: %s", e, exc_info=True)

    fsp = None
    if sys.platform == "win32":
        for rdir in resolve_dirs:
            if os.path.isdir(rdir):
                candidate = os.path.join(rdir, "fusionscript.dll")
                if os.path.isfile(candidate):
                    fsp = candidate
                    break
    if fsp:
        try:
            spec = importlib.util.spec_from_file_location("fusionscript", fsp)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                r = mod.scriptapp("Resolve")
                if r:
                    log.info("[get_resolve] fusionscript fallback OK")
                    return r
        except Exception as e:
            log.warning("[get_resolve] fusionscript fallback failed: %s", e)

    _diagnose_scriptapp_failure(log, _dvr_ref, fsp)
    return None


def get_comp(resolve):
    try:
        f = resolve.Fusion()
        if not f:
            return None
        comp = getattr(f, "CurrentComp", None)
        if comp is None:
            comp = f.GetCurrentComp()
        return comp
    except Exception:
        return None


def get_resolve_with_timeout(custom_path: str = "", timeout: float = 6.0):
    """Startup-only bootstrap guard (MFlow pattern). Ongoing API calls stay on main thread."""
    value, _err, timed_out = _run_with_timeout(
        get_resolve, args=(custom_path,), timeout=timeout, name="get_resolve"
    )
    if timed_out:
        logging.getLogger(_LOG).warning("[get_resolve] timeout — standalone mode")
    return value


def get_comp_with_timeout(resolve, timeout: float = 4.0):
    value, _err, _timed_out = _run_with_timeout(
        get_comp, args=(resolve,), timeout=timeout, name="get_comp"
    )
    return value


def _probe_worker(custom_path, queue):
    try:
        queue.put(("ok", bool(get_resolve(custom_path))))
    except Exception as e:
        queue.put(("error", str(e)))


def probe_resolve_connection(custom_path: str = "", timeout: float = 6.0) -> bool:
    log = logging.getLogger(_LOG)
    try:
        import multiprocessing

        ctx = multiprocessing.get_context("spawn")
        q = ctx.Queue()
        p = ctx.Process(target=_probe_worker, args=(custom_path, q), daemon=True)
        p.start()
        p.join(timeout)
        if p.is_alive():
            log.warning("[get_resolve] probe hung — killing")
            try:
                p.terminate()
                p.join(2.0)
                if p.is_alive():
                    p.kill()
                    p.join(1.0)
            except Exception:
                pass
            return False
        if not q.empty():
            kind, val = q.get()
            return bool(val) if kind == "ok" else False
        return False
    except Exception as e:
        log.warning("[get_resolve] probe unavailable: %s", e)
        return False


class ResolveWatcher(QObject):
    timeline_changed = Signal(str)
    timecode_changed = Signal(str)
    disconnected = Signal()

    def __init__(self, resolve, parent=None):
        super().__init__(parent)
        self._resolve = resolve
        self._last_timecode = ""
        self._last_timeline_name = ""
        self._poll_fail_count = 0
        self._playback_mode = False
        self._tc_timer = QTimer(self)
        self._tc_timer.timeout.connect(self._poll_timecode)

    def start(self):
        self._tc_timer.start(200)

    def stop(self):
        self._tc_timer.stop()

    def set_playback_mode(self, active: bool):
        active = bool(active)
        if self._playback_mode == active:
            return
        self._playback_mode = active
        if active:
            self._tc_timer.stop()
        elif not self._tc_timer.isActive():
            self._tc_timer.start(200)

    def _poll_timecode(self):
        if self._playback_mode or not self._resolve:
            return
        try:
            pm_fn = getattr(self._resolve, "GetProjectManager", None)
            if not callable(pm_fn):
                return
            pm = pm_fn()
            project = pm.GetCurrentProject() if pm else None
            timeline = project.GetCurrentTimeline() if project else None
            if not timeline:
                return
            tc = timeline.GetCurrentTimecode()
            if tc and tc != self._last_timecode:
                self._last_timecode = tc
                self.timecode_changed.emit(tc)
            name = timeline.GetName() or ""
            if name and name != self._last_timeline_name:
                self._last_timeline_name = name
                self.timeline_changed.emit(name)
            self._poll_fail_count = 0
        except Exception as e:
            logging.getLogger(_LOG).debug("[Watcher] poll error: %s", e)
            self._poll_fail_count += 1
            if self._poll_fail_count >= 8:
                self.disconnected.emit()
                self.stop()
