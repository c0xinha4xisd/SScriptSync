type TakeRow = {
  title: string
  duration: string
  meta: string
}

export function TakeCard({ rows, anchorId }: { rows: TakeRow[]; anchorId?: string }) {
  return (
    <div
      className="rounded-md border border-[#2b2b31] bg-[#1a1a1f] p-2.5 shadow-lg shadow-black/30"
      data-anchor={anchorId}
    >
      {rows.map((row, i) => (
        <div key={i} className={`flex gap-2.5 ${i > 0 ? "mt-2.5" : ""}`}>
          <div className="relative aspect-video w-[70px] shrink-0 overflow-hidden rounded-sm border border-[#2b2b31]">
            <img src="/scene-thumb.png" alt="Frame do take" className="size-full object-cover opacity-90" />
          </div>
          <div className="min-w-0 pt-0.5">
            <div className="text-[12px] font-medium text-[#d4d4d8]">{row.title}</div>
            <div className="text-[11px] text-[#8a8a91]">{row.duration}</div>
            <div className="mt-0.5 font-mono text-[10px] text-[#6f6f77]">{row.meta}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
