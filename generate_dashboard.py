import os
import requests
from datetime import date, datetime

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
TODAY = date.today()

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-01",
    "Content-Type": "application/json",
}

CRONOGRAMAS = {
    "Cruz Verde":     "17c63390-2d83-8111-8fe8-000b617b7e29",
    "Mi Comisariato": "2ca63390-2d83-8155-ae74-000b0738252c",
    "Fybeca":         "25463390-2d83-8115-a5f2-000b97b006d6",
    "MAJA":           "33663390-2d83-8342-a2f5-8768c72128da",
    "Tuvacol":        "31163390-2d83-810e-88f8-000b138394ad",
    "Tiendas 3B":     "32263390-2d83-8177-9465-000bc1938d67",
    "MiCorral":       "06b63390-2d83-83fa-b1b5-07954f01b376",
    "Puppis Col":     "27663390-2d83-81bc-8f6d-000b397ba9d9",
    "Puppis Arg":     "42163390-2d83-83db-b015-87aeb58fc21c",
}

KICKOFFS = {
    "Cruz Verde":     date(2025, 1,  7),
    "Mi Comisariato": date(2025, 9,  8),
    "Fybeca":         date(2025, 8, 19),
    "MAJA":           date(2026, 2, 24),
    "Tuvacol":        date(2026, 2, 24),
    "Tiendas 3B":     date(2026, 2, 24),
    "MiCorral":       date(2026, 3,  2),
    "Puppis Col":     date(2025, 9,  3),
    "Puppis Arg":     date(2026, 3,  2),
    "Neto":           date(2025, 7,  5),
}

HITOS = {
    "forecast": ["activación módulo de forecast", "activación y configuración módulo de pronóstico de demanda"],
    "dist":     ["activación módulo de distribución", "despliegue en productivo: módulo distribución",
                 "despliegue en productivo: módulo distribución"],
    "compras":  ["activación módulo de compras", "pruebas y aceptación módulo de compras",
                 "activación del módulo"],
}

def weeks(start, end):
    return round((end - start).days / 7, 1)

def query_db(db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(url, headers=HEADERS, json=body)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results

def get_title(page):
    """Extrae título de la página desde la API REST de Notion."""
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            items = prop.get("title", [])
            return items[0]["plain_text"] if items else ""
    return ""

def get_status(page):
    """Extrae estado de la página."""
    props = page.get("properties", {})
    for key in ["Estado", "Status"]:
        prop = props.get(key, {})
        if prop.get("type") == "status":
            s = prop.get("status")
            return s["name"] if s else ""
    return ""

def get_fin(page):
    """Extrae fecha fin — prueba todos los campos posibles."""
    props = page.get("properties", {})
    for key in ["Fin", "Fecha Fin", "Fecha fin", "Fecha Fin ", "date:Fin:start"]:
        prop = props.get(key, {})
        if prop.get("type") == "date" and prop.get("date"):
            d = prop["date"]
            return d.get("end") or d.get("start")
    return None

def parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except:
        return None

def get_hito(pages, nombres):
    """Busca hito por nombre (case-insensitive) y devuelve (estado, fecha_fin)."""
    for page in pages:
        title = get_title(page).lower().strip()
        if any(n.lower() in title for n in nombres):
            estado = get_status(page)
            fin = parse_date(get_fin(page))
            return estado, fin
    return None, None

def is_atrasado(fin, estado):
    if not fin or not estado:
        return False
    if "Completada" in estado or "Archivada" in estado:
        return False
    return fin < TODAY

def get_client_data(name, db_id):
    pages = query_db(db_id)
    ko = KICKOFFS.get(name)

    # Debug: mostrar todas las actividades encontradas
    print(f"    {name}: {len(pages)} tareas encontradas")

    f_estado, f_fin = get_hito(pages, HITOS["forecast"])
    d_estado, d_fin = get_hito(pages, HITOS["dist"])
    c_estado, c_fin = get_hito(pages, HITOS["compras"])

    print(f"    Forecast: estado={f_estado}, fin={f_fin}")
    print(f"    Dist:     estado={d_estado}, fin={d_fin}")
    print(f"    Compras:  estado={c_estado}, fin={c_fin}")

    ttff = weeks(ko, f_fin) if ko and f_fin else None
    dist = weeks(ko, d_fin) if ko and d_fin else None
    ttv  = weeks(ko, c_fin) if ko and c_fin else None

    elapsed = weeks(ko, TODAY) if ko else 0
    rem = round((c_fin - TODAY).days / 7, 1) if c_fin else None
    if ttv and elapsed >= ttv:
        elapsed = ttv
        rem = 0

    f_atr = is_atrasado(f_fin, f_estado)
    d_atr = is_atrasado(d_fin, d_estado)
    c_atr = is_atrasado(c_fin, c_estado)
    atrasado = f_atr or d_atr or c_atr

    # Progreso general
    total = len([p for p in pages if get_status(p)])
    done  = len([p for p in pages if "Completada" in str(get_status(p))])
    pct = round((done / total) * 100) if total else 0

    return {
        "name": name, "ko": ko,
        "ttff": ttff, "ttff_real": f_estado and "Completada" in f_estado,
        "dist": dist,  "dist_real": d_estado and "Completada" in d_estado,
        "ttv": ttv,    "comp_fin": c_fin,
        "elapsed": elapsed, "rem": rem,
        "atrasado": atrasado,
        "f_atr": f_atr, "d_atr": d_atr, "c_atr": c_atr,
        "pct": pct,
    }

def calc_averages(clients):
    avgs = [c for c in clients if c["name"] != "Puppis Arg"]
    ttff_v = [c["ttff"] for c in avgs if c["ttff"]]
    dist_v = [c["dist"] for c in avgs if c["dist"]]
    ttv_v  = [c["ttv"]  for c in avgs if c["ttv"]]
    no_cv  = [c["ttv"]  for c in avgs if c["ttv"] and c["name"] != "Cruz Verde"]
    avg = lambda v: round(sum(v)/len(v), 1) if v else 0
    return avg(ttff_v), avg(dist_v), avg(ttv_v), avg(no_cv)

def badge(c):
    if c["rem"] == 0 and not c["atrasado"]:
        return "b-gr", "Go-live ✓"
    if c["atrasado"]:
        return "b-re", "Atrasado"
    if c["name"] in ["MAJA", "Tiendas 3B", "Puppis Arg"]:
        return "b-gr", "Cerca go-live"
    return "b-am", "En progreso"

def golive_badge(c):
    rem = c["rem"]
    if rem is None:   return "gl-na", "sin fecha"
    if rem == 0:      return "gl-done", "Go-live ✓"
    if rem < 3:       return "gl-hot", f"{rem} sem → go-live"
    return "gl-mid", f"{rem} sem → go-live"

def metric_val(val, real, atrasado):
    if val is None:
        return '<div class="m-val na">—</div>'
    color = "var(--re)" if atrasado else ("var(--gr)" if real else "var(--mu2)")
    warn = "⚠" if atrasado else ""
    return f'<div class="m-val" style="color:{color}">{val}{warn}</div>'

def render_card(c, extra_class=""):
    b_cls, b_txt = badge(c)
    g_cls, g_txt = golive_badge(c)
    pct = c["pct"]
    gen_color = "var(--re)" if c["atrasado"] else ("var(--gr)" if pct > 70 else "var(--ac)")
    outlier_tag = '<span style="font-size:9px;color:var(--am);font-family:\'DM Mono\',monospace">outlier</span>' if c["name"] == "Cruz Verde" else ""
    ko_str = c['ko'].strftime('%-d %b %Y') if c['ko'] else '—'
    return f"""
    <div class="cc {extra_class}">
      <div class="cc-top">
        <div><div class="cc-name">{c['name']} {outlier_tag}</div><div class="cc-meta">kickoff {ko_str}</div></div>
        <div class="cc-right"><span class="badge {b_cls}">{b_txt}</span><span class="golive {g_cls}">{g_txt}</span></div>
      </div>
      <div class="prow"><span class="pl">General</span><div class="pt"><div class="pf" style="width:{pct}%;background:{gen_color}"></div></div><span class="pp">{pct}%</span></div>
      <div class="cc-metrics">
        <div class="m-item">{metric_val(c['ttff'], c['ttff_real'], c['f_atr'])}<div class="m-lbl">TtFF sem</div></div>
        <div class="m-item">{metric_val(c['dist'], c['dist_real'], c['d_atr'])}<div class="m-lbl">TtA sem</div></div>
        <div class="m-item">{metric_val(c['ttv'],  False,          c['c_atr'])}<div class="m-lbl">TTV sem</div></div>
      </div>
    </div>"""

def generate_html(clients, avg_ttff, avg_dist, avg_ttv, no_cv_ttv):
    today_str = TODAY.strftime("%-d de %B %Y")
    golive    = sum(1 for c in clients if c["rem"] == 0 and not c["atrasado"] and c["name"] != "Puppis Arg")
    atrasados = sum(1 for c in clients if c["atrasado"] and c["name"] != "Puppis Arg")
    en_prog   = 9 - golive - atrasados

    chart_clients = [c for c in clients if c["name"] != "Puppis Arg"]
    chart_clients.sort(key=lambda c: c["ttv"] or 0, reverse=True)

    card_order = ["Cruz Verde","Fybeca","Neto","Puppis Col","Puppis Arg",
                  "Mi Comisariato","MAJA","Tuvacol","Tiendas 3B","MiCorral"]
    cards_html = ""
    puppis_done = False
    for name in card_order:
        c = next((x for x in clients if x["name"] == name), None)
        if not c: continue
        if name == "Puppis Col" and not puppis_done:
            c_arg = next((x for x in clients if x["name"] == "Puppis Arg"), None)
            cards_html += '\n    <div style="grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:12px">'
            cards_html += render_card(c, "outlier golive-done")
            if c_arg: cards_html += render_card(c_arg)
            cards_html += '\n    </div>'
            puppis_done = True
            continue
        if name == "Puppis Arg": continue
        extra = "outlier" if name in ["Cruz Verde","Fybeca","Neto","Mi Comisariato"] else ""
        cards_html += render_card(c, extra)

    MAX, META = 75, 24
    meta_pct = (META / MAX) * 100
    chart_rows = ""
    for c in chart_clients:
        el_pct  = min((c["elapsed"] / MAX) * 100, 100)
        rem     = c["rem"] or 0
        ttv     = c["ttv"] or 0
        ttv_pct = min((ttv / MAX) * 100, 100)
        over    = ttv > META
        near    = 0 < rem < 3
        rem_color  = "#3ecf8e" if near else "#f5a623"
        bar_color  = "#f25f5c" if c["name"] == "Cruz Verde" else "#5b8fff"
        if rem == 0:
            bar_inner = f'<div style="height:100%;width:{ttv_pct:.1f}%;background:#3ecf8e;opacity:.5;border-radius:3px"></div>'
        else:
            rem_pct = min((rem / MAX) * 100, 100 - el_pct)
            bar_inner = (f'<div style="height:100%;width:{el_pct:.1f}%;background:{bar_color};opacity:.8;'
                         f'border-radius:3px 0 0 3px;display:inline-block;vertical-align:top"></div>')
            if rem_pct > 0:
                bar_inner += (f'<div style="height:100%;width:{rem_pct:.1f}%;background:{rem_color};opacity:.95;'
                              f'border-radius:0 3px 3px 0;display:inline-block;vertical-align:top"></div>')
        over_div = (f'<div style="position:absolute;top:50%;transform:translateY(-50%);left:{meta_pct:.1f}%;'
                    f'width:{max(ttv_pct-meta_pct,0):.1f}%;height:14px;background:rgba(242,95,92,0.12);'
                    f'z-index:1;border-radius:0 3px 3px 0"></div>') if over else ""
        rem_txt  = "✓ go-live" if rem == 0 else f"{rem} sem rest."
        rem_clr  = "var(--gr)" if rem == 0 else ("#3ecf8e" if near else "#f5a623")
        name_cls = " out" if c["name"] == "Cruz Verde" else ""
        chart_rows += f"""
    <div class="chart-row">
      <div><div class="cr-name{name_cls}">{c['name']}</div><div class="cr-sub">TTV est. {ttv} sem</div></div>
      <div class="bar-area">
        <div style="position:absolute;top:0;bottom:0;left:{meta_pct:.1f}%;width:1.5px;background:rgba(255,255,255,0.2);z-index:2">
          <span style="position:absolute;top:-15px;left:50%;transform:translateX(-50%);font-size:8px;font-family:DM Mono,monospace;color:var(--mu);white-space:nowrap">meta 24</span>
        </div>
        {over_div}
        <div style="position:absolute;top:50%;transform:translateY(-50%);left:0;right:0;height:14px;background:var(--s2);border-radius:3px;overflow:hidden;display:flex">{bar_inner}</div>
      </div>
      <div class="cr-nums"><div class="cr-el">{ttv} sem TTV</div><div class="cr-rem" style="color:{rem_clr}">{rem_txt}</div></div>
    </div>"""

    cv_ttv = next((c["ttv"] for c in chart_clients if c["name"] == "Cruz Verde"), "—")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Implementaciones — Celes</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,400;0,500;1,400&family=Sora:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0d0f14;--s1:#13161d;--s2:#1a1e28;--b1:rgba(255,255,255,0.07);--b2:rgba(255,255,255,0.13);--tx:#e8eaf0;--mu:#5e6478;--mu2:#8891a8;--ac:#5b8fff;--ac-s:rgba(91,143,255,0.1);--gr:#3ecf8e;--gr-s:rgba(62,207,142,0.1);--am:#f5a623;--am-s:rgba(245,166,35,0.1);--re:#f25f5c;--re-s:rgba(242,95,92,0.1)}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Sora',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh;padding-bottom:5rem}}
.topbar{{display:flex;align-items:center;justify-content:space-between;padding:1.1rem 2.5rem;border-bottom:1px solid var(--b1);position:sticky;top:0;background:rgba(13,15,20,0.92);z-index:10;backdrop-filter:blur(12px)}}
.logo{{font-size:12px;font-weight:600;letter-spacing:.14em;color:var(--mu2);text-transform:uppercase}}
.logo span{{color:var(--ac)}}
.update{{font-family:'DM Mono',monospace;font-size:11px;color:var(--mu);background:var(--s2);border:1px solid var(--b2);padding:4px 12px;border-radius:20px}}
.update b{{color:var(--mu2);font-weight:500}}
.page{{max-width:1100px;margin:0 auto;padding:2.5rem 2rem}}
.slabel{{font-size:10px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;color:var(--mu);margin-bottom:.9rem;margin-top:2.5rem}}
.slabel:first-child{{margin-top:0}}
.ns-top{{border:1px solid var(--b2);border-radius:16px;overflow:hidden;margin-bottom:1px}}
.ns-card{{background:var(--s1);padding:1.75rem 2rem 1.5rem}}
.ns-card.center{{text-align:center;padding:1.75rem 30%}}
.ns-icon{{font-size:15px;margin-bottom:.5rem}}
.ns-tag{{font-size:9px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--mu);margin-bottom:.35rem}}
.ns-val{{font-size:42px;font-weight:300;color:var(--tx);line-height:1;letter-spacing:-.03em}}
.ns-val .u{{font-size:16px;color:var(--mu2);margin-left:3px}}
.ns-val.warn{{color:var(--am)}}
.ns-target{{display:inline-block;font-size:10px;font-family:'DM Mono',monospace;padding:3px 8px;border-radius:4px;margin-top:.55rem}}
.ns-target.bad{{color:var(--am);background:var(--am-s)}}
.ns-meta{{font-size:10.5px;color:var(--mu);margin-top:.5rem;line-height:1.6}}
.ns-sub{{font-size:10px;color:var(--mu);font-family:'DM Mono',monospace;margin-top:.35rem}}
.ns-sub span{{color:var(--mu2)}}
.ns-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--b2);border:1px solid var(--b2);border-radius:16px;overflow:hidden;margin-bottom:.75rem}}
.defs{{background:var(--s2);border-left:2px solid var(--ac);border-radius:0 8px 8px 0;padding:.8rem 1.2rem;margin-bottom:.6rem;font-size:11px;color:var(--mu2);line-height:1.75}}
.defs strong{{color:var(--tx);font-weight:500}}
.outlier-note{{background:var(--s2);border-left:2px solid var(--am);border-radius:0 8px 8px 0;padding:.8rem 1.2rem;margin-bottom:1.75rem;font-size:11px;color:var(--mu2);line-height:1.7}}
.outlier-note strong{{color:var(--tx);font-weight:500}}
.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:2rem}}
.kpi{{background:var(--s1);border:1px solid var(--b1);border-radius:12px;padding:1.2rem;text-align:center}}
.kpi-n{{font-size:34px;font-weight:300;letter-spacing:-.03em;line-height:1}}
.kpi-l{{font-size:11px;color:var(--mu2);margin-top:5px}}
.cgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.cc{{background:var(--s1);border:1px solid var(--b1);border-radius:14px;padding:1.35rem;transition:border-color .2s}}
.cc:hover{{border-color:var(--b2)}}
.cc.outlier{{border-color:rgba(245,166,35,0.22)}}
.cc.golive-done{{border-color:rgba(62,207,142,0.3)}}
.cc-top{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.1rem;gap:6px}}
.cc-name{{font-size:13px;font-weight:500;line-height:1.3}}
.cc-meta{{font-size:10px;color:var(--mu);margin-top:3px}}
.cc-right{{display:flex;flex-direction:column;align-items:flex-end;gap:5px;flex-shrink:0}}
.badge{{font-size:9px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;border-radius:6px;white-space:nowrap}}
.b-gr{{background:var(--gr-s);color:var(--gr)}}.b-am{{background:var(--am-s);color:var(--am)}}.b-re{{background:var(--re-s);color:var(--re)}}
.golive{{font-family:'DM Mono',monospace;font-size:10px;font-weight:500;padding:3px 8px;border-radius:6px;white-space:nowrap}}
.gl-hot{{background:var(--gr-s);color:var(--gr)}}.gl-mid{{background:var(--am-s);color:var(--am)}}.gl-na{{background:var(--b1);color:var(--mu)}}.gl-done{{background:var(--gr-s);color:var(--gr)}}
.prow{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.pl{{font-family:'DM Mono',monospace;font-size:10px;color:var(--mu);width:56px;flex-shrink:0}}
.pt{{flex:1;height:3px;background:var(--s2);border-radius:99px;overflow:hidden}}
.pf{{height:100%;border-radius:99px}}
.pp{{font-family:'DM Mono',monospace;font-size:10px;color:var(--mu2);width:26px;text-align:right}}
.cc-metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:.9rem;padding-top:.9rem;border-top:1px solid var(--b1)}}
.m-item{{text-align:center;padding:7px 4px;background:var(--s2);border-radius:7px}}
.m-val{{font-family:'DM Mono',monospace;font-size:12px;font-weight:500;color:var(--tx)}}
.m-val.na{{color:var(--mu)}}
.m-lbl{{font-size:8.5px;color:var(--mu);letter-spacing:.04em;text-transform:uppercase;margin-top:2px}}
.chart-section{{margin-top:2.5rem}}
.chart-row{{display:grid;grid-template-columns:148px 1fr 100px;align-items:center;padding:10px 0;border-top:1px solid var(--b1)}}
.chart-row:last-child{{border-bottom:1px solid var(--b1)}}
.cr-name{{font-size:12px;font-weight:500;padding-right:14px}}
.cr-name.out{{color:var(--am)}}
.cr-sub{{font-size:10px;color:var(--mu);margin-top:2px}}
.bar-area{{position:relative;height:32px}}
.cr-nums{{text-align:right;padding-left:12px}}
.cr-el{{font-family:'DM Mono',monospace;font-size:10px;color:var(--mu2)}}
.cr-rem{{font-family:'DM Mono',monospace;font-size:11px;font-weight:500;margin-top:1px}}
@keyframes up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
.ns-top,.ns-grid{{animation:up .45s ease both}}
.defs,.outlier-note{{animation:up .45s .04s ease both}}
.kpi-row{{animation:up .45s .08s ease both}}
.cgrid{{animation:up .45s .13s ease both}}
.chart-section{{animation:up .45s .18s ease both}}
</style>
</head>
<body>
<div class="topbar">
  <div class="logo"><span>Celes</span> · Implementaciones</div>
  <div class="update">Actualización: <b>{today_str}</b></div>
</div>
<div class="page">
  <div class="slabel">North star metrics — promedios del área · 9 clientes (Puppis = 1)</div>
  <div class="ns-top">
    <div class="ns-card center">
      <div class="ns-icon">⭐</div>
      <div class="ns-tag">TTV · Time to Value</div>
      <div class="ns-val warn">{avg_ttv} <span class="u">sem</span></div>
      <div class="ns-target bad">Meta ≤ 24 sem · 9 clientes</div>
      <div class="ns-meta">Kickoff → Activación Módulo de Compras</div>
      <div class="ns-sub">Sin Cruz Verde: <span>{no_cv_ttv} sem</span></div>
    </div>
  </div>
  <div class="ns-grid">
    <div class="ns-card">
      <div class="ns-icon">⚡</div>
      <div class="ns-tag">TtFF · Time to First Forecast</div>
      <div class="ns-val warn">{avg_ttff} <span class="u">sem</span></div>
      <div class="ns-target bad">Meta ≤ 8 sem · 8 clientes</div>
      <div class="ns-meta">Kickoff → Forecast activo en producción</div>
    </div>
    <div class="ns-card">
      <div class="ns-icon">🚀</div>
      <div class="ns-tag">TtA · Time to Activation</div>
      <div class="ns-val warn">{avg_dist} <span class="u">sem</span></div>
      <div class="ns-target bad">Meta ≤ 10 sem · 8 clientes</div>
      <div class="ns-meta">Kickoff → Distribución go-live</div>
    </div>
  </div>
  <div class="defs">
    <strong>TtFF</strong> kickoff → forecast activo &nbsp;·&nbsp; <strong>TtA</strong> kickoff → distribución go-live &nbsp;·&nbsp; <strong>TTV</strong> kickoff → activación módulo compras &nbsp;·&nbsp; ⚠️ = hito vencido sin completar
  </div>
  <div class="outlier-note">
    <strong>Cruz Verde</strong> (kickoff ene 2025 · {cv_ttv} sem TTV) incluido en promedio, marcado outlier visual. Sin CV: TTV <strong>{no_cv_ttv} sem</strong>. Hitos vencidos sin completar → marcados ⚠️ Atrasado.
  </div>
  <div class="slabel">Pipeline · semana {TODAY.strftime('%-d %b %Y')}</div>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-n" style="color:var(--ac)">9</div><div class="kpi-l">Clientes activos</div></div>
    <div class="kpi"><div class="kpi-n" style="color:var(--gr)">{golive}</div><div class="kpi-l">Go-live completo</div></div>
    <div class="kpi"><div class="kpi-n" style="color:var(--am)">{en_prog}</div><div class="kpi-l">En progreso</div></div>
    <div class="kpi"><div class="kpi-n" style="color:var(--re)">{atrasados}</div><div class="kpi-l">Atrasado</div></div>
  </div>
  <div class="slabel">Estado por cliente</div>
  <div class="cgrid">
    {cards_html}
  </div>
  <div class="chart-section">
    <div class="slabel">Camino al go-live de Compras — de más lejos a más cerca</div>
    <p style="font-size:11px;color:var(--mu2);margin-bottom:1.25rem;line-height:1.6">Azul = semanas transcurridas · Ámbar/Verde = restantes · Línea = meta TTV 24 sem</p>
    <div style="display:flex;gap:1.25rem;margin-bottom:1.5rem;flex-wrap:wrap">
      <div style="display:flex;align-items:center;gap:7px;font-size:11px;color:var(--mu2)"><div style="width:13px;height:11px;border-radius:2px;background:#5b8fff;opacity:.8"></div>Transcurridas</div>
      <div style="display:flex;align-items:center;gap:7px;font-size:11px;color:var(--mu2)"><div style="width:13px;height:11px;border-radius:2px;background:#f5a623"></div>Restantes</div>
      <div style="display:flex;align-items:center;gap:7px;font-size:11px;color:var(--mu2)"><div style="width:13px;height:11px;border-radius:2px;background:#3ecf8e"></div>Restantes &lt; 3 sem</div>
    </div>
    {chart_rows}
  </div>
  <div style="font-size:11px;color:var(--mu);text-align:center;margin-top:3rem;font-family:'DM Mono',monospace">
    generado automáticamente · celes cs &amp; implementaciones · {today_str}
  </div>
</div>
</body>
</html>"""

# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Leyendo cronogramas de Notion...")
    clients = []

    # Neto: datos desde Excel, valores fijos actualizables aquí
    neto_comp = date(2026, 4, 24)
    neto_rem  = max(round((neto_comp - TODAY).days / 7, 1), 0)
    neto = {
        "name": "Neto", "ko": KICKOFFS["Neto"],
        "ttff": 28.9, "ttff_real": False,
        "dist": 29.3, "dist_real": False,
        "ttv": 41.9,  "comp_fin": neto_comp,
        "elapsed": min(weeks(KICKOFFS["Neto"], TODAY), 41.9),
        "rem": neto_rem,
        "atrasado": True, "f_atr": True, "d_atr": True, "c_atr": False,
        "pct": 61,
    }
    clients.append(neto)

    for name, db_id in CRONOGRAMAS.items():
        print(f"  → {name}")
        try:
            c = get_client_data(name, db_id)
            c["name"] = name
            clients.append(c)
        except Exception as e:
            print(f"    ERROR: {e}")

    avg_ttff, avg_dist, avg_ttv, no_cv = calc_averages(clients)
    print(f"\nPromedios: TtFF={avg_ttff} TtA={avg_dist} TTV={avg_ttv} (sin CV: {no_cv})")

    html = generate_html(clients, avg_ttff, avg_dist, avg_ttv, no_cv)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ index.html generado correctamente")
