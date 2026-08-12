import { TopBar } from "@/components/script-sync/top-bar"
import { MediaPanel } from "@/components/script-sync/media-panel"
import { Workspace } from "@/components/script-sync/workspace"
import { BottomBar } from "@/components/script-sync/bottom-bar"

export default function Page() {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-[#0c0c0e] text-[#c9c9cf]">
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <MediaPanel />
        <Workspace />
      </div>
      <BottomBar />
    </main>
  )
}
