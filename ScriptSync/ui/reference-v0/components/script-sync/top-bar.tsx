import { RefreshCw, List, Download, Upload } from "lucide-react"

export function TopBar() {
  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-[#232327] bg-[#141417] px-4">
      <div className="flex items-baseline gap-1.5">
        <span className="text-sm font-semibold tracking-wide text-[#e7e7ea]">SCRIPT+SYNC</span>
        <span className="text-xs font-medium text-[#6b6b72]">v3.0</span>
      </div>

      <nav className="flex items-center gap-6 text-xs text-[#9a9aa2]">
        <button className="flex items-center gap-1.5 transition-colors hover:text-[#e7e7ea]">
          <RefreshCw className="size-3.5" aria-hidden="true" />
          <span>F3-Auto Sync</span>
        </button>
        <button className="flex items-center gap-1.5 transition-colors hover:text-[#e7e7ea]">
          <List className="size-3.5" aria-hidden="true" />
          <span>Scenes</span>
        </button>
        <button className="flex items-center gap-1.5 transition-colors hover:text-[#e7e7ea]">
          <Download className="size-3.5" aria-hidden="true" />
          <span>Import</span>
        </button>
        <button className="flex items-center gap-1.5 transition-colors hover:text-[#e7e7ea]">
          <Upload className="size-3.5" aria-hidden="true" />
          <span>Export</span>
        </button>
        <div className="ml-2 h-1.5 w-16 overflow-hidden rounded-full bg-[#2a2a30]">
          <div className="h-full w-2/3 rounded-full bg-[#5b6472]" />
        </div>
      </nav>
    </header>
  )
}
