"use client";

import { ttBadge } from "@/utils/metrics";

interface NSMetricsProps {
  ttff: number | null;
  tta: number | null;
  ttv: number | null;
  ttv_no_cv: number | null;
  n_clients: number;
}

const TARGETS = { ttff: 8, tta: 10, ttv: 24 };

const BADGE_COLORS: Record<string, string> = {
  green: "var(--gr)",
  amber: "var(--am)",
  red:   "var(--re)",
  gray:  "var(--mu)",
};

function MetricValue({ value, target, large }: { value: number | null; target: number; large?: boolean }) {
  const badge = ttBadge(value, target);
  const color = BADGE_COLORS[badge];
  return (
    <span
      className={`font-mono font-semibold ${large ? "text-5xl" : "text-3xl"}`}
      style={{ color }}
    >
      {value !== null ? `${value}` : "—"}
      <span className={`${large ? "text-xl" : "text-base"} ml-1 font-normal`} style={{ color: "var(--mu2)" }}>
        sem
      </span>
    </span>
  );
}

function TargetBadge({ value, target }: { value: number | null; target: number }) {
  const badge = ttBadge(value, target);
  const color = BADGE_COLORS[badge];
  const label = badge === "green" ? `≤ ${target} sem ✓` : `meta ${target} sem`;
  return (
    <span
      className="text-xs px-2 py-0.5 rounded-full font-medium"
      style={{ background: `${color}22`, color }}
    >
      {label}
    </span>
  );
}

export default function NSMetrics({ ttff, tta, ttv, ttv_no_cv, n_clients }: NSMetricsProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* TTV – prominent */}
      <div
        className="rounded-xl p-6 flex flex-col items-center text-center"
        style={{ background: "var(--s1)", border: "1px solid var(--b2)" }}
      >
        <div className="flex items-center justify-between w-full mb-3">
          <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--mu2)" }}>
            TTV ⭐ · Time to Value
          </span>
          <TargetBadge value={ttv} target={TARGETS.ttv} />
        </div>
        <MetricValue value={ttv} target={TARGETS.ttv} large />
        <span className="text-xs mt-1" style={{ color: "var(--mu)" }}>
          promedio {n_clients} clientes
        </span>
        {ttv_no_cv !== null && (
          <div className="mt-3 pt-3 w-full border-t flex items-center justify-center gap-2" style={{ borderColor: "var(--b1)" }}>
            <span className="text-xs" style={{ color: "var(--mu)" }}>sin Cruz Verde:</span>
            <span className="font-mono font-semibold text-lg" style={{ color: "var(--mu2)" }}>
              {ttv_no_cv}
              <span className="text-sm ml-1 font-normal">sem</span>
            </span>
          </div>
        )}
        <p className="text-xs mt-2" style={{ color: "var(--mu)" }}>
          Kickoff → Activación Módulo de Compras
        </p>
      </div>

      {/* TtFF + TtA */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { key: "ttff", label: "TtFF · Time to First Forecast", value: ttff, target: TARGETS.ttff, desc: "Kickoff → Forecast" },
          { key: "tta",  label: "TtA · Time to Activation",      value: tta,  target: TARGETS.tta,  desc: "Kickoff → Distribución" },
        ].map((m) => (
          <div
            key={m.key}
            className="rounded-xl p-4 flex flex-col items-center text-center"
            style={{ background: "var(--s1)", border: "1px solid var(--b2)" }}
          >
            <div className="flex items-start justify-between w-full mb-2">
              <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--mu2)" }}>
                {m.label}
              </span>
              <TargetBadge value={m.value} target={m.target} />
            </div>
            <MetricValue value={m.value} target={m.target} />
            <p className="text-xs mt-1" style={{ color: "var(--mu)" }}>{m.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
