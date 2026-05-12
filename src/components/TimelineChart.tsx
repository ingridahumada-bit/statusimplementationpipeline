"use client";

import { Client } from "@/lib/types";

const META_WEEKS = 24;
const MAX_WEEKS  = 100;

export default function TimelineChart({ clients }: { clients: Client[] }) {
  const visible = clients
    .filter((c) => c.in_average && c.name !== "Puppis Arg")
    .sort((a, b) => (b.ttv_sem ?? 0) - (a.ttv_sem ?? 0));

  const metaPct  = (META_WEEKS / MAX_WEEKS) * 100;

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: "var(--s1)", border: "1px solid var(--b2)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--mu2)" }}>
          Timeline · Camino al Go-live
        </span>
        <span className="text-xs font-mono" style={{ color: "var(--mu)" }}>
          ← semanas desde kickoff
        </span>
      </div>

      <div className="relative">
        {/* Meta line */}
        <div
          className="absolute top-0 bottom-0 w-px z-10"
          style={{ left: `${metaPct}%`, background: "var(--re)", opacity: 0.6 }}
        />
        <div
          className="absolute -top-5 text-xs font-mono"
          style={{ left: `${metaPct}%`, transform: "translateX(-50%)", color: "var(--re)" }}
        >
          meta 24
        </div>

        <div className="flex flex-col gap-2 pt-1">
          {visible.map((c) => {
            const total   = c.ttv_sem ?? c.elapsed_sem + (c.remaining_sem ?? 0);
            const elapsed = c.elapsed_sem;
            const elapsedPct = Math.min((elapsed / MAX_WEEKS) * 100, 100);
            const totalPct   = Math.min((total / MAX_WEEKS) * 100, 100);
            const isOver     = total > META_WEEKS;
            const elColor    = c.status === "atrasado" ? "var(--re)" : "var(--ac)";
            const remColor   = (c.remaining_sem !== null && c.remaining_sem <= 3) ? "var(--gr)" : "var(--am)";

            return (
              <div key={c.name} className="flex items-center gap-3">
                <span className="text-xs w-28 flex-shrink-0 text-right" style={{ color: "var(--mu2)" }}>
                  {c.flag} {c.name}
                </span>
                <div className="relative flex-1 h-5 rounded overflow-hidden" style={{ background: "var(--s2)" }}>
                  {/* Elapsed segment */}
                  <div
                    className="absolute left-0 top-0 h-full rounded-l"
                    style={{ width: `${elapsedPct}%`, background: elColor, opacity: 0.85 }}
                  />
                  {/* Remaining segment */}
                  {c.remaining_sem !== null && c.remaining_sem > 0 && (
                    <div
                      className="absolute top-0 h-full"
                      style={{
                        left: `${elapsedPct}%`,
                        width: `${totalPct - elapsedPct}%`,
                        background: remColor,
                        opacity: 0.5,
                      }}
                    />
                  )}
                  {/* Red zone overlay if TTV > 24 */}
                  {isOver && (
                    <div
                      className="absolute top-0 h-full"
                      style={{
                        left: `${metaPct}%`,
                        width: `${totalPct - metaPct}%`,
                        background: "var(--re)",
                        opacity: 0.15,
                      }}
                    />
                  )}
                </div>
                <span
                  className="text-xs font-mono w-16 flex-shrink-0"
                  style={{
                    color: c.status === "golive"
                      ? "var(--gr)"
                      : c.remaining_sem === 0
                      ? "var(--re)"
                      : "var(--mu2)"
                  }}
                >
                  {c.status === "golive"
                    ? "✓ go-live"
                    : c.remaining_sem === 0
                    ? "⚠ vencida"
                    : c.remaining_sem !== null
                    ? `${c.remaining_sem}s rest.`
                    : "—"}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
