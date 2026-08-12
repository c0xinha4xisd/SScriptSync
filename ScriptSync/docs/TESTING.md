# SScriptSync_v1 — Guia do Primeiro Teste

Checklist para validar no **DaVinci Resolve Studio 21**.

---

## 1. Instalação

```powershell
cd C:\Users\victv\Plugins\SScriptSync\ScriptSync
python install.py
```

Confirme:
- [ ] Pasta `%LOCALAPPDATA%\SScriptSync_v1\` criada
- [ ] `SScriptSync_v1.lua` em Fusion Scripts Utility
- [ ] Script antigo `ScriptSync.lua` removido (se existia)

---

## 2. Resolve Studio 21

1. **External scripting using = Local** (Preferences → System → General)
2. Projeto + timeline com clipes na **Video Track 1**
3. Página **Edit**

---

## 3. Abrir

```
Workspace → Scripts → SScriptSync_v1
```

Ou standalone:
```powershell
python C:\Users\victv\Plugins\SScriptSync\ScriptSync\main.py
```

---

## 4. Conexão

- [ ] **"Connected to Resolve Studio"** (dot verde)
- [ ] Painel CLIPS lista V1

---

## 5. Fluxo

1. **Import** → `.txt` / `.srt` / `.csv`
2. Sync **By Clips (V1)** → **Sync Timeline**
3. Clique numa linha → playhead move
4. Feche e reabra → sessão restaurada de `~/.sscriptsync_v1/projects/`

---

## Logs

```powershell
Get-Content $env:USERPROFILE\.sscriptsync_v1\sscriptsync_v1.log -Tail 80
```

---

Ver [RESOLVE_STUDIO_21_API.md](./RESOLVE_STUDIO_21_API.md) para API completa.
