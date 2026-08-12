# SScriptSync_v1 — DaVinci Resolve Studio 21 Integration API

Documentação de referência de como o **SScriptSync_v1** se conecta e opera com o **DaVinci Resolve Studio 21** (Windows).  
Versão do plugin: **1.1.0** | Schema de sessão: **1**

---

## Índice

1. [Visão geral da arquitetura](#1-visão-geral-da-arquitetura)
2. [Pré-requisitos Resolve Studio 21](#2-pré-requisitos-resolve-studio-21)
3. [Caminhos de instalação](#3-caminhos-de-instalação)
4. [Modos de conexão com o Resolve](#4-modos-de-conexão-com-o-resolve)
5. [API nativa do Resolve (usada pelo SScriptSync_v1)](#5-api-nativa-do-resolve-usada-pelo-sscriptsync_v1)
6. [Bridge interno: ResolveBridge (`core/resolve_bridge.py`)](#6-bridge-interno-resolvebridge)
7. [Bridge UI: QWebChannel (`ui/backend.py` ↔ `ui/app.html`)](#7-bridge-ui-qwebchannel)
8. [Core: timecode, parser, persistência](#8-core-timecode-parser-persistência)
9. [Modos de sincronização](#9-modos-de-sincronização)
10. [Modelo de dados de linha](#10-modelo-de-dados-de-linha)
11. [Persistência de sessão](#11-persistência-de-sessão)
12. [Limitações conhecidas](#12-limitações-conhecidas)
13. [Logs e diagnóstico](#13-logs-e-diagnóstico)
14. [Referências externas](#14-referências-externas)

---

## 1. Visão geral da arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    DaVinci Resolve Studio 21                     │
│  Workspace → Scripts → SScriptSync_v1.lua  (launcher)                │
└────────────────────────────┬────────────────────────────────────┘
                             │ pythonw main.py
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  main.py                                                         │
│    ├── ResolveBridge ← DaVinciResolveScript.scriptapp("Resolve") │
│    ├── SScriptSyncWindow (PySide6 QMainWindow)                    │
│    └── QWebEngineView → ui/app.html                              │
└────────────────────────────┬────────────────────────────────────┘
                             │ QWebChannel
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  ui/backend.py (Backend QObject)                                 │
│    ├── core/resolve_bridge.py  → API Resolve                     │
│    ├── core/text_parser.py     → TXT/SRT/CSV + sync              │
│    ├── core/timecode.py        → SMPTE                           │
│    └── core/sync_store.py      → JSON por projeto/timeline       │
└─────────────────────────────────────────────────────────────────┘
```

**Fluxo principal:** Resolve → Python externo → Backend → Core → Resolve API → UI atualizada via signals.

---

## 2. Pré-requisitos Resolve Studio 21

| Requisito | Onde configurar |
|-----------|-----------------|
| **DaVinci Resolve Studio 21** | Versão Free não suporta scripting externo completo |
| **External scripting using = Local** | `DaVinci Resolve → Preferences → System → General` |
| **Python 3.9+** com **PySide6** | Instalado via `python install.py` |
| **Projeto aberto** com **timeline ativa** | Edit / Cut / Color page para jump |
| **Resolve em execução** antes de abrir SScriptSync_v1 | `scriptapp("Resolve")` exige processo ativo |

### Resolve Free (modo alternativo)

- Launcher: `SScriptSync_v1_Free.py` em `Fusion/Scripts/Comp/`
- Injeta objeto Fusion `app` — **sem API de timeline completa**
- Click-to-jump e sync de clipes **não disponíveis** no Free

---

## 3. Caminhos de instalação

### SScriptSync_v1 (aplicação)

| Plataforma | Caminho padrão |
|------------|----------------|
| Windows | `%LOCALAPPDATA%\SScriptSync_v1\` |
| macOS | `~/Library/Application Support/SScriptSync_v1/` |
| Linux | `~/.local/share/SScriptSync_v1/` |

### Launcher Lua (Studio)

```
%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\SScriptSync_v1.lua
```

### Módulo DaVinciResolveScript (Resolve 21)

O `main.py` adiciona automaticamente:

```
C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules
```

Arquivo: `DaVinciResolveScript.py` + `fusionscript.dll`

### Dados de sessão

```
%USERPROFILE%\.sscriptsync_v1\projects\{ProjectName}__{TimelineName}.json
```

### Logs

```
%USERPROFILE%\.sscriptsync_v1\sscriptsync_v1.log
%USERPROFILE%\.sscriptsync_v1\crash.log
```

---

## 4. Modos de conexão com o Resolve

### 4.1 Studio — processo externo (recomendado)

```python
import DaVinciResolveScript as dvr_script
resolve = dvr_script.scriptapp("Resolve")
```

Implementado em `core/resolve_bridge.py` → `try_connect_resolve()`  
Chamado por `main.py` na inicialização.

**Condições de sucesso:**
- Resolve aberto
- Preferência *External scripting = Local*
- Módulo no PYTHONPATH (auto-configurado)

### 4.2 Studio — via launcher Lua

`SScriptSync_v1.lua` executa `pythonw.exe main.py` sem injetar `resolve`.  
A conexão ocorre igual ao modo 4.1 via `scriptapp()`.

### 4.3 Free — Fusion injetado

`SScriptSync_v1_Free.py` recebe `app` (Fusion) do Resolve.  
Backend entra em modo Fusion (`comp` set) — timeline API indisponível.

### 4.4 Standalone

`python main.py` sem Resolve → UI funciona, import/parser ok, sem sync/jump.

---

## 5. API nativa do Resolve (usada pelo SScriptSync_v1)

Referência oficial: [DaVinci Resolve Scripting API](https://deric.github.io/DaVinciResolve-API-Docs/)  
Testado contra API **Studio 21** (estrutura compatível v18–21).

### 5.1 Cadeia de objetos

```
Resolve
  └── GetProjectManager() → ProjectManager
        └── GetCurrentProject() → Project
              └── GetCurrentTimeline() → Timeline
```

### 5.2 Métodos Timeline utilizados

| Método | Retorno | Uso no SScriptSync_v1 |
|--------|---------|-------------------|
| `GetName()` | `string` | Nome na UI + chave de sessão |
| `GetSetting("timelineFrameRate")` | `string` | FPS para conversão SMPTE |
| `GetStartFrame()` | `int` | Sync linear |
| `GetEndFrame()` | `int` | Duração da timeline |
| `GetStartTimecode()` | `string` | Metadados (futuro) |
| `GetCurrentTimecode()` | `string` | Polling playhead (200ms) |
| `SetCurrentTimecode(tc)` | `bool` | **Click-to-jump** |
| `GetTrackCount("video")` | `int` | Enumerar faixas |
| `GetItemListInTrack("video", 1)` | `TimelineItem[]` | Clipes V1 para sync |

### 5.3 Métodos TimelineItem utilizados

| Método | Retorno | Uso |
|--------|---------|-----|
| `GetName()` | `string` | Nome do clipe na UI |
| `GetStart()` | `int` | Frame início (timeline space) |
| `GetEnd()` | `int` | Frame fim |

### 5.4 SetCurrentTimecode — comportamento crítico

```python
timeline.SetCurrentTimecode("01:00:05:12")  # → bool
timeline.GetCurrentTimecode()             # → "01:00:05:12"
```

**Regras:**
- Funciona nas páginas: **Cut, Edit, Color, Fairlight, Deliver**
- **Não funciona** na página Fusion
- Pode ser assíncrono — SScriptSync_v1 usa retry (até 8 tentativas, 50ms)

Implementação: `ResolveBridge.set_playhead()`

### 5.5 Métodos Project utilizados

| Método | Uso |
|--------|-----|
| `GetName()` | Chave de persistência |

### 5.6 API **não** utilizada (futuro)

| Método | Motivo |
|--------|--------|
| `GetMarkers()` | Sync por markers (roadmap) |
| `AddMarker()` | Export de associações |
| `GetCurrentVideoItem()` | Highlight de clipe ativo |
| Transcrição nativa | Sem API pública estável |
| WorkflowIntegration.node | Caminho Electron alternativo |

---

## 6. Bridge interno: ResolveBridge

Arquivo: `core/resolve_bridge.py`

### Classe `ResolveBridge`

| Método | Descrição |
|--------|-----------|
| `connect()` | Atualiza `_project`, `_timeline`, `_fps` |
| `get_context()` | Dict com metadados project/timeline |
| `get_timeline_clips(track_type, track_index)` | Lista clipes ordenados por `start_frame` |
| `set_playhead(timecode)` | SetCurrentTimecode + retry |
| `get_current_timecode()` | GetCurrentTimecode seguro |

### Funções auxiliares

| Função | Descrição |
|--------|-----------|
| `try_connect_resolve()` | `scriptapp("Resolve")` |
| `add_resolve_module_path()` | Insere Modules no sys.path |

### Formato de clipe retornado

```json
{
  "name": "Clip001.mov",
  "start_frame": 86400,
  "end_frame": 86496,
  "duration_frames": 96,
  "start_tc": "01:00:00:00",
  "end_tc": "01:00:04:00",
  "track_type": "video",
  "track_index": 1
}
```

---

## 7. Bridge UI: QWebChannel

Arquivos: `ui/backend.py` (Python) ↔ `ui/app.html` (JavaScript)

### 7.1 Signals (Python → JavaScript)

| Signal | Payload | Quando |
|--------|---------|--------|
| `connection_changed` | `(bool, str)` | Conexão Resolve |
| `status_changed` | `(str, str)` | Mensagem + cor hex |
| `script_loaded` | `(str)` | Texto plano importado |
| `lines_updated` | `(str JSON)` | Linhas parseadas/syncadas |
| `clips_updated` | `(str JSON)` | Clipes V1 |
| `timeline_info` | `(str JSON)` | Metadados timeline |
| `timecode_changed` | `(str)` | Playhead atual (polling) |
| `active_line_changed` | `(int)` | Índice linha ativa (-1 = nenhuma) |
| `sync_completed` | `(bool, str)` | Resultado do sync |
| `session_loaded` | `(str)` | Sessão restaurada do JSON |

### 7.2 Slots (JavaScript → Python)

| Slot | Parâmetros | Ação |
|------|------------|------|
| `open_import_dialog()` | — | QFileDialog import |
| `import_script(path)` | `str` | Import por caminho |
| `save_script(content, fmt)` | `str, str` | Export TXT/SRT/CSV |
| `sync_timeline(content, fmt, mode)` | `str, str, str` | Sync (`linear` \| `clips`) |
| `update_line(index, text)` | `int, str` | Edição inline |
| `jump_to_timecode(tc)` | `str` | Move playhead |
| `jump_to_line(index)` | `int` | Jump via linha |
| `jump_to_clip(start_tc)` | `str` | Jump via painel clipes |
| `refresh_clips()` | — | Re-lê clipes V1 |
| `get_timeline_info()` | — | Atualiza painel timeline |
| `clear_script()` | — | Limpa editor + sessão |

### 7.3 Exemplo JavaScript

```javascript
backend.sync_timeline(scriptText, 'auto', 'clips');
backend.jump_to_line(3);
backend.clips_updated.connect(json => renderClips(JSON.parse(json)));
```

---

## 8. Core: timecode, parser, persistência

### 8.1 `core/timecode.py`

| Função | Descrição |
|--------|-----------|
| `timecode_to_frames(tc, fps)` | `"HH:MM:SS:FF"` → frames |
| `frames_to_timecode(frames, fps)` | frames → TC |
| `parse_srt_timestamp(srt, fps)` | SRT → `{start, end}` |
| `get_timeline_fps(timeline)` | Lê `timelineFrameRate` |
| `find_line_at_timecode(lines, tc, fps)` | Índice da linha ativa |
| `is_valid_timecode(tc)` | Valida formato |

### 8.2 `core/text_parser.py`

| Função | Descrição |
|--------|-----------|
| `detect_format(content)` | `txt` / `srt` / `csv` |
| `parse(content, fmt, fps)` | Router principal |
| `associate_timecodes(lines, duration, fps, start)` | Sync **linear** |
| `associate_by_clips(lines, clips, fps)` | Sync **por clipes V1** |
| `normalize_for_ui(lines)` | Padroniza dicts para JSON |
| `to_text(lines, fmt)` | Export |

### 8.3 `core/sync_store.py`

| Função | Descrição |
|--------|-----------|
| `save_session(project, timeline, **kwargs)` | Grava JSON |
| `load_session(project, timeline)` | Lê JSON |
| `session_path(project, timeline)` | Caminho do arquivo |

---

## 9. Modos de sincronização

### 9.1 Linear (`mode="linear"`)

Distribui linhas uniformemente entre `GetStartFrame()` e `GetEndFrame()`.

```
Linha 1 → TC início timeline
Linha N → TC fim timeline
```

Ideal para: roteiro sem timecodes, preview rápido.

### 9.2 Por clipes V1 (`mode="clips"`)

1. Lê clipes da **Video Track 1**
2. Aloca linhas proporcionalmente à duração de cada clipe
3. Subdivide timecodes dentro de cada clipe

```
Clipe A (4s) → linhas 1-2
Clipe B (8s) → linhas 3-5
```

Fallback: se V1 vazia → sync linear automático.

Ideal para: documentário, entrevistas, timeline já editada.

### 9.3 SRT / CSV

Arquivos com timecodes embutidos **preservam** TCs existentes — sync não sobrescreve.

---

## 10. Modelo de dados de linha

```json
{
  "text": "Diálogo ou narração",
  "line_number": 1,
  "start_tc": "01:00:00:00",
  "end_tc": "01:00:02:12",
  "speaker": "JOÃO",
  "clip_name": "Interview_01.mov",
  "synced": true
}
```

---

## 11. Persistência de sessão

Auto-save após: import, sync, edit line, clear.  
Auto-load ao conectar: se existir JSON para project+timeline atual.

```json
{
  "schema_version": 1,
  "project": "MeuProjeto",
  "timeline": "Timeline 1",
  "import_path": "C:\\scripts\\roteiro.txt",
  "format": "txt",
  "is_synced": true,
  "sync_mode": "clips",
  "lines": [ ... ],
  "updated_at": "2026-08-11T21:00:00+00:00"
}
```

---

## 12. Limitações conhecidas

| Limitação | Workaround |
|-----------|------------|
| Jump só em Edit/Cut/Color | Mude de página antes de clicar |
| SetCurrentTimecode assíncrono | Retry loop no backend |
| Free edition sem timeline API | Use Studio ou Workflow Integration |
| Sync clips só V1 | Coloque storyline principal em V1 |
| Drop-frame / 29.97 DF | FPS lido como float; DF não implementado |
| Transcrição Resolve | Import manual SRT exportado |
| Janela externa (não dockada) | Comportamento PySide6/MFlow |

---

## 13. Logs e diagnóstico

```powershell
# Log principal
Get-Content $env:USERPROFILE\.sscriptsync_v1\sscriptsync_v1.log -Tail 50

# Sessões salvas
Get-ChildItem $env:USERPROFILE\.sscriptsync_v1\projects\
```

Mensagens comuns:

| Log | Significado |
|-----|-------------|
| `Connected via DaVinciResolveScript` | OK |
| `Running standalone` | Resolve não encontrado |
| `SetCurrentTimecode attempt N failed` | Jump falhou — verifique página |
| `Session saved/loaded` | Persistência OK |

---

## 14. Referências externas

- [DaVinci Resolve API Docs (Deric)](https://deric.github.io/DaVinciResolve-API-Docs/)
- [X-Raym DaVinci Resolve Scripts](https://github.com/X-Raym/DaVinci-Resolve-Scripts)
- [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)
- Blackmagic Resolve 21 Help → Documentation → Developer

---

*Documento gerado para SScriptSync_v1 v1.1.0 — DaVinci Resolve Studio 21.*
