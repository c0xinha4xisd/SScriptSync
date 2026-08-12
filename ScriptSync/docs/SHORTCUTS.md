# SScriptSync v1 — Atalhos e referência rápida

Referência canônica de atalhos, cliques e fluxos da UI.  
**Manter em sync com** o objeto `APP_REFERENCE` em `ui/app.html` (popup de introdução).

Abrir no app: botão **?** na titlebar ou **F1**.

---

## Editor

| Ação | Descrição |
|------|-----------|
| **Enter** | Quebra linha abaixo (split) |
| **Shift + Enter** | Nova linha dentro do texto |
| **Backspace** (linha vazia) | Exclui / une com linha anterior |
| **↑ / ↓** | Navegar entre linhas (no início/fim do texto) |
| **Esc** | Cancelar edição da linha |

---

## Link Mode

| Ação | Descrição |
|------|-----------|
| **Link** (toolbar) | Ativar / desativar modo ligação |
| **Shift + click** | Selecionar intervalo de linhas |
| **Ctrl + click** | Alternar linha na seleção |
| **Click** em clip (CLIPS) | Liga seleção ao clip |
| **▶ Marker** (menu Link) | Marker no playhead quando não há clip |

---

## Navegação

| Ação | Descrição |
|------|-----------|
| **▶** (linha / clip / node SYNC) | Jump / foco na timeline |
| **Click** em clipe (painel CLIPS) | Playhead + in/out marks no Resolve |
| **Duplo-click** no timecode | Jump na timeline |
| **Click** em linha sincronizada | Foco + highlight de conexões |
| **Buscar…** (toolbar) | Filtrar linhas do roteiro |

## Painel CLIPS

| Ação | Descrição |
|------|-----------|
| **Buscar clipe…** | Filtrar por nome, faixa (V/A) ou timecode |
| **Todos / V / A** | Mostrar vídeo, áudio ou ambos |
| **Click** em clipe | Foco no Resolve + highlight in/out |
| **Link Mode + click** | Ligar linhas selecionadas (vídeo ou áudio) |

Clipes **somente áudio** (A1, A2…) aparecem com ícone ♪ — antes só vídeo era listado.

---

## Notas

| Ação | Descrição |
|------|-----------|
| **✎** | Abrir painel de nota inline |
| **Ctrl + Enter** | Salvar nota |
| **Esc** | Fechar painel de nota |

---

## Toolbar e menus

| Item | Descrição |
|------|-----------|
| **Re-sync** | Re-lê clipes da timeline |
| **Auto Sync** | Sync automático (filtros no menu Sync) |
| **Arquivo** | Novo, Import, Save, Export, + Linha |
| **Link** | Marker, Unlink, Desfazer / Refazer |
| **Sync** | Modo linear/clips, filtros, range marks, SRT |

---

## Geral

| Ação | Descrição |
|------|-----------|
| **F1** | Abrir referência rápida |
| **Esc** | Fechar menus / popup |
| **×** (linha) | Excluir linha (confirma se múltiplas selecionadas) |

---

## Dicas

- Salvar `.txt` grava sidecar `.ssync.json` — links voltam ao reimportar.
- Painel **SYNC** à direita: thumbnails + nodes por take; clique para jump.
- Linhas conectoras amarelas destacam clip / linha selecionados.
- Resolve: **Workspace → Scripts → SScriptSync_v1**

---

## Ao adicionar novos atalhos

1. Implementar o atalho em `ui/app.html` (ou backend se aplicável).
2. Atualizar `APP_REFERENCE` em `ui/app.html`.
3. Atualizar esta tabela em `docs/SHORTCUTS.md`.
4. Mencionar na seção relevante do `README.md` se for fluxo principal.
