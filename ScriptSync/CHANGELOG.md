# Changelog

All notable changes to **SScriptSync v1** are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [1.2.0] — 2026-08-12 — UI v3 (v0 design)

**Powered by [JhonnyMarajo](https://github.com/JhonnyMarajo) (Jhonatam Martins)**

Redesign completo da interface (export v0.app), spine inline e take cards na ordem do roteiro.

### Added

- UI v3: top bar, painel mídias, workspace spine+roteiro+minimap, footer decupagem
- `ui/v0-theme.css`, `ui/reference-v0/` (referência visual)
- Nós sync com **nome do clip** + renomear (`link_label`, duplo-clique / F2)
- Take cards **inline** por linha (expande só linha ativa)
- Busca roteiro (Ctrl+F) e busca mídias no painel
- `backend.set_sync_node_label()` para labels customizados

### Fixed

- Link Mode sem re-render completo (glitch ao ligar clip)
- Spine alinhada à linha (sem MIN_GAP artificial)
- Scroll, drag-drop e highlights para layout v0

### Docs

- README/INSTALL: aviso **standalone vs Resolve Scripts** (GitHub clone)

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
