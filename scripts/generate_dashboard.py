#!/usr/bin/env python3
"""
Genera public/data.json desde la API de Celes Cronogramas (fuente única).

Antes: 10 bases de Notion con esquemas distintos + Google Sheet de Neto,
identificando go-lives por nombre. Ahora: GET /api/metrics de la app, donde
cada hito de activación está marcado explícitamente (tipo_hito) y las fechas
proyectadas/línea base salen del motor de cronogramas.

Requiere:
  METRICS_TOKEN  (secret)
  METRICS_URL    (opcional; default: producción)

La versión anterior queda en scripts/generate_dashboard_notion_backup.py.
"""
from __future__ import annotations
import json
import os
from datetime import date, datetime

import requests

METRICS_URL = os.environ.get(
    "METRICS_URL",
    "https://celes-cronogramas.vercel.app/api/metrics",
)
METRICS_TOKEN = os.environ["METRICS_TOKEN"]

# Presentación por cliente (el dato vive en la app; esto es solo estética
# del tablero). Clientes nuevos no listados reciben metadata por defecto.
CLIENT_META = {
    "Cruz Verde":     {"flag": "🇨🇴", "is_outlier_visual": True,  "in_average": True, "kickoff_override": "2025-01-07"},
    "Fybeca":         {"flag": "🇪🇨", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2025-08-19"},
    "Mi Comisariato": {"flag": "🇨🇴", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2025-09-08"},
    "MAJA":           {"flag": "🇨🇴", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2026-02-24"},
    "Tuvacol":        {"flag": "🇨🇴", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2026-02-24"},
    "Tiendas 3B":     {"flag": "🇨🇴", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2026-02-24"},
    "MiCorral":       {"flag": "🇨🇴", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2026-03-02"},
    "Puppis Col":     {"flag": "🇨🇴", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2025-09-03"},
    "Puppis Arg":     {"flag": "🇦🇷", "is_outlier_visual": False, "in_average": False, "kickoff_override": "2026-03-02"},
    "Neto":           {"flag": "🇲🇽", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2025-07-05"},
    "Farmanorte":     {"flag": "🇨🇴", "is_outlier_visual": False, "in_average": True, "kickoff_override": "2026-04-23"},
}

# nombre en la app → etiqueta histórica del tablero
NAME_MAP = {
    "Fybeca + Sana Sana": "Fybeca",
    "Mi Corral": "MiCorral",
    "Maja Sportswear": "MAJA",
}

FLAG_BY_COUNTRY = {
    "Colombia": "🇨🇴", "México": "🇲🇽", "Ecuador": "🇪🇨",
    "Argentina": "🇦🇷", "Perú": "🇵🇪", "Chile": "🇨🇱",
}


def weeks_between(d1: str, d2: str) -> float:
    delta = datetime.fromisoformat(d2) - datetime.fromisoformat(d1)
    return round(delta.days / 7, 1)


def build_hito(m: dict) -> dict:
    """Hito del data.json desde una métrica de la API (ttff/tta/ttv)."""
    today = date.today().isoformat()
    fecha = m.get("fechaProyectada")
    completada = bool(m.get("completado"))
    atrasado = bool(fecha and fecha < today and not completada)
    if completada:
        estado = "Completada"
    elif fecha:
        estado = "En progreso" if atrasado else "Sin empezar"
    else:
        estado = ""
    return {
        "estado": estado,
        "fecha_fin": fecha,
        "completada": completada,
        "atrasado": atrasado,
    }


def build_client(p: dict) -> dict:
    today = date.today().isoformat()
    name = NAME_MAP.get(p["cliente"], p["cliente"])
    meta = CLIENT_META.get(name, {
        "flag": FLAG_BY_COUNTRY.get(p.get("pais") or "", "🌎"),
        "is_outlier_visual": False,
        "in_average": True,
    })
    # kickoff oficial del tablero si existe (clientes migrados conservan
    # su fecha histórica); clientes nuevos usan el del cronograma
    kickoff = meta.get("kickoff_override") or p["kickoff"]

    def sem(fecha):
        return weeks_between(kickoff, fecha) if fecha else None

    forecast = build_hito(p["ttff"])
    distribucion = build_hito(p["tta"])
    compras = build_hito(p["ttv"])

    ttff_sem = sem(forecast["fecha_fin"])
    tta_sem = sem(distribucion["fecha_fin"])
    ttv_sem = sem(compras["fecha_fin"])

    elapsed_sem = weeks_between(kickoff, today) if kickoff else 0
    remaining_sem = (
        max(0.0, weeks_between(today, compras["fecha_fin"]))
        if compras["fecha_fin"] else None
    )

    atrasado_por = [
        key for key, h in [
            ("forecast", forecast), ("distribucion", distribucion), ("compras", compras)
        ] if h["atrasado"]
    ]
    if atrasado_por:
        status = "atrasado"
    elif compras["completada"]:
        status = "golive"
    else:
        status = "en_progreso"

    return {
        "name": name,
        "flag": meta["flag"],
        "country": p.get("pais") or "",
        "kickoff": kickoff,
        "is_outlier_visual": meta["is_outlier_visual"],
        "in_average": meta["in_average"],
        "source": "celes-cronogramas",
        "forecast": forecast,
        "distribucion": distribucion,
        "compras": compras,
        "ttff_sem": ttff_sem,
        "tta_sem": tta_sem,
        "ttv_sem": ttv_sem,
        # extra (no usado por la UI actual, disponible para la vista de desvío):
        "ttff_base_sem": p["ttff"].get("semanasLineaBase"),
        "tta_base_sem": p["tta"].get("semanasLineaBase"),
        "ttv_base_sem": p["ttv"].get("semanasLineaBase"),
        "elapsed_sem": elapsed_sem,
        "remaining_sem": remaining_sem,
        "progress_pct": p.get("avancePct", 0),
        "status": status,
        "atrasado_por": atrasado_por,
    }


def calc_averages(clients: list[dict]) -> dict:
    in_avg = [c for c in clients if c["in_average"]]
    no_cv = [c for c in in_avg if not c["is_outlier_visual"]]

    def avg(lst, key):
        vals = [c[key] for c in lst if c[key] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "ttff":      avg(in_avg, "ttff_sem"),
        "tta":       avg(in_avg, "tta_sem"),
        "ttv":       avg(in_avg, "ttv_sem"),
        "ttv_no_cv": avg(no_cv, "ttv_sem"),
        "n_ttff":    sum(1 for c in in_avg if c["ttff_sem"] is not None),
        "n_tta":     sum(1 for c in in_avg if c["tta_sem"] is not None),
        "n_ttv":     sum(1 for c in in_avg if c["ttv_sem"] is not None),
    }


def main():
    print(f"Consultando {METRICS_URL} ...")
    resp = requests.get(
        METRICS_URL,
        headers={"Authorization": f"Bearer {METRICS_TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()
    proyectos = resp.json()["proyectos"]

    clients = [build_client(p) for p in proyectos if p.get("kickoff")]
    omitidos = [p["cliente"] for p in proyectos if not p.get("kickoff")]
    if omitidos:
        print(f"  ⚠ Sin kickoff (cronograma vacío), omitidos: {', '.join(omitidos)}")

    output = {
        "updated_at": date.today().isoformat(),
        "averages": calc_averages(clients),
        "clients": clients,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "public", "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ data.json generado con {len(clients)} clientes desde Celes Cronogramas.")


if __name__ == "__main__":
    main()
