"use client";

export default function TopBar({ updatedAt }: { updatedAt: string }) {
  return (
    <header
      className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 border-b"
      style={{ background: "var(--s1)", borderColor: "var(--b2)" }}
    >
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold tracking-wide" style={{ color: "var(--tx)" }}>
          Celes · Dashboard de Implementaciones
        </span>
      </div>
      <span className="text-xs font-mono" style={{ color: "var(--mu2)" }}>
        Actualizado {updatedAt}
      </span>
    </header>
  );
}
