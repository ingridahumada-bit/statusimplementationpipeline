"use client";

interface KPIRowProps {
  total: number;
  en_progreso: number;
  atrasados: number;
}

export default function KPIRow({ total, en_progreso, atrasados }: KPIRowProps) {
  const pills = [
    { label: "Clientes activos", value: total,       color: "var(--ac)" },
    { label: "En progreso",      value: en_progreso, color: "var(--am)" },
    { label: "Atrasados",        value: atrasados,   color: "var(--re)" },
  ];

  return (
    <div className="flex gap-3 flex-wrap">
      {pills.map((p) => (
        <div
          key={p.label}
          className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
          style={{ background: "var(--s2)", border: `1px solid var(--b2)` }}
        >
          <span
            className="font-mono text-base font-semibold"
            style={{ color: p.color }}
          >
            {p.value}
          </span>
          <span style={{ color: "var(--mu2)" }}>{p.label}</span>
        </div>
      ))}
    </div>
  );
}
