# SScriptSync_v1 — Editor de Roteiro Sincronizado com Timeline

Editor de texto interativo sincronizado com a timeline do **DaVinci Resolve Studio**, inspirado no fluxo **AVID ScriptSync**.

**Autor:** [Jhonatam Martins (JhonnyMarajo)](https://github.com/JhonnyMarajo)  
**Versão:** 1.1.0 (skeleton) | **Resolve alvo:** Studio 21  
**Repositório:** backup GitHub antes da grande atualização v2

---

## Funcionalidades (skeleton v1.1.0)

| Área | O que funciona |
|------|----------------|
| **Editor** | Escrever do zero, import TXT/SRT/CSV, edição inline, notas |
| **Link Mode** | Selecionar linhas → clicar clip (V ou A) → timecodes + cor |
| **Visual** | Curva SVG clipe→linha, coluna SYNC, highlight |
| **Sync** | Auto Linear / By Clips, range, filtros CAPS/()/(cena) |
| **Navegação** | Jump linha/clip/TC, focus clip (marks + playhead) |
| **Persistência** | Sidecar `.ssync.json`, sessão por projeto/timeline |
| **Export** | TXT + sidecar + EDL |

Ver **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** para mapa completo do código.

---

## Instalação

```powershell
cd C:\Users\victv\Plugins\SScriptSync\ScriptSync
python install.py
```

Instala em: `%LOCALAPPDATA%\SScriptSync_v1\`

No Resolve Studio 21:

```
Workspace → Scripts → SScriptSync_v1
```

**Resolve:** Preferences → System → General → **External scripting using = Local**

---

## Fluxo Link Mode (AVID-style)

1. Importe o roteiro (TXT)
2. Ative **Link** na toolbar
3. Clique nas linhas (Shift = intervalo, Ctrl = múltiplas)
4. Clique no clip em **CLIPS** (vídeo ou áudio)
5. Clique na linha linkada → curva + jump na timeline
6. **Re-sync** (↻) se clipes mudaram na timeline

---

## Toolbar — o que cada botão faz

| Controle | Função |
|----------|--------|
| **Link** | Liga/desliga Link Mode |
| **Re-sync** | Re-lê clipes e remapeia links (`resync_timeline`) |
| **Auto Sync** | Auto-sync com modo do menu Sync |
| **Arquivo → Novo / Import / Salvar / Export / + Linha / Limpar** | I/O roteiro |
| **Link → Marker / Unlink / Desfazer / Refazer** | Links manuais |
| **Sync → Linear / Clips / Range / SRT** | Auto-sync e import |
| **Scene / Page ◀ ▶** | Navega cenas (requer INT./EXT. no texto) |
| **? / F1** | Referência rápida |
| **↻ (CLIPS)** | Igual Re-sync |

---

## Salvar com links

- Salvar `.txt` → grava sidecar `roteiro.txt.ssync.json`
- Salvar `.ssync.json` → projeto completo
- Sessão auto: `%USERPROFILE%\.sscriptsync_v1\projects\`

---

## Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura e módulos |
| [docs/RESOLVE_STUDIO_21_API.md](docs/RESOLVE_STUDIO_21_API.md) | API Resolve + QWebChannel |
| [docs/SHORTCUTS.md](docs/SHORTCUTS.md) | Atalhos (sync com popup intro) |
| [docs/TESTING.md](docs/TESTING.md) | Checklist de testes |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | Bugs conhecidos / deferred |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões |

---

## Estrutura do código

```
ScriptSync/
├── main.py              # Entry PySide6
├── install.py           # Deploy local
├── core/                # Lógica + Resolve API
├── ui/
│   ├── app.html         # UI completa
│   └── backend.py       # Bridge Python ↔ JS
├── scripts/             # Launchers Resolve
└── docs/
```

---

## Dados e logs

| Item | Caminho |
|------|---------|
| App instalada | `%LOCALAPPDATA%\SScriptSync_v1\` |
| Sessões | `%USERPROFILE%\.sscriptsync_v1\projects\` |
| Log | `%USERPROFILE%\.sscriptsync_v1\sscriptsync_v1.log` |

---

## Resolve Free

```
Fusion page → Scripts → Comp → SScriptSync_v1_Free
```

Timeline API limitada no Free.

---

## Licença

MIT — Jhonatam Martins (JhonnyMarajo) — ver [../LICENSE](../LICENSE)
