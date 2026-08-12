-- SScriptSync_v1 launcher for DaVinci Resolve Studio
-- Place in: %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
-- In Resolve: Workspace > Scripts > SScriptSync_v1

local APP_NAME = "SScriptSync_v1"
local is_win = (package.config:sub(1,1) == "\\")
local sep     = is_win and "\\" or "/"

local script_dir = (debug.getinfo(1,"S").source or ""):match("^@(.+)[/\\][^/\\]+$") or ""

local function default_app_dir()
    if is_win then
        local la = os.getenv("LOCALAPPDATA") or ""
        if la ~= "" then return la .. "\\" .. APP_NAME end
        local up = os.getenv("USERPROFILE") or os.getenv("HOME") or "C:\\Users\\Default"
        return up .. "\\AppData\\Local\\" .. APP_NAME
    else
        local home = os.getenv("HOME") or "/tmp"
        local mac_test = io.open(home .. "/Library", "r")
        if mac_test then mac_test:close()
            return home .. "/Library/Application Support/" .. APP_NAME
        else
            return home .. "/.local/share/" .. APP_NAME
        end
    end
end

local app_dir = default_app_dir()
local path_txt = "sscriptsync_v1_path.txt"
local txt_paths = {
    script_dir .. sep .. path_txt,
    app_dir .. sep .. path_txt,
}
for _, tp in ipairs(txt_paths) do
    local f = io.open(tp, "r")
    if f then
        local p = f:read("*l"); f:close()
        if p and p ~= "" then app_dir = p; break end
    end
end

local main_py = app_dir .. sep .. "main.py"

local check = io.open(main_py, "r")
if not check then
    print("[" .. APP_NAME .. "] ERROR: main.py not found at: " .. main_py ..
          "\nRun install.py first, or edit " .. path_txt)
    return
end
check:close()

local python_exe = nil
local py_txt_paths = {
    script_dir .. sep .. "python_path.txt",
    app_dir .. sep .. "python_path.txt",
}
for _, pp in ipairs(py_txt_paths) do
    local f = io.open(pp, "r")
    if f then
        local p = f:read("*l"); f:close()
        if p and p ~= "" then
            local tf = io.open(p, "r")
            if tf then tf:close(); python_exe = p; break end
        end
    end
end

if not python_exe and is_win then
    local la = os.getenv("LOCALAPPDATA") or ""
    local candidates = {
        la .. "\\Programs\\Python\\Python312\\python.exe",
        la .. "\\Programs\\Python\\Python311\\python.exe",
        la .. "\\Programs\\Python\\Python310\\python.exe",
        la .. "\\Programs\\Python\\Python39\\python.exe",
    }
    for _, c in ipairs(candidates) do
        local tf = io.open(c, "r")
        if tf then tf:close(); python_exe = c; break end
    end
end

if not python_exe then
    python_exe = is_win and "python" or "python3"
end

local cmd
if is_win then
    local pyw = python_exe:gsub("python%.exe$", "pythonw.exe")
    local tf2 = io.open(pyw, "r")
    if tf2 then tf2:close(); python_exe = pyw end
    cmd = string.format('start "" "%s" "%s"', python_exe, main_py)
else
    cmd = string.format('"%s" "%s" > /tmp/sscriptsync_v1.log 2>&1 &', python_exe, main_py)
end

print("[" .. APP_NAME .. "] Launching: " .. cmd)
os.execute(cmd)
