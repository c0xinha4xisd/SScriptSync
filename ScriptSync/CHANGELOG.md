# Changelog

All notable changes to **SScriptSync v1** are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [1.1.0] — 2026-08-12 — Skeleton backup

**Powered by [JhonnyMarajo](https://github.com/JhonnyMarajo) (Jhonatam Martins)**

Baseline estável antes da grande atualização AVID ScriptSync-style.

### Added

- Editor de roteiro PySide6 + QWebEngine (`ui/app.html`)
- **Link Mode** manual (linhas ↔ clipes V/A) estilo AVID ScriptSync
- Curvas SVG clipe → barra colorida da linha (on highlight)
- Coluna **SYNC** com thumbnails + nodes por clipe
- Painel **CLIPS** com busca e filtros V/A
- Auto-sync **Linear** e **By Clips**
- Sidecar `.ssync.json` + persistência por projeto/timeline
- Export bundle (TXT + sidecar + EDL)
- Import SRT/Rev mapping
- Notas inline por linha
- Undo/redo de links
- Popup intro + `docs/SHORTCUTS.md`
- `docs/RESOLVE_STUDIO_21_API.md` — referência API Resolve Studio 21

### Fixed (this release)

- Links visuais: `lines_updated` não re-renderizava com editor focado
- `clip_index` de faixas de áudio no reconcile
- Fallback `clip_uid` para desenho de conexões

### Removed

- Protótipo Electron legado (`main.js`, `renderer.js`, `index.html`, etc.)
- `core/resolve_async.py` (worker thread quebrava API Resolve)

### Known issues (deferred → v2)

- Sync Resolve instável durante playback (ver `docs/KNOWN_ISSUES.md`)
- Playhead-follow durante play pausa watcher (by design, pode refinar)

---

## [1.0.0] — 2026-08-11

- Primeira versão funcional: import, sync linear, click-to-jump, sessão JSON
