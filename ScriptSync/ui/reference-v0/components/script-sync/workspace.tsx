"use client"

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react"
import { SyncNode } from "./sync-node"
import { TakeCard } from "./take-card"
import { ScriptText } from "./script-text"
import { Minimap } from "./minimap"

type Path = { d: string; color: string }

type Connection =
  | { key: string; type: "node"; from: string; to: string; color: string }
  | { key: string; type: "branch"; to: string; color: string }

const CONNECTIONS: Connection[] = [
  { key: "top", type: "node", from: "camA", to: "top", color: "#3f3f47" },
  { key: "ana", type: "branch", to: "ana", color: "#5b6472" },
  { key: "b1", type: "node", from: "camB2", to: "b1", color: "#3f3f47" },
  { key: "b2", type: "node", from: "audio2", to: "b2", color: "#3f3f47" },
]

export function Workspace() {
  const bodyRef = useRef<HTMLDivElement>(null)
  const spineRef = useRef<HTMLDivElement>(null)
  const [paths, setPaths] = useState<Path[]>([])
  const [size, setSize] = useState({ w: 0, h: 0 })

  const compute = useCallback(() => {
    const body = bodyRef.current
    const spine = spineRef.current
    if (!body) return
    const base = body.getBoundingClientRect()
    const ox = -base.left + body.scrollLeft
    const oy = -base.top + body.scrollTop

    const rectOf = (id: string) => {
      const el = body.querySelector<HTMLElement>(`[data-anchor="${id}"]`)
      return el ? el.getBoundingClientRect() : null
    }

    const spineX = spine ? spine.getBoundingClientRect().left + ox + 1 : 60

    const next: Path[] = []
    for (const c of CONNECTIONS) {
      const target = rectOf(c.to)
      if (!target) continue
      const ex = target.left + ox
      const ey = target.top + oy + target.height / 2

      if (c.type === "node") {
        const src = rectOf(c.from)
        if (!src) continue
        const sx = src.right + ox
        const sy = src.top + oy + src.height / 2
        const c1x = sx + (ex - sx) * 0.5
        const c2x = ex - (ex - sx) * 0.5
        next.push({ d: `M ${sx} ${sy} C ${c1x} ${sy}, ${c2x} ${ey}, ${ex} ${ey}`, color: c.color })
      } else {
        // branch off the vertical spine, sweeping down into the target
        const sy = ey - 150
        next.push({
          d: `M ${spineX} ${sy} C ${spineX} ${ey}, ${spineX + (ex - spineX) * 0.5} ${ey}, ${ex} ${ey}`,
          color: c.color,
        })
      }
    }

    setSize({ w: body.scrollWidth, h: body.scrollHeight })
    setPaths(next)
  }, [])

  useLayoutEffect(() => {
    compute()
  }, [compute])

  useEffect(() => {
    const body = bodyRef.current
    if (!body) return
    const ro = new ResizeObserver(() => compute())
    ro.observe(body)
    for (const img of Array.from(body.querySelectorAll("img"))) {
      if (!img.complete) img.addEventListener("load", compute, { once: true })
    }
    window.addEventListener("resize", compute)
    const t = setTimeout(compute, 300)
    return () => {
      ro.disconnect()
      window.removeEventListener("resize", compute)
      clearTimeout(t)
    }
  }, [compute])

  return (
    <section className="flex min-w-0 flex-1 flex-col bg-[#0d0d10]">
      {/* Column headers */}
      <div className="flex h-11 shrink-0 items-center border-b border-[#232327] text-sm text-[#c9c9cf]">
        <span className="w-[184px] shrink-0 pl-4 text-[#9a9aa2]">Sincronização</span>
        <span className="flex-1">Roteiro</span>
      </div>

      {/* Body */}
      <div ref={bodyRef} className="relative flex-1 overflow-y-auto">
        {/* Connector overlay (computed from real element positions) */}
        <svg
          className="pointer-events-none absolute left-0 top-0 z-0 overflow-visible"
          width={size.w || "100%"}
          height={size.h || "100%"}
          aria-hidden="true"
        >
          {paths.map((p, i) => (
            <path key={i} d={p.d} fill="none" stroke={p.color} strokeWidth={2} strokeLinecap="round" />
          ))}
        </svg>

        <div className="relative z-10 flex min-h-full">
          {/* Sync lane */}
          <div className="relative w-[120px] shrink-0">
            <div
              ref={spineRef}
              className="absolute bottom-10 left-1/2 top-8 w-px -translate-x-1/2 bg-[#2b2b31]"
            />
            <div className="relative flex h-full flex-col items-center">
              <div className="mt-5 flex flex-col items-center gap-8">
                <SyncNode color="yellow" label="Câm A" anchorId="camA" />
                <SyncNode color="blue" label="Câm B" />
                <SyncNode color="green" label="Áudio" />
              </div>
              <div className="mt-14 h-14 w-1.5 rounded-full bg-[#33333b]" />
              <div className="mt-3 h-16 w-1.5 rounded-full bg-[#33333b]" />
              <div className="flex-1" />
              <div className="mb-6 flex flex-col items-center gap-[110px]">
                <SyncNode color="blue" label="Câm B" anchorId="camB2" />
                <SyncNode color="green" label="Áudio" anchorId="audio2" />
              </div>
            </div>
          </div>

          {/* Content column */}
          <div className="flex min-w-0 flex-1 flex-col pl-6">
            {/* Top take card */}
            <div className="flex items-start gap-4 pr-4 pt-4">
              <div className="pt-1">
                <TakeCard
                  anchorId="top"
                  rows={[
                    { title: "TAKE 4A-3", duration: "30 mins", meta: "fps fps · duratão" },
                    { title: "TAKE 4B-1", duration: "24 mins", meta: "1320 fps · duratão · 13 min" },
                  ]}
                />
              </div>
            </div>

            {/* Script */}
            <div className="mt-4 flex flex-1 border-t border-[#1e1e22]">
              <ScriptText />
              <Minimap />
            </div>

            {/* Bottom take cards */}
            <div className="space-y-4 py-5 pr-4">
              <div className="max-w-[300px]">
                <TakeCard
                  anchorId="b1"
                  rows={[{ title: "TAKE 4A-3", duration: "30 mins", meta: "120 fps · fps · duration: 24 m" }]}
                />
              </div>
              <div className="max-w-[300px]">
                <TakeCard
                  anchorId="b2"
                  rows={[{ title: "TAKE 4B-1", duration: "30 mins", meta: "1:0 fps · fps · duration: 22 m" }]}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
