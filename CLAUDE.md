# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Celes Implementation Dashboard — tracks 9–10 active clients across LATAM implementing Celes's supply chain platform. Auto-refreshes every 3 days via GitHub Actions pulling from Notion + one static Excel file.

## Commands

### Frontend (Next.js)
```bash
npm install
npm run dev          # localhost:3000
npm run build        # production build
npm run lint
```

Static export for GitHub Pages:
```bash
npm run build        # outputs to /out when next.config.js has output: 'export'
```

### Python data pipeline
```bash
pip install requests pandas openpyxl

export NOTION_TOKEN=ntn_...
python scripts/generate_dashboard.py   # writes public/data.json
```

Run locally to validate data before pushing: `npm run dev` reads from `public/data.json` at build time.

### GitHub Actions
Manual trigger: Actions → "Actualizar Dashboard" → Run workflow.
Automatic: runs every 3 days at 08:00 UTC.

---

## Architecture

Two decoupled layers connected by `public/data.json`:

```
Notion API (9 clients) ─┐
                         ├─► generate_dashboard.py ─► public/data.json ─► Next.js SSG ─► GitHub Pages
Excel (Neto only)       ─┘
```

**Why static generation:** data changes every 3 days, not in real time. `output: 'export'` in `next.config.js` lets GitHub Pages serve pre-built HTML with zero server.

**`public/data.json`** is the sole contract between Python and TypeScript. The frontend never calls Notion directly. See `src/lib/types.ts` for the full TypeScript interfaces (`DashboardData`, `Client`, `Hito`).

---

## Data Pipeline (`scripts/generate_dashboard.py`)

### Reading Notion properties — CRITICAL

Notion property names vary by client database. Always iterate by **type**, not by name:

```python
def get_title(page):        # type == "title"
def get_status(page):       # type == "status", keys "Estado" or "Status"
def get_fecha_fin(page):    # checks "Fecha Fin" then "Fin" then "Plazo"
                            # "Fecha Fin" is a formula in some DBs → reads formula.date.start
                            # "Fin" is a plain date in others → reads date.start/end
```

### Milestone detection

Hitos are matched case-insensitively against these aliases:

| Key | Aliases |
|-----|---------|
| `forecast` | "activación módulo de forecast", "activación y configuración módulo de pronóstico de demanda" |
| `distribucion` | "activación módulo de distribución", "despliegue en productivo: módulo distribución" |
| `compras` | "activación módulo de compras", "pruebas y aceptación módulo de compras" |

### Neto exception

Neto's schedule lives in `data/Cronograma_Neto_V3.xlsx` (not in Notion). Columns: `#, Módulo, Actividad, Responsable, Estado, # de Días, Fecha inicio, Fecha Fin`. Match milestones by regex on the `Actividad` column.

### Client flags

| Flag | Meaning |
|------|---------|
| `in_average: false` | Puppis Arg — excluded from all area averages |
| `is_outlier_visual: true` | Cruz Verde — shown with amber border, included in averages but highlighted |
| Puppis rule | Puppis Col + Puppis Arg = 1 logical client in the system; Col is the primary for averages |

### `atrasado` formula

```python
atrasado = (fecha_fin < date.today()) and (estado != "Completada")
```

---

## Frontend Components

| Component | Responsibility |
|-----------|---------------|
| `NSMetrics` | TTV (prominent center), TtFF + TtA below. Shows "sin Cruz Verde" as secondary stat. Badge red/amber/green vs. target. |
| `KPIRow` | 3 pills: total active, en progreso, atrasado |
| `ClientCard` | Per-client card with progress bar, module bars (color by state), TtFF/TtA/TTV chips in footer |
| `ClientGrid` | 3-col grid; Puppis Col + Puppis Arg render as a 2-col subgrid spanning a full row |
| `TimelineChart` | Horizontal bars ordered by TTV desc. Vertical line at 24 weeks ("meta TTV"). Red zone if TTV > 24. |
| `TopBar` | Sticky header with `updated_at` date |

Client card display order: Cruz Verde → Fybeca → Neto → [Puppis Col + Puppis Arg] → Mi Comisariato → MAJA → Tuvacol → Tiendas 3B → MiCorral.

---

## Design Tokens

```css
--bg: #0d0f14;   --s1: #13161d;   --s2: #1a1e28;
--ac: #5b8fff;   --gr: #3ecf8e;   --am: #f5a623;   --re: #f25f5c;
--tx: #e8eaf0;   --mu: #5e6478;   --mu2: #8891a8;
```

Fonts: **Sora** (UI), **DM Mono** (metrics/numbers).

---

## North Star Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| TtFF | Kickoff → Forecast module activation | ≤ 8 weeks |
| TtA | Kickoff → Distribution module go-live | ≤ 10 weeks |
| TTV ⭐ | Kickoff → Purchases module activation | ≤ 24 weeks |

Kickoff = `fecha_fin` of hito #1 (Kick Off / Planeación) in each client's schedule.
Averages computed over 9 clients (Puppis Arg excluded). Cruz Verde included but flagged as outlier.

---

## Deployment

**GitHub Pages** (current):
```js
// next.config.js
{ output: 'export', basePath: '/statusimplementationpipeline', images: { unoptimized: true } }
```

**Vercel** (alternative): remove `output: 'export'` and `basePath`, connect repo on vercel.com.

Required GitHub secret: `NOTION_TOKEN` (integration "status implementation pipeline").

---

## Notion Database IDs

| Client | Database ID |
|--------|-------------|
| Cruz Verde | `17c63390-2d83-8111-8fe8-000b617b7e29` |
| Mi Comisariato | `2ca63390-2d83-8155-ae74-000b0738252c` |
| Fybeca | `25463390-2d83-8115-a5f2-000b97b006d6` |
| MAJA | `33663390-2d83-8342-a2f5-8768c72128da` |
| Tuvacol | `31163390-2d83-810e-88f8-000b138394ad` |
| Tiendas 3B | `32263390-2d83-8177-9465-000bc1938d67` |
| MiCorral | `06b63390-2d83-83fa-b1b5-07954f01b376` |
| Puppis Col | `27663390-2d83-81bc-8f6d-000b397ba9d9` |
| Puppis Arg | `42163390-2d83-83db-b015-87aeb58fc21c` |
