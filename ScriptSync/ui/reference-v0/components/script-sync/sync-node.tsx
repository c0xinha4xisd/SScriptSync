type NodeColor = "yellow" | "blue" | "green"

const styles: Record<NodeColor, { ring: string; text: string }> = {
  yellow: { ring: "border-[#f5b83d] text-[#f5b83d]", text: "text-[#f5b83d]" },
  blue: { ring: "border-[#4a9fe8] text-[#4a9fe8]", text: "text-[#4a9fe8]" },
  green: { ring: "border-[#4ade80] text-[#4ade80]", text: "text-[#4ade80]" },
}

export function SyncNode({
  color,
  label,
  anchorId,
}: {
  color: NodeColor
  label: string
  anchorId?: string
}) {
  const s = styles[color]
  return (
    <div className="relative z-10 flex flex-col items-center" data-anchor={anchorId}>
      <div
        className={`flex size-11 items-center justify-center rounded-full border-2 bg-[#0f0f12] ${s.ring}`}
      >
        <span className={`text-[10px] font-medium leading-tight ${s.text}`}>{label}</span>
      </div>
    </div>
  )
}
