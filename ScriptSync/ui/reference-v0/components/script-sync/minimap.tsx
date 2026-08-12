// Deterministic pattern of tick rows: [width%, color]
const ticks: Array<{ w: number; c: string }> = [
  { w: 40, c: "#5b6472" },
  { w: 70, c: "#3d3d44" },
  { w: 55, c: "#4a9fe8" },
  { w: 30, c: "#3d3d44" },
  { w: 80, c: "#4a4a52" },
  { w: 45, c: "#4ade80" },
  { w: 60, c: "#3d3d44" },
  { w: 35, c: "#3d3d44" },
  { w: 75, c: "#4a4a52" },
  { w: 50, c: "#f5b83d" },
  { w: 40, c: "#3d3d44" },
  { w: 65, c: "#4a9fe8" },
  { w: 30, c: "#3d3d44" },
  { w: 85, c: "#4a4a52" },
  { w: 45, c: "#3d3d44" },
  { w: 55, c: "#4ade80" },
  { w: 35, c: "#3d3d44" },
  { w: 70, c: "#4a4a52" },
  { w: 50, c: "#f5b83d" },
  { w: 40, c: "#3d3d44" },
  { w: 60, c: "#4a9fe8" },
  { w: 30, c: "#3d3d44" },
  { w: 80, c: "#4a4a52" },
  { w: 45, c: "#4ade80" },
  { w: 55, c: "#3d3d44" },
  { w: 35, c: "#3d3d44" },
  { w: 75, c: "#4a4a52" },
  { w: 40, c: "#f5b83d" },
  { w: 50, c: "#3d3d44" },
  { w: 65, c: "#4a9fe8" },
  { w: 30, c: "#3d3d44" },
  { w: 70, c: "#4a4a52" },
  { w: 45, c: "#4ade80" },
]

// Marker dots on the gutter: [row index, color]
const markers: Array<{ row: number; c: string }> = [
  { row: 0, c: "#8a8a91" },
  { row: 2, c: "#4a9fe8" },
  { row: 5, c: "#4ade80" },
  { row: 9, c: "#f5b83d" },
  { row: 11, c: "#4a9fe8" },
  { row: 15, c: "#4ade80" },
  { row: 18, c: "#f5b83d" },
  { row: 20, c: "#4a9fe8" },
  { row: 23, c: "#4ade80" },
  { row: 27, c: "#f5b83d" },
  { row: 29, c: "#4a9fe8" },
  { row: 32, c: "#4ade80" },
]

const ROW_H = 3
const GAP = 3
const PY = 16

export function Minimap() {
  return (
    <div className="relative flex w-[56px] shrink-0 border-l border-[#1e1e22] bg-[#0a0a0d]">
      {/* Gutter with vertical line + colored markers */}
      <div className="relative w-4 shrink-0">
        <div className="absolute bottom-4 left-1/2 top-4 w-px -translate-x-1/2 bg-[#232329]" />
        {markers.map((m, i) => (
          <div
            key={i}
            className="absolute left-1/2 size-1.5 -translate-x-1/2 rounded-full"
            style={{ top: PY + m.row * (ROW_H + GAP) - 1, backgroundColor: m.c }}
          />
        ))}
      </div>

      {/* Code-line ticks */}
      <div className="flex flex-1 flex-col items-start py-4 pr-2" style={{ gap: GAP }}>
        {ticks.map((t, i) => (
          <div
            key={i}
            className="rounded-full"
            style={{ width: `${t.w}%`, height: ROW_H, backgroundColor: t.c }}
          />
        ))}
      </div>

      {/* Scroll thumb indicator */}
      <div className="absolute right-1 top-2 h-8 w-1 rounded-full bg-[#3a3a42]" />
    </div>
  )
}
