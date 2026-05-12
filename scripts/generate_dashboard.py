#!/usr/bin/env python3
"""
Reads Notion databases (9 clients) + Neto Google Sheet → writes public/data.json
"""
from __future__ import annotations
import json
import os
import re
from datetime import date, datetime

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
    "Farmanorte":      "35263390-2d83-8134-baf7-f013da250296",
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
    "Neto":           {"flag": "🇲🇽", "country": "México",     "kickoff": "2025-07-05", "is_outlier_visual": False, "in_average": True, "gsheet": "1azDG7zcRHqFv6s6jufBp5w1EemeBqM2yahv040jCgyc", "gid": "1934856518"},
    "Farmanorte":     {"flag": "🇨🇴", "country": "Colombia",  "kickoff": "2026-04-23", "is_outlier_visual": False, "in_average": True},
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
    # Different DBs use different field names for end date
    for key in ("Fecha Fin", "Fin", "Plazo"):
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
    completada = estado in ("Completada", "Completado", "Listo")
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
    done = sum(1 for p in pages if get_status(p) in ("Completada", "Completado", "Listo"))
    return round((done / total) * 100)


def build_client_metrics(name: str, kickoff: str, forecast: dict, distribucion: dict, compras: dict, progress_pct: int) -> dict:
    today = date.today().isoformat()
    # Completed → actual weeks taken; not completed → projected weeks to planned date.
    # Both cases use fecha_fin (the recorded or planned end date).
    ttff_sem = weeks_between(kickoff, forecast["fecha_fin"])      if forecast["fecha_fin"]      else None
    tta_sem  = weeks_between(kickoff, distribucion["fecha_fin"])  if distribucion["fecha_fin"]  else None
    ttv_sem  = weeks_between(kickoff, compras["fecha_fin"])       if compras["fecha_fin"]       else None

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


# ── Neto Google Sheet builder ─────────────────────────────────────────────────

NETO_GSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "{sheet_id}/export?format=csv&gid={gid}"
)


def parse_mx_date(raw: str) -> str | None:
    """Parse dd/mm/yyyy (Mexican format) → ISO yyyy-mm-dd. Returns None if invalid."""
    raw = raw.strip()
    if not raw or raw == "-":
        return None
    try:
        return datetime.strptime(raw, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def build_neto_from_gsheet() -> dict:
    print("  Fetching Neto from Google Sheets...")
    meta = CLIENT_META["Neto"]
    url  = NETO_GSHEET_URL.format(sheet_id=meta["gsheet"], gid=meta["gid"])

    import csv, io
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    rows = list(csv.reader(io.StringIO(resp.text)))

    # Row 0 = group headers, Row 1 = column headers, data starts at Row 2
    data_rows = rows[2:]

    # Col indices: B=1 Módulo, C=2 Actividad, E=4 Estado, H=7 FinOrig, N=13 FinMod
    COL_ACT   = 2
    COL_EST   = 4
    COL_H_FIN = 7   # Fecha Fin Original
    COL_N_FIN = 13  # Fecha Fin Modificado 03/2026

    def best_fin(row: list) -> str | None:
        """Use col N if it has a real date, else fall back to col H."""
        n = parse_mx_date(row[COL_N_FIN]) if len(row) > COL_N_FIN else None
        if n:
            return n
        return parse_mx_date(row[COL_H_FIN]) if len(row) > COL_H_FIN else None

    tasks = [
        {
            "actividad": r[COL_ACT].strip(),
            "estado":    r[COL_EST].strip(),
            "fecha_fin": best_fin(r),
        }
        for r in data_rows
        if len(r) > COL_EST and r[COL_ACT].strip() and r[COL_EST].strip()
    ]

    total = len(tasks)
    done  = sum(1 for t in tasks if t["estado"] in ("Completado", "Completada"))
    progress_pct = round((done / total) * 100) if total else 0

    def find_hito(pattern: str) -> tuple[str, str | None]:
        """Return last matching row (estado, fecha_fin)."""
        matches = [
            t for t in tasks
            if re.search(pattern, t["actividad"], re.IGNORECASE) and t["fecha_fin"]
        ]
        if not matches:
            # fallback: match without requiring date
            matches = [t for t in tasks if re.search(pattern, t["actividad"], re.IGNORECASE)]
        if not matches:
            return "", None
        t = matches[-1]
        return t["estado"], t["fecha_fin"]

    forecast_raw     = find_hito(r"Fase Activaci[oó]n M[oó]dulo Forecast|Activaci[oó]n.*Forecast")
    distribucion_raw = find_hito(r"Salida en Vivo Dispers|Salida.*Vivo.*Dispers")
    compras_raw      = find_hito(r"Fase Activaci[oó]n m[oó]dulo de Compras|Salida.*Vivo.*Compras")

    forecast     = build_hito(*forecast_raw)
    distribucion = build_hito(*distribucion_raw)
    compras      = build_hito(*compras_raw)

    kickoff = meta["kickoff"]
    client  = build_client_metrics("Neto", kickoff, forecast, distribucion, compras, progress_pct)
    client["source"] = "gsheet"
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

    clients.append(build_neto_from_gsheet())

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
