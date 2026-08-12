# SScriptSync v1 — Architecture (Skeleton)

**Author:** Jhonatam Martins ([@JhonnyMarajo](https://github.com/JhonnyMarajo))  
**Version:** 1.1.0 (skeleton backup — Aug 2026)

Editor de roteiro sincronizado com DaVinci Resolve Studio, inspirado no fluxo [AVID ScriptSync](https://www.avid.com/products/media-composer-scriptsync-option).

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Shell | Python 3.10+ |
| UI window | PySide6 `QMainWindow` + `QWebEngineView` |
| UI front | Single-page `ui/app.html` (CSS + JS inline) |
| Bridge | `QWebChannel` → `ui/backend.py` |
| Resolve API | `DaVinciResolveScript.scriptapp("Resolve")` |
| Persistência | JSON em `~/.sscriptsync_v1/projects/` + sidecar `.ssync.json` |

Referência de conexão: padrão **MFlow** (probe spawn + main-thread scriptapp).  
Referência API: [Deric Resolve API Docs](https://deric.github.io/DaVinciResolve-API-Docs/), [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp).

---

## Directory layout

```
SScriptSync/                 ← repo root
├── LICENSE
├── .gitignore
└── ScriptSync/              ← application source
    ├── main.py              ← entry: QApplication + window
    ├── install.py           ← deploy to %LOCALAPPDATA%\SScriptSync_v1
    ├── requirements.txt     ← PySide6
    ├── core/
    │   ├── resolve_bridge.py    ← Resolve API wrapper
    │   ├── resolve_connection.py  ← get_resolve, probe, watcher
    │   ├── script_link.py         ← manual link (AVID-style)
    │   ├── link_model.py          ← multi-take links[]
    │   ├── text_parser.py         ← TXT/SRT/CSV + auto-sync
    │   ├── timecode.py
    │   ├── project_io.py          ← sidecar + reconcile clip_index
    │   ├── sync_store.py
    │   ├── export_io.py
    │   └── thumbnail_cache.py
    ├── ui/
    │   ├── app.html           ← full UI (editor, clips, sync rail, SVG links)
    │   └── backend.py         ← QObject slots/signals
    ├── scripts/
    │   ├── SScriptSync_v1.lua       ← Resolve Studio launcher
    │   └── SScriptSync_v1_Free.py   ← Resolve Free (Fusion)
    └── docs/
        ├── RESOLVE_STUDIO_21_API.md
        ├── SHORTCUTS.md
        ├── TESTING.md
        ├── ARCHITECTURE.md      ← this file
        └── KNOWN_ISSUES.md
```

---

## Data flow

```
Resolve Studio
    │ Workspace → Scripts → SScriptSync_v1.lua → pythonw main.py
    ▼
main.py::_bootstrap_resolve()
    │ probe (spawn) → get_resolve() main thread
    ▼
Backend (ui/backend.py)
    │ ResolveBridge.connect()
    │ get_timeline_clips(), SetCurrentTimecode(), AddMarker()
    ▼
Signals → app.html (clips_updated, lines_updated, timecode_changed, …)
    ▼
User: Link Mode → link_lines_to_clip → script_link.apply_clip_to_lines
```

---

## Core concepts

### Link model

Each script **line** may have `links[]` (multi-take). Each link stores:

- `clip_uid`, `clip_index`, `start_tc`, `end_tc`, `link_color`, `link_id`

Stable identity: **`clip_uid`** (`v1_86400`, `a1_86400`) — `clip_index` is remapped on refresh via `reconcile_clip_indices()`.

### Sync modes

| Mode | Behavior |
|------|----------|
| `linear` | Distribui linhas uniformemente na timeline |
| `clips` | Aloca linhas por duração dos clipes |

Manual links (`TextParser.is_manually_linked`) são preservados no auto-sync.

### Session keys

`{project_name}__{timeline_name}.json` under `~/.sscriptsync_v1/projects/`

---

## UI modules (app.html)

| Module | Functions |
|--------|-----------|
| Editor | `renderLines`, `bindLineInput`, inline notes |
| Link Mode | `toggleLinkMode`, `linkSelectionToClip`, SVG `drawLinkConnections` |
| Clips panel | `renderClips`, filters V/A, `focusClipInResolve` |
| Sync rail | `renderSyncRail`, `positionSyncNodes` |
| Toolbar | Menus Arquivo / Link / Sync |
| Playback | `setPlaybackActive`, watcher throttle |

---

## Install & run

```powershell
cd ScriptSync
python install.py
```

Resolve Studio: **Workspace → Scripts → SScriptSync_v1**

---

## Next (v2 roadmap)

Ver conversa AVID ScriptSync ([tutorial](https://youtu.be/VG2k-KK_bE0)):

- Multi-take tabs por linha (slates)
- Sync por markers
- Playback estável sem freeze
- Workflow Integration docked (opcional)
