# SScriptSync

**Script-synced text editor for DaVinci Resolve Studio** — AVID ScriptSync-style workflow.

**Powered by [Jhonatam Martins (JhonnyMarajo)](https://github.com/JhonnyMarajo)**

**Repositório:** [github.com/c0xinha4xisd/SScriptSync](https://github.com/c0xinha4xisd/SScriptSync)

---

## Quick start

```powershell
cd ScriptSync
python install.py
```

In Resolve Studio: **Workspace → Scripts → SScriptSync_v1**

---

## v1.1.0 — Skeleton backup (Aug 2026)

This release is a **stable skeleton** before the major v2 update:

- Link Mode (script lines ↔ timeline clips, video + audio)
- Visual connection curves + SYNC column
- Auto-sync linear / by clips
- Session persistence + sidecar JSON
- Export bundle + SRT import

See **[ScriptSync/CHANGELOG.md](ScriptSync/CHANGELOG.md)** and **[ScriptSync/docs/ARCHITECTURE.md](ScriptSync/docs/ARCHITECTURE.md)**.

Known deferred issues: **[ScriptSync/docs/KNOWN_ISSUES.md](ScriptSync/docs/KNOWN_ISSUES.md)**

---

## Documentation

| Doc | Description |
|-----|-------------|
| [ScriptSync/README.md](ScriptSync/README.md) | User guide |
| [ScriptSync/docs/ARCHITECTURE.md](ScriptSync/docs/ARCHITECTURE.md) | Code architecture |
| [ScriptSync/docs/RESOLVE_STUDIO_21_API.md](ScriptSync/docs/RESOLVE_STUDIO_21_API.md) | Resolve API reference |
| [ScriptSync/docs/SHORTCUTS.md](ScriptSync/docs/SHORTCUTS.md) | Keyboard & UI shortcuts |
| [ScriptSync/docs/TESTING.md](ScriptSync/docs/TESTING.md) | Test checklist |

---

## Requirements

- **DaVinci Resolve Studio** 18–21 (Free edition: limited via Fusion script)
- Python 3.10+ with **PySide6**
- Resolve: Preferences → General → **External scripting using = Local**

---

## License

MIT — see [LICENSE](LICENSE)
