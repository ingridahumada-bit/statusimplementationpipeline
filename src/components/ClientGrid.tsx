"use client";

import { Client } from "@/lib/types";
import ClientCard from "./ClientCard";

const DISPLAY_ORDER = [
  "Cruz Verde",
  "Fybeca",
  "Neto",
  "Puppis Col",
  "Puppis Arg",
  "Mi Comisariato",
  "MAJA",
  "Tuvacol",
  "Tiendas 3B",
  "MiCorral",
  "Farmanorte",
];

export default function ClientGrid({ clients }: { clients: Client[] }) {
  const byName = Object.fromEntries(clients.map((c) => [c.name, c]));
  const ordered = DISPLAY_ORDER.map((n) => byName[n]).filter(Boolean);

  const rows: React.ReactNode[] = [];
  let i = 0;

  while (i < ordered.length) {
    const c = ordered[i];
    if (c.name === "Puppis Col" && byName["Puppis Arg"]) {
      // Puppis pair: full-width row with 2 cards side by side
      rows.push(
        <div
          key="puppis-row"
          className="col-span-3 grid grid-cols-2 gap-4"
        >
          <ClientCard client={byName["Puppis Col"]} />
          <ClientCard client={byName["Puppis Arg"]} />
        </div>
      );
      i += 2; // skip both
    } else if (c.name === "Puppis Arg") {
      i++; // already rendered above
    } else {
      rows.push(<ClientCard key={c.name} client={c} />);
      i++;
    }
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      {rows}
    </div>
  );
}
