export interface Hito {
  estado: string;
  fecha_fin: string | null;
  completada: boolean;
  atrasado: boolean;
}

export interface Client {
  name: string;
  flag: string;
  country: string;
  kickoff: string;
  is_outlier_visual: boolean;
  in_average: boolean;
  source: "notion" | "excel";

  forecast: Hito;
  distribucion: Hito;
  compras: Hito;

  ttff_sem: number | null;
  tta_sem: number | null;
  ttv_sem: number | null;
  elapsed_sem: number;
  remaining_sem: number | null;
  progress_pct: number;

  status: "en_progreso" | "atrasado" | "golive";
  atrasado_por: ("forecast" | "distribucion" | "compras")[];
}

export interface DashboardData {
  updated_at: string;
  averages: {
    ttff: number | null;
    tta: number | null;
    ttv: number | null;
    ttv_no_cv: number | null;
    n_ttff: number;
    n_tta: number;
    n_ttv: number;
  };
  clients: Client[];
}
