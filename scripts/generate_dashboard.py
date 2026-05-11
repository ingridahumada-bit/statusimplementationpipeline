#!/usr/bin/env python3
"""
Reads Notion databases (9 clients) + Neto Excel → writes public/data.json
"""
from __future__ import annotations
import json
import os
import re
from datetime import date, datetime

import pandas as pd
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

CRONOGRAMAS = {
    "Cruz Verde":      "17c63390-2d83-808e-8a0d-f0999f0cd01d",
    "Fybeca":          "25463390-2d83-81cb-818c-f0aa6217a957",
    "Mi Comisariato":  "2ca63390-2d83-8007-99f4-f9c3f6222667",
    "MAJA":            "eab63390-2d83-8277-8779-01cba04530af",
    "Tuvacol":         "31163390-2d83-81fa-9dc4-c7e49fe0ee98",
    "Tiendas 3B":      "32263390-2d83-80aa-8f10-e8a850a50de8",
    "MiCorral":        "a4663390-2d83-823e-b995-81ad171a8fab",
    "Puppis Col":      "27663390-2d83-80f0-b1d2-d8ca322d4ba1",
    "Puppis Arg":      "d3963390-2d83-82c1-810f-016ef9c02381",
}

CLIENT_META = {
    "Cruz Verde":     {"flag": "🇨🇴", "country": "Colombia",   "kickoff": "2025-01-07", "is_outlier_visual": True,  "in_average": True},
    "Fybeca":         {"flag": "🇪🇨", "country": "Ecuador",    "kickoff": "2025-08-19", "is_outlier_visual": False, "in_average": True},
    "Mi Comisariato": {"flag": "🇨🇴", "country": "Colombia",   "kickoff": "2025-09-08", "is_outlier_visual": False, "in_average": True},
    "MAJA":           {"flag": "🇨🇴", "country": "Colombia",   "kickoff": "2026-02-24", "is_outlier_visual": False, "in_average": True},
    "Tuvacol":        {"flag": "🇨🇴", "country": "Colombia",   "kickoff": "2026-02-24", "is_outlier_visual": False, "in_average": True},
    "Tiendas 3B":     {"flag": "🇨🇴", "country": "Colombia",   "kickoff": "2026-02-24", "is_outlier_visual": False, "in_average": True},
    "MiCorral":       {"flag": "🇨🇴", "country": "Colombia",   "kickoff": "2026-03-02", "is_outlier_visual": False, "in_average": True},
    "Puppis Col":     {"flag": "🇨🇴", "country": "Colombia",   "kickoff": "2025-09-03", "is_outlier_visual": False, "in_average": True},
    "Puppis Arg":     {"flag": "🇦🇷", "country": "Argentina",  "kickoff": "2026-03-02", "is_outlier_visual": False, "in_average": False},
    "Neto":           {"flag": "🇲🇽", "country": "México",     "kickoff": "2025-07-05", "is_outlier_visual": False, "in_average": True},
}

HITO_ALIASES = {
    "forecast": [
        "activación módulo de forecast",
        "activación y configuración módulo de pronóstico de demanda",
    ],
    "distribucion": [
        "activación módulo de distribución",
        "despliegue en productivo: módulo distribución",
    ],
    "compras": [
        "activación módulo de compras",
        "pruebas y aceptación módulo de compras",
    ],
}


# ── Notion helpers ────────────────────────────────────────────────────────────

def query_database(db_id: str) -> list[dict]:
    pages, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=HEADERS, json=body
        )
        r.raise_for_status()
        data = r.json()
        pages.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return pages


def get_title(page: dict) -> str:
    for prop in page["properties"].values():
        if prop["type"] == "title":
            items = prop.get("title", [])
            return items[0]["plain_text"].strip() if items else ""
    return ""


def get_status(page: dict) -> str:
    for key in ("Estado", "Status"):
        prop = page["properties"].get(key, {})
        if prop.get("type") == "status" and prop.get("status"):
            return prop["status"]["name"]
    return ""


def get_fecha_fin(page: dict) -> str | None:
    # Some DBs use "Fecha Fin", others use "Fin" — try explicit names first
    for key in ("Fecha Fin", "Fin"):
        prop = page["properties"].get(key, {})
        if prop.get("type") == "date" and prop.get("date"):
            d = prop["date"]
            return d.get("end") or d.get("start")
    return None


# ── Calculations ──────────────────────────────────────────────────────────────

def weeks_between(d1: str, d2: str) -> float:
    delta = datetime.fromisoformat(d2) - datetime.fromisoformat(d1)
    return round(delta.days / 7, 1)


def build_hito(estado: str, fecha_fin: str | None) -> dict:
    today = date.today().isoformat()
    completada = estado in ("Completada", "Completado")
    atrasado = bool(fecha_fin and fecha_fin < today and not completada)
    return {
        "estado": estado,
        "fecha_fin": fecha_fin,
        "completada": completada,
        "atrasado": atrasado,
    }


def find_hito_in_pages(pages: list[dict], aliases: list[str]) -> tuple[str, str | None]:
    for page in pages:
        title = get_title(page).lower().strip()
        if any(alias in title for alias in aliases):
            return get_status(page), get_fecha_fin(page)
    return "", None


def count_progress(pages: list[dict]) -> int:
    total = len(pages)
    if not total:
        return 0
    done = sum(1 for p in pages if get_status(p) in ("Completada", "Completado"))
    return round((done / total) * 100)


def build_client_metrics(name: str, kickoff: str, forecast: dict, distribucion: dict, compras: dict, progress_pct: int) -> dict:
    today = date.today().isoformat()
    ttff_sem = weeks_between(kickoff, forecast["fecha_fin"])   if forecast["completada"] and forecast["fecha_fin"]   else (weeks_between(kickoff, forecast["fecha_fin"])   if forecast["fecha_fin"]   else None)
    tta_sem  = weeks_between(kickoff, distribucion["fecha_fin"]) if distribucion["completada"] and distribucion["fecha_fin"] else (weeks_between(kickoff, distribucion["fecha_fin"]) if distribucion["fecha_fin"] else None)
    ttv_sem  = weeks_between(kickoff, compras["fecha_fin"])    if compras["fecha_fin"]    else None

    elapsed_sem  = weeks_between(kickoff, today)
    remaining_sem = weeks_between(today, compras["fecha_fin"]) if compras["fecha_fin"] else None
    if remaining_sem is not None and remaining_sem < 0:
        remaining_sem = 0

    atrasado_por = []
    for key, h in [("forecast", forecast), ("distribucion", distribucion), ("compras", compras)]:
        if h["atrasado"]:
            atrasado_por.append(key)

    if atrasado_por:
        status = "atrasado"
    elif compras["completada"]:
        status = "golive"
    else:
        status = "en_progreso"

    meta = CLIENT_META[name]
    return {
        "name": name,
        "flag": meta["flag"],
        "country": meta["country"],
        "kickoff": kickoff,
        "is_outlier_visual": meta["is_outlier_visual"],
        "in_average": meta["in_average"],
        "source": "notion",
        "forecast": forecast,
        "distribucion": distribucion,
        "compras": compras,
        "ttff_sem": ttff_sem,
        "tta_sem": tta_sem,
        "ttv_sem": ttv_sem,
        "elapsed_sem": elapsed_sem,
        "remaining_sem": remaining_sem,
        "progress_pct": progress_pct,
        "status": status,
        "atrasado_por": atrasado_por,
    }


# ── Notion client builder ─────────────────────────────────────────────────────

def build_notion_client(name: str) -> dict:
    db_id = CRONOGRAMAS[name]
    print(f"  Fetching {name}...")
    pages = query_database(db_id)

    forecast_raw    = find_hito_in_pages(pages, HITO_ALIASES["forecast"])
    distribucion_raw = find_hito_in_pages(pages, HITO_ALIASES["distribucion"])
    compras_raw     = find_hito_in_pages(pages, HITO_ALIASES["compras"])

    forecast    = build_hito(*forecast_raw)
    distribucion = build_hito(*distribucion_raw)
    compras     = build_hito(*compras_raw)
    progress_pct = count_progress(pages)

    kickoff = CLIENT_META[name]["kickoff"]
    return build_client_metrics(name, kickoff, forecast, distribucion, compras, progress_pct)


# ── Neto Excel builder ────────────────────────────────────────────────────────

def build_neto_from_excel(path: str) -> dict:
    print("  Reading Neto from Excel...")
    df = pd.read_excel(path, header=0)
    df.columns = [str(c).strip() for c in df.columns]

    tasks = df[df["Actividad"].notna() & df["Estado"].notna()].copy()
    tasks["_fecha_fin"] = pd.to_datetime(tasks["Fecha Fin"], errors="coerce").dt.date

    total = len(tasks)
    done  = len(tasks[tasks["Estado"].isin(["Completado", "Completada"])])
    progress_pct = round((done / total) * 100) if total else 0

    def find_excel_hito(pattern: str) -> tuple[str, str | None]:
        mask = tasks["Actividad"].str.contains(pattern, case=False, na=False, regex=True)
        rows = tasks[mask & tasks["_fecha_fin"].notna()]
        if rows.empty:
            return "", None
        r = rows.iloc[-1]
        return str(r["Estado"]), str(r["_fecha_fin"])

    forecast_raw    = find_excel_hito(r"Activaci[oó]n.*Forecast|M[oó]dulo.*Forecast")
    distribucion_raw = find_excel_hito(r"Salida.*[Vv]ivo.*[Dd]ispers|Distribuci[oó]n")
    compras_raw     = find_excel_hito(r"Salida.*[Vv]ivo.*[Cc]ompras|Compras")

    forecast    = build_hito(*forecast_raw)
    distribucion = build_hito(*distribucion_raw)
    compras     = build_hito(*compras_raw)

    kickoff = CLIENT_META["Neto"]["kickoff"]
    client  = build_client_metrics("Neto", kickoff, forecast, distribucion, compras, progress_pct)
    client["source"] = "excel"
    return client


# ── Averages ──────────────────────────────────────────────────────────────────

def calc_averages(clients: list[dict]) -> dict:
    in_avg = [c for c in clients if c["in_average"]]
    no_cv  = [c for c in in_avg if not c["is_outlier_visual"]]

    def avg(lst, key):
        vals = [c[key] for c in lst if c[key] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "ttff":     avg(in_avg, "ttff_sem"),
        "tta":      avg(in_avg, "tta_sem"),
        "ttv":      avg(in_avg, "ttv_sem"),
        "ttv_no_cv": avg(no_cv, "ttv_sem"),
        "n_ttff":   sum(1 for c in in_avg if c["ttff_sem"] is not None),
        "n_tta":    sum(1 for c in in_avg if c["tta_sem"]  is not None),
        "n_ttv":    sum(1 for c in in_avg if c["ttv_sem"]  is not None),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Generando dashboard...")
    clients = []

    for name in CRONOGRAMAS:
        clients.append(build_notion_client(name))

    excel_path = os.path.join(os.path.dirname(__file__), "..", "data", "Cronograma_Neto_V3.xlsx")
    if os.path.exists(excel_path):
        clients.append(build_neto_from_excel(excel_path))
    else:
        print("  ⚠ Excel de Neto no encontrado, omitiendo.")

    averages = calc_averages(clients)
    output = {
        "updated_at": date.today().isoformat(),
        "averages": averages,
        "clients": clients,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "public", "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ data.json generado con {len(clients)} clientes.")


if __name__ == "__main__":
    main()
