export function weeksBetween(a: string, b: string): number {
  const msPerWeek = 7 * 24 * 60 * 60 * 1000;
  return Math.round(((new Date(b).getTime() - new Date(a).getTime()) / msPerWeek) * 10) / 10;
}

export function weeksFromToday(date: string): number {
  return weeksBetween(new Date().toISOString().split("T")[0], date);
}

export type BadgeColor = "green" | "amber" | "red" | "gray";

export function ttBadge(value: number | null, target: number): BadgeColor {
  if (value === null) return "gray";
  if (value <= target) return "green";
  if (value <= target * 1.25) return "amber";
  return "red";
}

export function statusColor(status: string): string {
  if (status === "Completada" || status === "Completado") return "gr";
  if (status === "En progreso" || status === "En Progreso") return "ac";
  return "mu";
}

export function hitoBarColor(completada: boolean, atrasado: boolean, estado: string): string {
  if (completada) return "var(--gr)";
  if (atrasado) return "var(--re)";
  if (estado === "En progreso" || estado === "En Progreso") return "var(--am)";
  return "var(--mu)";
}

// Post-go-live stabilization: forecast + distribución ya activados, y la
// salida en vivo de compras está en curso — sin importar si viene atrasada.
export function isEstabilizacion(client: {
  forecast: { completada: boolean };
  distribucion: { completada: boolean };
  compras: { estado: string };
}): boolean {
  return (
    client.forecast.completada &&
    client.distribucion.completada &&
    (client.compras.estado === "En progreso" || client.compras.estado === "En Progreso")
  );
}
