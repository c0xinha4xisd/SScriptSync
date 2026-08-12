import { Video, Volume2, VolumeX } from "lucide-react"

type MediaItem = {
  label: string
  muted: boolean
  tcIn: string
  tcOut?: string
  selected?: boolean
}

const items: MediaItem[] = [
  { label: "CENA 04", muted: false, tcIn: "10:04:12:00", tcOut: "10:04:45:00", selected: true },
  { label: "CENA 04", muted: true, tcIn: "10:04:12:00", tcOut: "10:04:25:00" },
  { label: "CENA 04", muted: false, tcIn: "10:05:12:00", tcOut: "10:04:25:00" },
  { label: "CENA 04", muted: false, tcIn: "10:05:45:00" },
  { label: "CENA 04", muted: false, tcIn: "10:06:25:00" },
  { label: "CENA 04", muted: false, tcIn: "10:06:25:00" },
  { label: "CENA 04", muted: false, tcIn: "10:06:37:00" },
  { label: "CENA 04", muted: false, tcIn: "10:06:45:00" },
]

export function MediaPanel() {
  return (
    <aside className="flex w-[150px] shrink-0 flex-col border-r border-[#232327] bg-[#0f0f12]">
      <div className="px-4 py-3">
        <h2 className="text-sm font-medium text-[#c9c9cf]">Mídias</h2>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto px-3 pb-4">
        {items.map((item, i) => (
          <article
            key={i}
            className={`overflow-hidden rounded-md border bg-[#16161a] ${
              item.selected ? "border-[#3f4a5c]" : "border-[#232327]"
            }`}
          >
            <div className="flex items-center justify-between px-2 pt-2">
              <span className="text-[11px] font-medium text-[#b6b6bd]">{item.label}</span>
              <div className="flex items-center gap-1 text-[#7d7d85]">
                <Video className="size-3" aria-hidden="true" />
                {item.muted ? (
                  <VolumeX className="size-3" aria-hidden="true" />
                ) : (
                  <Volume2 className="size-3" aria-hidden="true" />
                )}
              </div>
            </div>
            <div className="relative mx-2 mt-1.5 aspect-video overflow-hidden rounded-sm">
              <img
                src="/scene-thumb.png"
                alt="Frame da cena 04"
                className="size-full object-cover opacity-90"
              />
            </div>
            <div className="px-2 pb-2 pt-1.5 font-mono text-[10px] leading-tight text-[#7d7d85]">
              <div>{item.tcIn}</div>
              {item.tcOut && <div>{item.tcOut}</div>}
            </div>
          </article>
        ))}
      </div>
    </aside>
  )
}
