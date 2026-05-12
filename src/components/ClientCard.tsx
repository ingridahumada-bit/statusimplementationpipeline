"use client";

import { Client, Hito } from "@/lib/types";
import { hitoBarColor, ttBadge } from "@/utils/metrics";

const BADGE_BG: Record<string, string> = {
  green: "#3ecf8e22",
  amber: "#f5a62322",
  red:   "#f25f5c22",
  gray:  "#5e647822",
};
const BADGE_COLOR: Record<string, string> = {
  green: "var(--gr)",
  amber: "var(--am)",
  red:   "var(--re)",
  gray:  "var(--mu)",
};

function StatusBadge({ status }: { status: Client["status"] }) {
  const map = {
    en_progreso: { label: "En progreso", color: "var(--am)", bg: "#f5a62322" },
    atrasado:    { label: "⚠ Atrasado",  color: "var(--re)", bg: "#f25f5c22" },
    golive:      { label: "✓ Go-live",   color: "var(--gr)", bg: "#3ecf8e22" },
  };
  const s = map[status];
  return (
    <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
}

function HitoBar({ label, hito }: { label: string; hito: Hito }) {
  const color = hitoBarColor(hito.completada, hito.atrasado, hito.estado);
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
      <span className="flex-1" style={{ color: "var(--mu2)" }}>{label}</span>
      <span className="font-mono" style={{ color }}>
        {hito.completada ? "✓" : hito.atrasado ? "⚠" : hito.estado === "No iniciada" ? "—" : "→"}
      </span>
      {hito.fecha_fin && (
        <span style={{ color: "var(--mu)" }}>{hito.fecha_fin}</span>
      )}
    </div>
  );
}

function MetricChip({
  label, value, target, isActual,
}: {
  label: string; value: number | null; target: number; isActual: boolean;
}) {
  const badge = ttBadge(value, target);
  return (
    <div
      className="flex flex-col items-center px-3 py-1.5 rounded-lg"
      style={{ background: "var(--bg)", border: "1px solid var(--b1)" }}
    >
      <span className="text-xs" style={{ color: "var(--mu)" }}>{label}</span>
      <span
        className="font-mono font-semibold text-sm"
        style={{ color: value !== null ? BADGE_COLOR[badge] : "var(--mu)" }}
      >
        {value !== null ? `${isActual ? "" : "~"}${value}s` : "—"}
      </span>
    </div>
  );
}

export default function ClientCard({ client }: { client: Client }) {
  const borderStyle = client.is_outlier_visual
    ? "1px solid var(--am)"
    : "1px solid var(--b1)";

  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-3"
      style={{ background: "var(--s1)", border: borderStyle }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg">{client.flag}</span>
            <span className="font-semibold text-sm" style={{ color: "var(--tx)" }}>
              {client.name}
            </span>
            {client.is_outlier_visual && (
              <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "#f5a62322", color: "var(--am)" }}>
                outlier
              </span>
            )}
          </div>
          <span className="text-xs" style={{ color: "var(--mu)" }}>
            Kickoff {client.kickoff} · {client.elapsed_sem}s transcurridas
          </span>
        </div>
        <StatusBadge status={client.status} />
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span style={{ color: "var(--mu2)" }}>Progreso general</span>
          <span className="font-mono" style={{ color: "var(--mu2)" }}>{client.progress_pct}%</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--s2)" }}>
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${client.progress_pct}%`,
              background: client.status === "atrasado" ? "var(--re)" : "var(--ac)",
            }}
          />
        </div>
      </div>

      {/* Hito bars */}
      <div className="flex flex-col gap-1.5">
        <HitoBar label="Forecast"     hito={client.forecast}     />
        <HitoBar label="Distribución" hito={client.distribucion} />
        <HitoBar label="Compras"      hito={client.compras}      />
      </div>

      {/* Metric chips footer */}
      <div className="grid grid-cols-3 gap-2 pt-1 border-t" style={{ borderColor: "var(--b1)" }}>
        <MetricChip label="TtFF" value={client.ttff_sem} target={8}  isActual={client.forecast.completada}     />
        <MetricChip label="TtA"  value={client.tta_sem}  target={10} isActual={client.distribucion.completada}  />
        <MetricChip label="TTV"  value={client.ttv_sem}  target={24} isActual={client.compras.completada}       />
      </div>
    </div>
  );
}
