import { DashboardData } from "@/lib/types";
import TopBar from "@/components/TopBar";
import KPIRow from "@/components/KPIRow";
import NSMetrics from "@/components/NSMetrics";
import ClientGrid from "@/components/ClientGrid";
import TimelineChart from "@/components/TimelineChart";
import data from "../../public/data.json";

const dashboard = data as DashboardData;

export default function Home() {
  const clients = dashboard.clients;
  const total       = clients.filter((c) => c.in_average || c.name === "Puppis Arg").length;
  const en_progreso = clients.filter((c) => c.status === "en_progreso").length;
  const atrasados   = clients.filter((c) => c.status === "atrasado").length;

  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh" }}>
      <TopBar updatedAt={dashboard.updated_at} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex flex-col gap-8">
        <div className="flex flex-col gap-4">
          <KPIRow total={total} en_progreso={en_progreso} atrasados={atrasados} />
          <NSMetrics
            ttff={dashboard.averages.ttff}
            tta={dashboard.averages.tta}
            ttv={dashboard.averages.ttv}
            ttv_no_cv={dashboard.averages.ttv_no_cv}
            n_clients={dashboard.averages.n_ttv}
          />
        </div>

        <TimelineChart clients={clients} />

        <ClientGrid clients={clients} />
      </main>
    </div>
  );
}
