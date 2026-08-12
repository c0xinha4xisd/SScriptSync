# Known Issues — v1.1.0 Skeleton

Itens **conhecidos** e **adiados** para a próxima grande atualização.  
Este documento existe para o backup no GitHub refletir o estado honesto do projeto.

---

## Deferred — Resolve sync durante playback

**Sintoma:** UI pode congelar ou sync falhar se Resolve estiver em playback intenso.  
**Causa:** API `scriptapp` do Resolve bloqueia a thread principal; tentativas async em worker thread quebraram conexão.  
**Workaround:** Pare o playback no Resolve antes de Re-sync / Link / abrir o plugin.  
**Plano v2:** Estratégia híbrida (MFlow-style): connect na main thread, throttle durante play.

---

## Limitações da API Resolve (documentadas)

| Item | Detalhe |
|------|---------|
| Jump / SetCurrentTimecode | Só em Edit, Cut, Color, Fairlight, Deliver — **não** na Fusion |
| Resolve Free | Sem timeline API externa — usar `SScriptSync_v1_Free.py` (limitado) |
| External scripting | Resolve Studio → Preferences → **Local** obrigatório |

Ver [RESOLVE_STUDIO_21_API.md](RESOLVE_STUDIO_21_API.md).

---

## UI / UX

| Item | Estado |
|------|--------|
| Standalone (`python main.py`) | Não conecta ao Resolve — usar **Workspace → Scripts → SScriptSync_v1** |
| Linhas SVG só no highlight | Intencional — clique na linha ou Link Mode |
| Scene / Page nav | Só detecta cabeçalhos INT./EXT. no roteiro |
| Thumbnails | Best-effort; podem falhar em clipes sem mídia local |

---

## Reportar

Log: `%USERPROFILE%\.sscriptsync_v1\sscriptsync_v1.log`
