"""
SScriptSync_v1 installer - python install.py
"""
import subprocess, sys, os, shutil, platform, glob, json, time

APP_NAME = "SScriptSync_v1"
PATH_TXT = "sscriptsync_v1_path.txt"
SCRIPTSYNC_VERSION = "1.1.0"
HERE   = os.path.dirname(os.path.abspath(__file__))
PLAT   = platform.system()
ARCH   = platform.machine()
PY_VER = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

# ── Resolve Scripts paths per platform ────────────────────────────────────────
SCRIPTS_UTILITY = {
    "Windows": [
        os.path.expandvars(r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"),
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility",
    ],
    "Darwin": [
        os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"),
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility",
    ],
    "Linux": [
        os.path.expanduser("~/.local/share/DaVinciResolve/Fusion/Scripts/Utility"),
        "/opt/resolve/Fusion/Scripts/Utility",
        "/home/resolve/Fusion/Scripts/Utility",
    ],
}

SCRIPTS_COMP = {
    "Windows": [
        os.path.expandvars(r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp"),
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Comp",
    ],
    "Darwin": [
        os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp"),
    ],
    "Linux": [
        os.path.expanduser("~/.local/share/DaVinciResolve/Fusion/Scripts/Comp"),
        "/opt/resolve/Fusion/Scripts/Comp",
    ],
}

def _get_install_dir():
    """Return platform-appropriate app data dir"""
    try:
        from platformdirs import user_data_dir
        return user_data_dir(APP_NAME, appauthor=False)
    except ImportError:
        pass
    # Manual fallback
    if PLAT == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")), "AppData", "Local"
        )
        return os.path.join(base, APP_NAME)
    elif PLAT == "Darwin":
        return os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    else:
        xdg = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(xdg, APP_NAME)

INSTALL_DIR = _get_install_dir()

def sep(c="-"): print(c * 54)

def log(msg, tag=""):
    prefix = f"[{tag}] " if tag else "  "
    print(f"{prefix}{msg}")

def safe(fn, *args, **kwargs):
    """Call fn, return (result, None) or (None, error_string)."""
    try:
        return fn(*args, **kwargs), None
    except Exception as e:
        return None, str(e)

# ── Detect all Python executables ────────────────────────────────────────────
def probe_python(exe):
    try:
        r = subprocess.run(
            [exe, "-c", "import sys; print(sys.version.split()[0]); print(sys.executable)"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            lines = r.stdout.strip().splitlines()
            if len(lines) >= 2:
                ver, real_exe = lines[0], lines[1]
                maj, minor = int(ver.split(".")[0]), int(ver.split(".")[1])
                if maj == 3 and minor >= 9:
                    return real_exe, ver
    except Exception:
        pass
    return None, None

def find_all_pythons():
    seen = {}
    
    def add(exe):
        if exe and os.path.isfile(exe):
            real_exe, ver = probe_python(exe)
            if real_exe and ver:
                if real_exe not in seen:
                    seen[real_exe] = ver
                    log(f"Found Python {ver} at {real_exe}", "PYTHON")
    
    # System python
    add(sys.executable)
    add("python3" if PLAT != "Windows" else "python")
    
    # Windows common paths
    if PLAT == "Windows":
        la = os.environ.get("LOCALAPPDATA", "")
        if la:
            for ver in ["312", "311", "310", "39"]:
                add(os.path.join(la, "Programs", "Python", f"Python{ver}", "python.exe"))
                add(os.path.join(la, "Programs", "Python", f"Python{ver}", "pythonw.exe"))
        
        # Program Files
        pf = os.environ.get("PROGRAMFILES", "")
        if pf:
            for ver in ["312", "311", "310", "39"]:
                add(os.path.join(pf, "Python3{ver}", "python.exe"))
                add(os.path.join(pf, "Python3{ver}", "pythonw.exe"))
    
    # PATH
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.isdir(p):
            for f in os.listdir(p):
                if f.startswith("python") and (f.endswith(".exe") or not "." in f):
                    add(os.path.join(p, f))
    
    return seen

# ── Install ScriptSync files ─────────────────────────────────────────────────
def install_files():
    """Copy ScriptSync files to install directory"""
    log(f"Installing {APP_NAME} to: {INSTALL_DIR}", "INSTALL")
    
    # Create install directory
    os.makedirs(INSTALL_DIR, exist_ok=True)
    
    # Copy files
    files_to_copy = [
        "main.py",
        "ui/backend.py",
        "ui/app.html",
        "scripts/SScriptSync_v1.lua",
        "scripts/SScriptSync_v1_Free.py",
    ]
    
    for rel_path in files_to_copy:
        src = os.path.join(HERE, rel_path)
        dst = os.path.join(INSTALL_DIR, rel_path)
        
        if not os.path.isfile(src):
            log(f"Warning: Source file not found: {src}", "INSTALL")
            continue
        
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        log(f"Copied: {rel_path}", "INSTALL")

    # Copy core package
    core_src = os.path.join(HERE, "core")
    core_dst = os.path.join(INSTALL_DIR, "core")
    if os.path.isdir(core_src):
        shutil.copytree(core_src, core_dst, dirs_exist_ok=True)
        log("Copied: core/", "INSTALL")

    # Copy docs
    docs_src = os.path.join(HERE, "docs")
    docs_dst = os.path.join(INSTALL_DIR, "docs")
    if os.path.isdir(docs_src):
        shutil.copytree(docs_src, docs_dst, dirs_exist_ok=True)
        log("Copied: docs/", "INSTALL")
    
    # Write version file
    with open(os.path.join(INSTALL_DIR, "VERSION"), "w") as f:
        f.write(SCRIPTSYNC_VERSION)
    
    # Write scriptsync_path.txt
    with open(os.path.join(INSTALL_DIR, PATH_TXT), "w") as f:
        f.write(INSTALL_DIR)
    
    log("Files installed successfully", "INSTALL")

# ── Install bridge scripts ───────────────────────────────────────────────────
def install_bridge_scripts():
    """Install bridge scripts to Resolve Scripts directories"""
    log("Installing bridge scripts to Resolve...", "INSTALL")

    def _remove_legacy(script_dir):
        for legacy in ("ScriptSync.lua", "ScriptSync_Free.py", "scriptsync_path.txt"):
            legacy_path = os.path.join(script_dir, legacy)
            if os.path.isfile(legacy_path):
                try:
                    os.remove(legacy_path)
                    log(f"Removed legacy: {legacy_path}", "INSTALL")
                except OSError:
                    pass

    # Install Lua script (Studio)
    for script_dir in SCRIPTS_UTILITY.get(PLAT, []):
        if os.path.isdir(script_dir):
            _remove_legacy(script_dir)
            src = os.path.join(INSTALL_DIR, "scripts", "SScriptSync_v1.lua")
            dst = os.path.join(script_dir, "SScriptSync_v1.lua")
            shutil.copy2(src, dst)
            log(f"Installed Lua script to: {script_dir}", "INSTALL")
            
            path_txt = os.path.join(script_dir, PATH_TXT)
            with open(path_txt, "w") as f:
                f.write(INSTALL_DIR)
            break
    
    # Install Python script (Free)
    for script_dir in SCRIPTS_COMP.get(PLAT, []):
        if os.path.isdir(script_dir):
            _remove_legacy(script_dir)
            src = os.path.join(INSTALL_DIR, "scripts", "SScriptSync_v1_Free.py")
            dst = os.path.join(script_dir, "SScriptSync_v1_Free.py")
            shutil.copy2(src, dst)
            log(f"Installed Python script to: {script_dir}", "INSTALL")
            
            path_txt = os.path.join(script_dir, PATH_TXT)
            with open(path_txt, "w") as f:
                f.write(INSTALL_DIR)
            break

# ── Install dependencies ─────────────────────────────────────────────────────
def install_dependencies(python_exe):
    """Install Python dependencies"""
    log("Installing dependencies...", "INSTALL")
    
    requirements = ["PySide6"]
    
    for req in requirements:
        try:
            result = subprocess.run(
                [python_exe, "-m", "pip", "install", req],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                log(f"Installed: {req}", "INSTALL")
            else:
                log(f"Failed to install {req}: {result.stderr}", "ERROR")
        except Exception as e:
            log(f"Error installing {req}: {e}", "ERROR")

# ── Write python_path.txt ────────────────────────────────────────────────────
def write_python_path(python_exe):
    """Write python_path.txt for bridge scripts"""
    path_txt = os.path.join(INSTALL_DIR, "python_path.txt")
    with open(path_txt, "w") as f:
        f.write(python_exe)
    log(f"Wrote python_path.txt: {python_exe}", "INSTALL")

# ── Main installation ────────────────────────────────────────────────────────
def main():
    print()
    sep("=")
    print("  SScriptSync_v1 Installer v" + SCRIPTSYNC_VERSION)
    print(f"  Platform: {PLAT} {ARCH}")
    print(f"  Python: {PY_VER}")
    sep("=")
    print()
    
    # Find Python
    log("Detecting Python installations...", "PYTHON")
    pythons = find_all_pythons()
    
    if not pythons:
        log("ERROR: No compatible Python found (3.9+ required)", "ERROR")
        log("Please install Python 3.9 or higher from python.org", "ERROR")
        return
    
    log(f"Found {len(pythons)} Python installation(s)", "PYTHON")
    
    # Select best Python
    python_exe = list(pythons.keys())[0]
    python_ver = pythons[python_exe]
    log(f"Selected: Python {python_ver} at {python_exe}", "PYTHON")
    print()
    
    # Install files
    install_files()
    print()
    
    # Install bridge scripts
    install_bridge_scripts()
    print()
    
    # Install dependencies
    install_dependencies(python_exe)
    print()
    
    # Write python_path.txt
    write_python_path(python_exe)
    
    # Summary
    sep("=")
    log("Installation complete!", "SUCCESS")
    log(f"{APP_NAME} installed to: {INSTALL_DIR}", "SUCCESS")
    print()
    log("To use SScriptSync_v1:", "INFO")
    if PLAT == "Windows":
        log("  - Resolve Studio: Workspace > Scripts > SScriptSync_v1", "INFO")
        log("  - Resolve Free: Scripts > Comp > SScriptSync_v1_Free (Fusion page)", "INFO")
    else:
        log("  - Resolve Studio: Workspace > Scripts > SScriptSync_v1", "INFO")
        log("  - Resolve Free: Scripts > Comp > SScriptSync_v1_Free (Fusion page)", "INFO")
    print()
    log("Or run standalone:", "INFO")
    log(f"  {python_exe} {os.path.join(INSTALL_DIR, 'main.py')}", "INFO")
    print()
    sep("=")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
