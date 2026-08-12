export function BottomBar() {
  return (
    <footer className="shrink-0 border-t border-[#232327] bg-[#101013] px-4 py-3">
      <div className="flex items-stretch gap-4">
        {/* Left buttons */}
        <div className="flex w-[260px] shrink-0 flex-col gap-2.5">
          <button className="rounded-md border border-[#2f2f36] bg-[#17171b] py-3 text-sm text-[#d4d4d8] transition-colors hover:bg-[#1e1e23]">
            Sincronizar Manualmente (F5)
          </button>
          <button className="rounded-md border border-[#2f2f36] bg-[#17171b] py-3 text-sm text-[#d4d4d8] transition-colors hover:bg-[#1e1e23]">
            Próxima Cena
          </button>
        </div>

        {/* Status box */}
        <div className="flex flex-1 items-center rounded-md border border-[#232327] bg-[#141417] px-4 py-3 text-sm leading-relaxed text-[#9a9aa2]">
          Sincronização fonética concluída para Cena 04
        </div>

        {/* Right side */}
        <div className="flex w-[220px] shrink-0 flex-col gap-2.5">
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#2a2a30]">
              <div className="h-full w-[35%] rounded-full bg-[#5b6472]" />
            </div>
            <span className="font-mono text-xs text-[#c9c9cf]">35%</span>
          </div>
          <button className="rounded-md border border-[#2f2f36] bg-[#17171b] py-2 text-sm text-[#d4d4d8] transition-colors hover:bg-[#1e1e23]">
            Avançar Script
          </button>
          <button className="rounded-md border border-[#2f2f36] bg-[#17171b] py-2 text-sm text-[#d4d4d8] transition-colors hover:bg-[#1e1e23]">
            Finalizar Decupagem
          </button>
        </div>
      </div>
    </footer>
  )
}
