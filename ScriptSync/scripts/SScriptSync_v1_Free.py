# SScriptSync_v1_Free.py
# Bridge for DaVinci Resolve FREE.
# In Resolve (Fusion page): Scripts > Comp > SScriptSync_v1_Free
import sys, os, platform

APP_NAME = "SScriptSync_v1"
PATH_TXT = "sscriptsync_v1_path.txt"


def _find_app_dir():
    PLAT = platform.system()
    here = ""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        try:
            import inspect
            here = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        except Exception:
            pass
    if here:
        txt = os.path.join(here, PATH_TXT)
        if os.path.isfile(txt):
            p = open(txt, encoding="utf-8").read().strip()
            if os.path.isfile(os.path.join(p, "main.py")):
                return p
    candidates = {
        "Windows": [os.path.join(os.environ.get("LOCALAPPDATA", ""), APP_NAME)],
        "Darwin": [os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")],
        "Linux": [os.path.expanduser(f"~/.local/share/{APP_NAME}")],
    }.get(PLAT, [])
    for c in candidates:
        if os.path.isfile(os.path.join(c, "main.py")):
            return c
    if here and os.path.isfile(os.path.join(here, "main.py")):
        return here
    return None


app_dir = _find_app_dir()
if app_dir is None:
    print(f"[{APP_NAME}] ERRO: não encontrado. Execute install.py primeiro.")
else:
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    try:
        _fusion = app  # noqa: F821
        _comp = _fusion.CurrentComp
        _resolve = None
        try:
            _resolve = _fusion.GetResolve()
        except Exception:
            pass

        from PySide6.QtWidgets import QApplication

        _qt = QApplication.instance() or QApplication(sys.argv)

        from main import main as run_app

        run_app(comp=_comp, resolve=_resolve)
    except NameError:
        print(f"[{APP_NAME}] ERRO: 'app' não encontrado.")
        print(f"        Execute SScriptSync_v1_Free em Scripts > Comp (Fusion).")
    except Exception as e:
        import traceback

        print(f"[{APP_NAME}] Erro: {e}")
        traceback.print_exc()
