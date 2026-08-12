# Instalação — primeiro PC (Windows)

Guia para instalar **SScriptSync v1** em um computador **novo**, sem Python configurado.

**Autor:** Jhonatam Martins (JhonnyMarajo)  
**Repo:** [github.com/c0xinha4xisd/SScriptSync](https://github.com/c0xinha4xisd/SScriptSync)

---

## Pré-requisitos

| Item | Obrigatório |
|------|-------------|
| **Windows 10/11** 64-bit | Sim |
| **Python 3.9+** (recomendado 3.11 ou 3.12) | Sim |
| **DaVinci Resolve Studio** 18–21 | Sim (para sync completo) |
| Resolve: External scripting = **Local** | Sim |

---

## Passo 1 — Instalar Python (se `python` não funciona)

Se ao rodar `python install.py` aparece:

```
Falha na execução do programa 'python.exe': O sistema não pode encontrar o arquivo especificado
```

**Python não está instalado** (ou o atalho da Microsoft Store está quebrado).

### Instalar

1. Acesse [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Baixe **Python 3.12** ou **3.11** (Windows installer 64-bit)
3. Execute o instalador e **marque**:
   - **Add python.exe to PATH**
   - **Install py launcher**
4. Clique **Install Now**
5. **Feche** o PowerShell e abra um **novo** terminal

### Testar

```powershell
py -3 --version
```

Deve mostrar algo como `Python 3.12.x`.

---

## Passo 2 — Clonar o projeto

```powershell
cd C:\Users\SeuUsuario
git clone https://github.com/c0xinha4xisd/SScriptSync.git
cd SScriptSync\ScriptSync
```

---

## Passo 3 — Rodar o instalador

**Opção A (recomendada — duplo-clique ou terminal):**

```powershell
.\install.bat
```

**Opção B (se `py` funciona):**

```powershell
py -3 install.py
```

**Opção C (se `python` funciona):**

```powershell
python install.py
```

### O instalador faz

1. Copia arquivos para `%LOCALAPPDATA%\SScriptSync_v1\`
2. Instala `SScriptSync_v1.lua` no Resolve (menu Scripts)
3. Instala **PySide6** via pip
4. Grava `python_path.txt` para o launcher Lua encontrar o Python

---

## Passo 4 — DaVinci Resolve

1. Abra **DaVinci Resolve Studio**
2. **Preferences → System → General**
3. **External scripting using = Local**
4. Abra um **projeto** com **timeline** na página **Edit**
5. Menu: **Workspace → Scripts → SScriptSync_v1**

> **Não use o modo standalone para decupagem.**  
> Comandos como `python %LOCALAPPDATA%\SScriptSync_v1\main.py` ou atalhos que abrem só a janela PySide6 **não** ligam ao Resolve.  
> O status ficará "Connecting…" / sem clipes. Sempre inicie pelo menu **Scripts** acima.

---

## Verificar instalação

| Check | Caminho / ação |
|-------|----------------|
| App instalada | `%LOCALAPPDATA%\SScriptSync_v1\main.py` |
| Launcher Lua | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\SScriptSync_v1.lua` |
| Python path | `%LOCALAPPDATA%\SScriptSync_v1\python_path.txt` |
| Log | `%USERPROFILE%\.sscriptsync_v1\sscriptsync_v1.log` |

---

## Problemas comuns

### `python` não encontrado

→ Instale Python (Passo 1) ou use `install.bat` / `py -3 install.py`.

### Script não aparece no Resolve

→ Rode `install.bat` de novo. Verifique se Resolve estava **fechado** durante a instalação (recomendado fechar e reabrir).

### `No module named PySide6`

```powershell
py -3 -m pip install PySide6
```

Depois rode `install.bat` novamente.

### Resolve Free (sem Studio)

Use **Fusion → Scripts → Comp → SScriptSync_v1_Free** — sync de timeline limitado.

### Abriu standalone (não conecta)

**Sintoma:** Janela abre, "Connecting…", sem clipes/timeline.  
**Causa:** App lançado via `python main.py` fora do Resolve.  
**Fix:** Feche, abra o Resolve com projeto+timeline, use **Workspace → Scripts → SScriptSync_v1**. Rode `install.bat` se o script não aparecer no menu.

---

## Próximo passo

[Teste funcional](TESTING.md)
