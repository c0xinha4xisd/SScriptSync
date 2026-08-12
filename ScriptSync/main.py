"""
SScriptSync_v1 - DaVinci Resolve Text Editor with Timeline Sync
Main entry point - PySide6 + QWebEngine (MFlow architecture)
"""
import sys
import os
import traceback
import logging
import faulthandler

APP_NAME = "SScriptSync_v1"
_IS_MP_CHILD = __name__ == "__mp_main__"

_LOG_DIR = os.path.join(os.path.expanduser("~"), ".sscriptsync_v1")
os.makedirs(_LOG_DIR, exist_ok=True)
_CRASH_LOG = os.path.join(_LOG_DIR, "crash.log")
if not _IS_MP_CHILD:
    _crash_f = open(_CRASH_LOG, "w", encoding="utf-8")
    faulthandler.enable(_crash_f)

import builtins
from collections import OrderedDict as _OD
if not hasattr(builtins, "OrderedDict"):
    builtins.OrderedDict = _OD

_LOG_PATH = os.path.join(_LOG_DIR, "sscriptsync_v1.log")
if _IS_MP_CHILD:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [PID:%(process)d] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(_LOG_DIR, f"probe_{os.getpid()}.log"), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [PID:%(process)d] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(_LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
log = logging.getLogger("sscriptsync_v1")
if not _IS_MP_CHILD:
    log.info("%s starting — Python %s — %s", APP_NAME, sys.version.split()[0], sys.platform)

_WIN_APP_ID = "Blackmagic.SScriptSync.v1.Editor"


def _win_set_app_user_model_id():
    """Own taskbar entry + normal Alt+Tab / foreground on Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_WIN_APP_ID)
    except Exception as e:
        log.debug("AppUserModelID: %s", e)


def _win_bring_window_to_front(window):
    """Raise window — never use AttachThreadInput (deadlocks with Resolve during playback)."""
    window.showNormal()
    window.raise_()
    window.activateWindow()
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(window.winId())
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    except Exception as e:
        log.debug("bring_to_front: %s", e)


def _excepthook(exc_type, exc_value, exc_tb):
    log.error("Uncaught exception:\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    if sys.platform == "win32":
        input("\nPress Enter to close...")
sys.excepthook = _excepthook

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _setup_env():
    if sys.platform == "win32":
        parts = os.environ.get("PATH", "").split(os.pathsep)
        os.environ["PATH"] = os.pathsep.join(p for p in parts if "WindowsApps" not in p)
        for rdir in [
            r"C:\Program Files\Blackmagic Design\DaVinci Resolve",
            r"C:\Program Files (x86)\Blackmagic Design\DaVinci Resolve",
        ]:
            if os.path.isdir(rdir) and rdir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = rdir + os.pathsep + os.environ["PATH"]
                try:
                    os.add_dll_directory(rdir)
                except (AttributeError, OSError):
                    pass
    elif sys.platform == "darwin":
        resolve_lib = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries"
        if os.path.isdir(resolve_lib):
            os.environ.setdefault("DYLD_LIBRARY_PATH", resolve_lib)
    else:
        for ldir in ["/opt/resolve/libs", "/opt/resolve/lib"]:
            if os.path.isdir(ldir):
                os.environ.setdefault("LD_LIBRARY_PATH", ldir)


_setup_env()

try:
    from PySide6.QtWidgets import QApplication, QMainWindow
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineScript
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtCore import Qt, QUrl, QFile, QIODevice, QTimer
    from PySide6.QtGui import QColor
except ImportError as e:
    log.error("PySide6 not installed: %s", e)
    if sys.platform == "win32":
        input("\nPySide6 not found. Run install.py first. Press Enter...")
    sys.exit(1)

APP_HTML = os.path.join(HERE, "ui", "app.html")


def _resource(relative):
    base = getattr(sys, "_MEIPASS", HERE)
    return os.path.join(base, relative)


def _inject_qwebchannel(page):
    """Qt 6.7+ blocks qrc:// from file:// pages — inject qwebchannel.js manually."""
    try:
        qwc = QFile(":/qtwebchannel/qwebchannel.js")
        if not qwc.open(QIODevice.OpenModeFlag.ReadOnly):
            log.warning("Could not read qrc qwebchannel.js — UI may not connect")
            return
        js = bytes(qwc.readAll()).decode("utf-8", errors="replace")
        qwc.close()
        script = QWebEngineScript()
        script.setName("__qwebchannel_inject__")
        script.setSourceCode(js)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        page.scripts().insert(script)
        log.info("qwebchannel.js injected via QWebEngineScript")
    except Exception as e:
        log.warning("qwebchannel injection failed: %s", e)


def _bootstrap_resolve(comp=None, resolve=None):
    """
    MFlow-style Resolve bootstrap (see core/resolve_connection.py):
      1. probe in separate OS process (never hang the app)
      2. get_resolve() on Qt main thread (scriptapp used only from main thread after)
    Requires Resolve Studio + External scripting = Local.
    Ref: docs/RESOLVE_STUDIO_21_API.md, davinci-resolve-mcp install docs.
    """
    if resolve or comp:
        return resolve, comp
    try:
        from core.resolve_connection import (
            probe_resolve_connection,
            get_resolve,
            get_comp,
        )
        log.info("Attempting Resolve connection (probe + main-thread scriptapp)…")
        if probe_resolve_connection(timeout=6.0):
            resolve = get_resolve()
            if resolve:
                comp = get_comp(resolve)
                log.info("Connected to Resolve Studio")
            else:
                log.warning("Probe OK but scriptapp returned None — check External scripting = Local")
        else:
            log.info("Resolve not available — standalone mode")
    except Exception as e:
        log.warning("Resolve connection error: %s", e)
        resolve = None
    return resolve, comp


class SScriptSyncWindow(QMainWindow):
    def __init__(self, resolve=None, comp=None, parent=None):
        super().__init__(parent)
        self._resolve = resolve
        self._comp = comp
        self._backend = None
        self._ui_busy_timer = QTimer(self)
        self._ui_busy_timer.setSingleShot(True)
        self._ui_busy_timer.timeout.connect(self._clear_ui_busy)

        self.setWindowTitle("SScriptSync v1 - DaVinci Resolve Text Editor")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setStyleSheet("QMainWindow { background-color: #0e0e12; }")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)

        self.webview = QWebEngineView()
        self.webview.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setCentralWidget(self.webview)

        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)

        self.webview.page().setBackgroundColor(QColor("#0e0e12"))

        self.channel = QWebChannel()
        from ui.backend import Backend
        self._backend = Backend(self, resolve=resolve, comp=comp)
        self.channel.registerObject("backend", self._backend)
        self.webview.page().setWebChannel(self.channel)

        _inject_qwebchannel(self.webview.page())

        html_path = _resource("ui/app.html")
        if os.path.isfile(html_path):
            self.webview.load(QUrl.fromLocalFile(html_path))
            self.webview.loadFinished.connect(self._on_page_ready)
            log.info("Loading UI: %s", html_path)
        else:
            log.error("HTML not found: %s", html_path)

    def _set_ui_busy(self):
        try:
            self.webview.page().runJavaScript("window.__uiBusy=true;")
        except Exception:
            pass
        self._ui_busy_timer.start(220)

    def _clear_ui_busy(self):
        try:
            self.webview.page().runJavaScript(
                "window.__uiBusy=false;"
                "if(typeof scheduleLayoutUpdate==='function')scheduleLayoutUpdate();"
            )
        except Exception:
            pass

    def moveEvent(self, event):
        if not getattr(self._backend, "_playback_active", False):
            self._set_ui_busy()
        super().moveEvent(event)

    def resizeEvent(self, event):
        if not getattr(self._backend, "_playback_active", False):
            self._set_ui_busy()
        super().resizeEvent(event)

    def _on_page_ready(self, ok):
        log.info("UI loadFinished ok=%s", ok)

    def closeEvent(self, event):
        try:
            if self._backend and getattr(self._backend, "_watcher", None):
                self._backend._watcher.stop()
        except Exception:
            pass
        super().closeEvent(event)


def main(comp=None, resolve=None):
    """Entry point. comp/resolve may be injected by SScriptSync_v1_Free.py."""
    _win_set_app_user_model_id()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationDisplayName("SScriptSync v1")

    resolve, comp = _bootstrap_resolve(comp=comp, resolve=resolve)

    window = SScriptSyncWindow(resolve=resolve, comp=comp)
    window.show()
    log.info("%s window shown (resolve=%s)", APP_NAME, bool(resolve))
    return app.exec()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(main())
