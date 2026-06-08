# `arcline` — Implementation Plan

> Status: **Phase 1.5 Complete (Historian shipped) / v0.2.0-dev**
> Last updated: 2026-06-09
> Audience: maintainers and contributors of the `arcline` framework.
> This document is the **single source of truth for design intent**. It supersedes ad-hoc notes and is updated whenever scope or architecture changes.

> **Phase progress:**
> - ✅ **Phase 1**   — Graph + I/O + Dashboard (MVP) — **DONE** (see §3 and §13)
> - ✅ **Phase 1.5** — Historian & Analytics — **DONE** (114 passed / 2 skipped; see §6.7 and §14)
> - ⏳ **Phase 2**   — Optimization (Pyomo) — *planned*
> - ⏳ **Phase 3**   — Scenarios & Sensitivity — *planned*

> **Naming convention (enforced):** All Python identifiers — functions, methods, attributes, parameters, locals — are **camelCase**. Exemptions: `def test_*` (pytest), dunders, environment variables (`ARCLINE_*`), and external library kwargs we forward verbatim (Dash props, pandas kwargs). Enforced by `tools/check_camel_case.py` (CI gate; 0 violations as of v0.2.0-dev).

---

## 1. Vision & Scope

`arcline` is a Python framework that treats **a supply chain as a directed multi-graph** and turns the network itself into the first-class modeling object. The library must let a practitioner:

1. **Model** a supply chain as typed nodes (Supplier, Plant, Warehouse/DC, Customer) and typed edges (Lane, Production, Storage) with rich, validated attributes.
2. **Persist** that network as portable, git-versionable artifacts (JSON / YAML / Parquet).
3. **Visualize and edit** it in an interactive **Dash** dashboard with full CRUD on nodes and edges, and a dedicated `dashboard/visualize` view that renders the entire network (abstract layout *or* geographic map when coordinates exist).
4. **Pull historic performance** for any node/edge attribute (e.g., the historic lead-time series for a `Lane` between a port and a supplier) from a **MS-SQL Server** data warehouse and analyse it (time series, distribution, summary stats, rolling stats) directly inside the dashboard.
5. **Optimize** flow, sourcing, facility-location, and capacity decisions on the network using **Pyomo** as the modeling layer with a solver-agnostic backend (CBC, HiGHS, Gurobi, CPLEX).
6. **Compare scenarios** (what-if, sensitivity, share-of-business) with reproducible, auditable results.

The non-goal is to reinvent solvers, geocoders, or general-purpose graph libraries. `arcline` is the **modeling, I/O, dashboard, and orchestration layer** that sits between `networkx`/`igraph` (graph storage) and Pyomo + LP/MILP solvers (math), and exposes the result through Dash.

---

## 2. Locked Design Decisions

These were chosen up-front and the plan below assumes them:

| Concern                  | Decision                                                                                  |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| **Dashboard stack**      | **Dash + Plotly** (production analytics oriented)                                         |
| **Persistence**          | **File-based** project folder: JSON/YAML for schema, Parquet for tabular bulk data        |
| **Historic data source** | **MS-SQL Server** via **SQLAlchemy Core + pyodbc**; on-demand fetch + local Parquet cache |
| **Optimization layer**   | **Pyomo** (MILP/LP) with solver-agnostic backend (CBC default, HiGHS, Gurobi, CPLEX)      |
| **Graph viz**            | **Plotly** (`Scattergl` for abstract layouts, `Scattermapbox` for geo)                    |
| **Phasing**              | (1) Graph + I/O + Dashboard → (1.5) Historian + Analytics → (2) Optimization → (3) Scenarios & Sensitivity |
| **Geospatial**           | **Optional** lat/lon on nodes; geo view only when coords exist, else force-directed/tiered |
| **Built-in taxonomy**    | **Yes** — ship `Supplier`, `Plant`, `Warehouse`, `Customer`, `Lane`, `Production`, `Storage` |
| **Graph backend**        | `networkx.MultiDiGraph` (default), `igraph` (for >1M edges) — already abstracted          |
| **Validation**           | `pydantic` v2 (already in use in `graph/base/`)                                           |
| **Python**               | ≥ 3.12                                                                                    |

---

## 3. Current State (snapshot — Phase 1 complete)

```
arcline/
├── __init__.py
├── graph/
│   ├── __init__.py
│   ├── nodes.py                 # DefaultNode (concrete)
│   ├── edges.py                 # DefaultEdge (concrete)
│   ├── registry.py              # kind ↔ class registry (lazy)
│   ├── builder.py               # NetworkBuilder (fluent assembly)
│   ├── base/
│   │   ├── nodes.py             # AbstractNode (+ lat/lon fields)
│   │   ├── edges.py             # AbstractEdge
│   │   └── graph.py             # AbstractGraph (cached indices,
│   │                            #   addNode/addEdge/updateNode/...)
│   ├── backends/
│   │   └── networkx.py          # NetworkXGraph (full mutator surface)
│   ├── library/                 # built-in taxonomy
│   │   ├── supplier.py · plant.py · warehouse.py · customer.py
│   │   └── lane.py · production.py · storage.py
│   └── icons/                   # warehouse / conveyor / vendor / graph
├── utils/                       # hashing · logging · geo
├── io/                          # schema · validators · readers ·
│                                #   writers · project
├── historian/                   # ── Phase 1.5 ──
│   ├── exceptions.py            # HistorianError hierarchy
│   ├── spec.py                  # HistorySpec (frozen pydantic) + HistorianMixin
│   ├── connection.py            # DSN env discovery, lazy SA engine,
│   │                            #   redactDsn, testConnection
│   ├── fetcher.py               # buildQuery (whitelisted idents) + fetch
│   ├── cache.py                 # Parquet cache; specHash invalidation
│   ├── analytics.py             # summary · rolling · distribution · resample
│   └── registry.py              # iterCatalog / specFor / attributesFor
├── cli/                         # typer app: init / validate / dashboard /
│   ├── main.py                  #   history sync|clear|validate
│   ├── commands.py
│   └── history.py               # historian CLI subgroup
└── dashboard/                   # Dash multi-page app
    ├── app.py · config.py · server.py
    ├── state/  (store · session w/ RLock + command pattern)
    ├── components/  (navbar w/ DB-status pill · node_form · edge_form ·
    │                data_table · kpi_cards)
    ├── viz/  (styles · layouts · plotly_graph)
    ├── pages/  (home · nodes · edges · visualize · history ·
    │           solve/scenarios placeholders)
    ├── callbacks/  (nodes_cb · edges_cb · visualize_cb · history_cb)
    └── assets/styles.css

examples/
├── toy_3node/                   # runnable Supplier → Plant → Customer
└── historian_schema.sql         # documented MS-SQL DDL for the catalog
tests/                           # 114 tests + 2 skipped, pytest -q ≈ 9 s
tools/check_camel_case.py        # AST naming guardrail (CI)
pyproject.toml                   # core + [dashboard] + [historian] +
                                 #   [igraph] + [dev]
```

**Phase 1 delivered:** typed taxonomy with pydantic validation, kind
registry, fluent `NetworkBuilder`, file-based `Project` with flat-array
`nodes.json` / `edges.json` and `manifest.yaml`, severity-coded
validator (`orphan-edge`, `duplicate-node-key`, `self-loop-edge`,
`unknown-*-kind`, `latitude/longitude-out-of-range`, schema-version
drift), CLI (`arcline init / validate / dashboard`) with friendly
errors, multi-page Dash app with CRUD on nodes/edges and three viz
layouts (spring / tiered / geo via Scattermapbox), 58 passing tests
including a `dash[testing]` smoke suite, runnable
`examples/toy_3node/` project, and a perf pass (graph index caching up
to 341×, lazy heavy imports cutting CLI cold-start 1.6×).

**Phase 1 implementation log (master branch):**

| Commit    | Batch         | Notes                                       |
|-----------|---------------|---------------------------------------------|
| `ddc2ee7` | 🏗️ A — graph  | taxonomy, registry, builder, NetworkXGraph |
| `7926444` | 📦 B — io/cli | Project, validators, CLI, utils            |
| `b0f35f3` | 🖥️ C+D — dash | full Dash multi-page app                   |
| `25d4b41` | ✅ E — tests  | pyproject, example, 46 tests               |
| `9c06ab6` | 🐛 fixes      | all P0 + key P1s (reviewer + debugger)     |
| `f1b3382` | ⚡ perf       | index cache + lazy imports (up to 341×)    |

**Phase 1.5 implementation log (master branch):**

| Commit    | Batch                  | Notes                                                       |
|-----------|------------------------|-------------------------------------------------------------|
| `8541ffa` | 🐫 R1–R8 refactor      | strict camelCase across dashboard / io / utils / cli / tests |
| `66ea772` | 🛡️ guardrail           | `tools/check_camel_case.py` AST checker + CI gate           |
| `fcf01c6` | 🧱 P15-1 foundation    | `historian.spec.HistorySpec` + `HistorianMixin`             |
| `f6c8330` | 🔌 P15-2 connection    | DSN env discovery + lazy SA engine + `testConnection`       |
| `35dd277` | 📥 P15-3 fetcher+cache | parameterized SQL + Parquet cache w/ specHash invalidation  |
| `ee21537` | 📊 P15-4 analytics     | summary / rolling / distribution / resample                 |
| `6161536` | 📚 P15-5 catalog       | HistorySpec on Lane / Plant / Warehouse / Customer + DDL    |
| `4fbf5a4` | 🛠️ P15-6 CLI           | `arcline history sync|clear|validate`                       |
| `cde3c01` | 🖥️ P15-7 dashboard     | `/dashboard/history` + DB-status pill + deep-link           |
| *(this)*  | 🐛 audit fixes         | distribution NaN crash · clearCache scope guard · navbar TTL · sync skipCount · timeout wired |

---

## 4. Target Package Layout (end-state)

```
arcline/
├── __init__.py                  # public API surface (lazy re-exports)
├── _version.py                  # __version__ source of truth
├── api/                         # curated public API; re-exports from internal modules
│   └── __init__.py
│
├── graph/                       # ── existing core, extended ──
│   ├── base/                    # AbstractNode / AbstractEdge / AbstractGraph (exists)
│   ├── nodes.py                 # DefaultNode (exists)
│   ├── edges.py                 # DefaultEdge (exists)
│   ├── library/                 # NEW — built-in supply-chain taxonomy
│   │   ├── __init__.py
│   │   ├── supplier.py          # Supplier(AbstractNode)
│   │   ├── plant.py             # Plant(AbstractNode)
│   │   ├── warehouse.py         # Warehouse / DistributionCenter
│   │   ├── customer.py          # Customer / DemandPoint
│   │   ├── lane.py              # Lane(AbstractEdge) — transport
│   │   ├── production.py        # Production(AbstractEdge) — intra-plant
│   │   └── storage.py           # Storage(AbstractEdge) — holding
│   ├── backends/
│   │   ├── networkx.py          # exists
│   │   └── igraph.py            # NEW — large-graph backend
│   ├── registry.py              # NEW — type registry (kind ↔ class) for (de)serialization
│   ├── builder.py               # NEW — fluent NetworkBuilder() helper
│   └── icons/                   # png assets (exists)
│
├── io/                          # NEW — pure I/O layer (no UI)
│   ├── __init__.py
│   ├── project.py               # Project folder layout, manifest.yaml
│   ├── readers.py               # from_json / from_yaml / from_parquet / from_csv
│   ├── writers.py               # to_json / to_yaml / to_parquet
│   ├── schema.py                # JSON-schema for nodes.json / edges.json
│   └── validators.py            # cross-file integrity checks (orphan edges, dup keys)
│
├── historian/                   # NEW — Phase 1.5: MS-SQL historic data layer
│   ├── __init__.py
│   ├── connection.py            # SQLAlchemy engine factory; reads ARCLINE_MSSQL_DSN
│   ├── spec.py                  # HistorySpec pydantic model (table, keyCol, valueCol, tsCol, filters)
│   ├── fetcher.py               # Generic fetch(spec, hashKey, range) -> pandas.DataFrame
│   ├── cache.py                 # Parquet cache under <project>/.cache/history/
│   ├── analytics.py             # univariate stats: summary, rolling, distribution bins
│   ├── registry.py              # (kind, attribute) -> HistorySpec lookup helpers
│   └── exceptions.py            # ConnectionError, SpecError, EmptyHistoryError
│
├── optim/                       # NEW — Phase 2: Pyomo modeling
│   ├── __init__.py
│   ├── solvers.py               # solver factory (cbc/highs/gurobi/cplex)
│   ├── models/
│   │   ├── min_cost_flow.py
│   │   ├── facility_location.py
│   │   ├── multi_period_flow.py
│   │   └── share_of_business.py
│   ├── compiler.py              # AbstractGraph → pyomo.ConcreteModel
│   ├── results.py               # SolveResult dataclass, KPI extractors
│   └── registry.py              # name → model class registry
│
├── scenarios/                   # NEW — Phase 3
│   ├── __init__.py
│   ├── scenario.py              # Scenario(name, base, overrides, results)
│   ├── workspace.py             # ScenarioWorkspace — manage many scenarios
│   ├── compare.py               # diffing & KPI comparison
│   └── sensitivity.py           # one-way / tornado sweeps
│
├── dashboard/                   # NEW — Dash app (Phase 1, alongside graph/io)
│   ├── __init__.py
│   ├── app.py                   # `python -m arcline.dashboard` entry point
│   ├── server.py                # Flask server + Dash factory
│   ├── config.py                # paths, theme, feature flags
│   ├── state/
│   │   ├── store.py             # dcc.Store keys; serialization helpers
│   │   └── session.py           # per-session graph in memory (single-user MVP)
│   ├── components/              # reusable UI atoms
│   │   ├── navbar.py
│   │   ├── node_form.py         # CRUD form (driven by pydantic schema)
│   │   ├── edge_form.py
│   │   ├── data_table.py        # AG-Grid / dash_table bulk editors
│   │   └── kpi_cards.py
│   ├── pages/                   # Dash multi-page app
│   │   ├── home.py              # project picker / open-recent
│   │   ├── nodes.py             # /dashboard/nodes — list + create + edit + delete
│   │   ├── edges.py             # /dashboard/edges — list + create + edit + delete
│   │   ├── visualize.py         # /dashboard/visualize — full network render
│   │   ├── history.py           # /dashboard/history — historic data analytics (Phase 1.5)
│   │   ├── scenarios.py         # /dashboard/scenarios (Phase 3)
│   │   └── solve.py             # /dashboard/solve  (Phase 2)
│   ├── callbacks/               # Dash callbacks split by page
│   │   ├── nodes_cb.py
│   │   ├── edges_cb.py
│   │   ├── visualize_cb.py
│   │   └── history_cb.py
│   ├── viz/                     # rendering helpers
│   │   ├── layouts.py           # force-directed (NetworkX spring), tiered, geo
│   │   ├── plotly_graph.py      # Plotly trace builders for nodes/edges
│   │   └── styles.py            # color/icon resolution from node/edge classes
│   └── assets/                  # static (CSS, copied icons)
│
├── cli/                         # NEW — `arcline` console script
│   ├── __init__.py
│   ├── main.py                  # typer/click app
│   └── commands.py              # init, validate, solve, dashboard, export
│
├── utils/
│   ├── hashing.py               # deterministic hashKey generation
│   ├── logging.py               # structured logging config
│   └── geo.py                   # haversine, bbox helpers (no geocoding deps)
│
└── examples/                    # runnable sample networks (small/medium)
    ├── toy_3node/
    └── facility_location_demo/
```

---

## 5. Phase 1 — Graph + I/O + Dashboard (MVP)

**Goal:** a user can create a project, define nodes/edges either programmatically or through the Dash UI, save/load to disk, and render the network on `/dashboard/visualize`.

### 5.1 Graph core extensions

* **`graph/library/`** — concrete subclasses of `AbstractNode` / `AbstractEdge`, each:
  * Adds domain attributes (e.g. `Supplier.leadTimeDays`, `Plant.productionRatePerHr`, `Warehouse.minCapacity/maxCapacity`, `Customer.demandMean/demandStd`, `Lane.distanceKm/costPerUnit/transitDays/mode`).
  * Overrides `imagePath` / `nodeColor` (and `edgeColor`) using assets from `graph/icons/`.
  * Declares a class-level string `kind` (e.g. `"supplier"`) used by the registry.
* **`graph/registry.py`** — `register(kind, cls)` + `resolve(kind) -> type`. Drives polymorphic deserialization (a saved JSON record with `"kind": "warehouse"` reconstructs a `Warehouse` instance).
* **`graph/builder.py`** — `NetworkBuilder` fluent API for ergonomic, validated programmatic construction (`builder.add_supplier(...).add_plant(...).connect(src, dst, cls=Lane, ...)`).
* **`AbstractNode`** gains optional `latitude: Optional[float]`, `longitude: Optional[float]` (validated to `[-90, 90]` / `[-180, 180]`).
* **`AbstractGraph`** gains `addNode`, `addEdge`, `updateNode`, `updateEdge` abstract methods (currently only remove/has/neighbors exist) so the dashboard can mutate a live graph; `NetworkXGraph` implements all of them.

### 5.2 Project / file I/O

A **project** is a directory:

```
my_network/
├── manifest.yaml          # name, version, arcline schema version, created/updated
├── nodes.json             # array of {kind, hashKey, name, ...attrs}
├── edges.json             # array of {kind, hashKey, srcKey, dstKey, ...attrs}
├── icons/                 # optional user-supplied icons override
└── scenarios/             # populated in Phase 3
    └── <scenario_name>/
```

* `arcline.io.project.Project.open(path) → Project` and `Project.save()`.
* `Project.toGraph(backend="networkx") → AbstractGraph`.
* `Project.fromGraph(graph) → Project` (round-trip).
* Cross-file validators: every edge's `srcKey`/`dstKey` exists in `nodes.json`; no duplicate `hashKey`s; pydantic validates each record on load.
* Parquet path is for **bulk** workflows (≥10⁵ records); JSON remains the canonical, diff-friendly format.

### 5.3 Dashboard (Dash) — Phase 1 scope

**App shell:** Dash multi-page app, Bootstrap theme via `dash-bootstrap-components`. `app.py` provides `python -m arcline.dashboard --project ./my_network` entry point. CLI `arcline dashboard ./my_network` wraps the same.

**State model:**
* The authoritative state is a single in-memory `AbstractGraph` held in a server-side session store (`flask-caching` filesystem cache, MVP = single-user / single-process).
* `dcc.Store` mirrors lightweight metadata (selected node, dirty flag, current project path) on the client.
* All mutations go through a **command pattern** (`AddNodeCmd`, `UpdateEdgeCmd`, …) so undo/redo and an audit log become straightforward later.
* "Save" writes back to the project folder via `arcline.io`.

**Pages:**

1. **`/`  Home** — project picker, recent projects, "New project" wizard (creates empty manifest + empty `nodes.json`/`edges.json`).
2. **`/dashboard/nodes`** — paginated AG-Grid/`dash_table` of all nodes. Buttons: *Create*, *Edit*, *Delete*, *Duplicate*. Modal form is **auto-generated from the pydantic schema** of the selected `kind` (so adding a new node class to `graph/library/` automatically gets a form). Validation errors surface inline from pydantic.
3. **`/dashboard/edges`** — analogous; source/destination dropdowns are searchable and filtered to existing nodes; multi-edges are allowed (matches `MultiDiGraph` semantics).
4. **`/dashboard/visualize`** — the full-network renderer (see 5.4).
5. **`/dashboard/solve`** — placeholder in Phase 1, wired in Phase 2.
6. **`/dashboard/scenarios`** — placeholder in Phase 1, wired in Phase 3.

**`dashboard/visualize` rendering:**
* **Mode toggle:** *Geo* (Mapbox) / *Force-directed* / *Tiered* (Supplier→Plant→DC→Customer columns).
* **Geo mode** appears only when ≥1 node has lat/lon; uses `Scattermapbox` with OpenStreetMap tiles (no token required) plus optional Mapbox token via env var.
* **Abstract modes** use `Scattergl` (handles 10⁵+ nodes smoothly); layout coordinates are computed by NetworkX (`spring_layout`, `multipartite_layout`) and cached on the graph object.
* Nodes are colored / shaped by `kind`; size encodes a user-selected attribute (e.g. capacity, demand). Hover tooltip shows full pydantic payload.
* Edges drawn as line segments; arrowheads via Plotly annotations for small graphs, suppressed for large ones (>2 000 edges) for performance.
* **Edit interactions** on the canvas:
  * Click a node → side panel shows the auto-generated form (same component as `/nodes`).
  * Shift+drag in geo/abstract mode → marquee-select; bulk delete / bulk edit common attributes.
  * Right-click empty canvas → "Add node here" (uses click coords as lat/lon in geo mode, otherwise as a layout hint).
  * "Connect" tool: click source → click destination → edge form modal.
* **KPI strip** (top of page): `numNodes`, `numEdges`, count by `kind`, total capacity, etc. — wired through `AbstractGraph` properties.

### 5.4 Phase 1 deliverables checklist

* [x] `graph/library/` taxonomy + registry + tests.
* [x] `addNode`/`addEdge`/`updateNode`/`updateEdge` on `AbstractGraph` + `NetworkXGraph`.
* [x] `arcline.io` (Project, readers, writers, schema, validators) + tests on round-trip fidelity.
* [x] CLI: `arcline init`, `arcline validate`, `arcline dashboard`.
* [x] Dash app shell, Home, Nodes, Edges, Visualize pages.
* [x] Pydantic-driven auto-form component.
* [x] At least one runnable example project under `examples/`.
* [x] CI: ruff + mypy + pytest on Python 3.12 / 3.13.

---

## 6. Phase 1.5 — Historian & Analytics (`arcline.historian`)

**Goal:** every node and edge attribute can be transparently traced back to its historic time-series in a MS-SQL Server data warehouse, fetched on demand, cached locally, and analysed (numerically and visually) inside the dashboard. This phase ships **right after the Phase 1 MVP, before optimization**, so analysts get value before any solver is wired in. Stochastic optimization in later phases will piggy-back on the same fetched history.

### 6.1 Declarative `HistorySpec` — convention over configuration

Each concrete node/edge class declares — at class level — *how* a given attribute maps to a row-set in MS-SQL. The framework auto-builds the parameterized SQL; classes never write SQL by hand.

```python
from arcline.historian import HistorySpec

class Lane(AbstractEdge):
    leadTimeDays   : float = Field(...)
    distanceKm     : float = Field(...)
    costPerUnit    : float = Field(...)

    history : ClassVar[Dict[str, HistorySpec]] = {
        "leadTimeDays": HistorySpec(
            table       = "dwh.fact_lane_lead_time",
            keyColumn   = "edge_hash_key",       # matches AbstractEdge.hashKey
            valueColumn = "actual_lead_time_days",
            tsColumn    = "shipment_date",
            filters     = {"is_active": 1},      # static WHERE predicates
            description = "Realized lead time per shipment, daily grain.",
        ),
        "costPerUnit": HistorySpec(
            table       = "dwh.fact_lane_cost",
            keyColumn   = "edge_hash_key",
            valueColumn = "unit_cost",
            tsColumn    = "invoice_date",
        ),
    }
```

* `HistorySpec` is a pydantic model with `table`, `keyColumn`, `valueColumn`, `tsColumn`, optional `schema`, `filters: Dict[str, Any]`, optional `aggregation: Literal["raw","daily","weekly","monthly"]`, and optional `valueTransform` (e.g., `"hours_to_days"`).
* The framework composes a parameterized SELECT (SQLAlchemy Core, never string-concatenation) with `WHERE keyColumn = :hashKey AND tsColumn BETWEEN :start AND :end`, plus the static `filters` dict.
* **Override hook (escape hatch):** any class may override `def fetchHistory(self, attribute, start, end) -> pd.DataFrame` for non-trivial joins. The convention path is preferred whenever it suffices.

### 6.2 Connection layer

* **MS-SQL Server** via **SQLAlchemy Core + pyodbc** (`mssql+pyodbc://...`).
* Connection string read from `ARCLINE_MSSQL_DSN` env var (12-factor); no credentials are ever stored in `manifest.yaml` or any tracked file.
* Single process-wide engine with connection pooling; lazy initialization on first fetch so users without a DB still load projects.
* `historian.connection.testConnection() -> bool` exposed for the dashboard's "DB status" indicator.

### 6.3 Fetch + cache strategy

* **On-demand fetch with local Parquet cache.** The first call fetches from MS-SQL and writes:

  ```
  <project>/.cache/history/
      <kind>/<hashKey>/<attribute>__<start>_<end>.parquet
  ```

  Subsequent calls within the same `[start, end)` window read from the Parquet without touching the DB.
* The cache directory is **always gitignored** (`arcline init` writes `.gitignore` with this entry).
* CLI: `arcline history sync --project ./demo_network [--since YYYY-MM-DD]` for bulk pre-warming (operationally useful for offline analyst sessions).
* `historian.cache.invalidate(...)` and `arcline history clear` for cache busting.
* Cache key includes a hash of the `HistorySpec` so spec changes invalidate stale caches automatically.

### 6.4 Analytics primitives (univariate baseline)

`historian.analytics` ships the baseline analytics every supply-chain analyst needs on a single attribute time-series; deeper analytics (outlier detection, changepoints, forecasting, cross-attribute correlation) are deferred to a future phase to keep this one tight.

* `summary(df) -> dict` — count, min, max, mean, std, median, p5/p25/p75/p95, last value, last refresh timestamp.
* `rolling(df, window) -> pd.DataFrame` — rolling mean & std on a configurable window (default 7-period).
* `distribution(df, bins) -> pd.DataFrame` — histogram bins for the value column.
* `resample(df, freq) -> pd.DataFrame` — convenience wrapper around `pandas.DataFrame.resample`.

All return plain `pandas` objects so they trivially feed Plotly traces in the dashboard.

### 6.5 Public API

```python
from arcline.historian import fetch, summary, rolling

edge = graph._edgesByKey["E-PORT-SUPPLIER-01"]["..."]
df = fetch(edge, attribute="leadTimeDays", start="2023-01-01", end="2025-01-01")
print(summary(df))
roll = rolling(df, window=7)
```

The same call path is what the dashboard uses; there is no parallel "dashboard-only" implementation.

### 6.6 Dashboard `/dashboard/history`

A new dedicated page (registered via Dash multi-page registry) sitting alongside `/dashboard/visualize`.

* **Selector pane (left):**
  * Entity type toggle: *Nodes* / *Edges*.
  * Searchable list of all entities in the current project (filterable by `kind`).
  * Once an entity is selected, the framework introspects `entity.history` (the `HistorySpec` mapping) and lists all attributes that have a spec.
  * Date range picker (defaults to last 24 months); attribute aggregation toggle (`raw` / `daily` / `weekly` / `monthly`).
* **Charts pane (right):**
  * **Time-series** Plotly line chart of the value column with hover tooltips and an overlaid rolling mean/std band (toggleable).
  * **Distribution** histogram + box plot side panel.
  * **Summary stats** card (count, min/mean/median/max, std, p5/p95, last value, last refreshed).
* **Operational affordances:**
  * "Refresh from DB" button (bypasses cache for the selected (entity, attribute, range) only).
  * Top-bar **DB status pill**: green = connected, amber = cached-only fallback, red = `ARCLINE_MSSQL_DSN` not set or unreachable.
  * "Export CSV / Parquet" button writes to `<project>/exports/`.
* **Cross-page integration with `/dashboard/visualize`:**
  * Clicking a node/edge on the visualize canvas exposes a "View history" link in the side drawer that deep-links to `/dashboard/history?entity=<hashKey>&attribute=<...>`.
* **Performance guardrails:**
  * Server-side downsampling (LTTB) for series longer than ~50k points before sending to the browser.
  * Streaming/chunked fetch for very large ranges (>5 years) to keep the UI responsive.

### 6.7 Phase 1.5 deliverables checklist

* [x] `arcline.historian.spec.HistorySpec` (pydantic, frozen) + class-level `history` mapping convention via `HistorianMixin`.
* [x] SQLAlchemy Core engine factory + `pyodbc` driver wiring; `ARCLINE_MSSQL_DSN` discovery; `testConnection()` (with TTL cache in navbar pill).
* [x] Generic parameterized fetcher with static-filter merging and timestamp range binding (identifier whitelist `[A-Za-z_][A-Za-z0-9_]*` to defeat injection).
* [x] Parquet cache layer with spec-hash invalidation; `<project>/.cache/history/` and gitignore handling. `clearCache(hashKey=...)` now requires `kind` (raises `CacheError` instead of silently no-op'ing).
* [x] `arcline history sync` / `arcline history clear` / `arcline history validate` CLI commands.
* [x] `analytics.summary` / `rolling` / `distribution` / `resample`. `distribution` drops NaN values before `np.histogram` (was crashing on real DB pulls).
* [x] `HistorySpec` definitions for the built-in taxonomy (Lane `transitDays` + `costPerUnit`, Plant `productionRatePerHr`, Warehouse `maxCapacity`, Customer `demandMean`) — see `examples/historian_schema.sql` for the matching MS-SQL DDL.
* [x] Dash page `/dashboard/history` + callbacks + DB status pill (TTL-cached so navbar render is not gated on a 5 s SQL probe).
* [x] Deep-link integration from `/dashboard/visualize` side drawer.
* [x] Tests: 23 historian-specific tests covering spec hashing, SQL composition, cache hit/miss, spec-drift invalidation, NaN handling, redaction. Live MS-SQL integration matrix gated by `@pytest.mark.mssql` is reserved for a future CI lane.

**Audit findings & fixes (post-P15-7):**

| ID  | Severity | File                                | Issue                                                                 | Fix                                                                  |
|-----|----------|-------------------------------------|-----------------------------------------------------------------------|----------------------------------------------------------------------|
| A1  | P0       | `historian/analytics.py::distribution` | Crashed with `ValueError: range of [nan, nan] is not finite` when the value series contains any NaN — common on real DB pulls. | Drop NaNs before `np.histogram`; all-NaN frames now return an empty histogram DataFrame (not a crash). |
| A2  | P1       | `historian/cache.py::clearCache`    | `clearCache(project, hashKey="X")` (without `kind`) silently no-op'd because the path resolved to `<root>/X` which never exists. | Raise `CacheError` when `hashKey` is supplied without `kind` — callers must scope explicitly. |
| A3  | P1       | `dashboard/components/navbar.py`    | `_dbStatusPill()` issued a synchronous `SELECT 1` on **every** navbar render → every page navigation paid up to 5 s of SQL latency. | TTL-cached resolver (`_resolveDbStatus`, 30 s); first paint probes once, navigation reuses the verdict. |
| A4  | P2       | `historian/connection.py::testConnection` | `timeout` parameter declared but never wired through to the engine. | Pass `timeout` through `execution_options` on the probe statement.   |
| A5  | P2       | `cli/history.py::sync`              | Iterated `_entitiesOfKind(graph, kind)` twice per kind (once to fetch, once to materialize again to count empties). | Single materialization per kind into `entitiesByKind`; `skipCount` increments only for kinds with zero entities. |
| A6  | P2       | `historian/analytics.py::resample`  | Dead code (`if "ts" not in aggregated.columns: aggregated.insert(...)`) unreachable after `reset_index()`. | Removed. |

---

## 7. Phase 2 — Optimization (`arcline.optim`)

**Goal:** turn an `AbstractGraph` into a Pyomo `ConcreteModel`, solve it, and surface results back on the graph and in the dashboard.

* **`compiler.py`** — `compile(graph, model_name, params) -> ConcreteModel`. Walks `graph.nodes` / `graph.edges`, reads typed attributes (capacity, cost, demand), and emits Pyomo sets / params / vars / constraints / objective.
* **Built-in models** (`optim/models/`):
  * `min_cost_flow` — classic LP min-cost multi-commodity flow.
  * `facility_location` — MILP, binary open/close on plants & DCs.
  * `multi_period_flow` — time-indexed with inventory at storage nodes.
  * `share_of_business` — allocation across suppliers with min/max share constraints (a stated keyword in `pyproject.toml`).
* **`solvers.py`** — `get_solver("cbc"|"highs"|"gurobi"|"cplex", **opts)`. Detects availability; falls back to CBC; honors `ARCLINE_SOLVER` env var.
* **`results.py`** — `SolveResult(status, objective, flows, decisions, duals, log_path, runtime_s)`; method `apply_to(graph)` annotates edges with optimal `flow`, nodes with `open/close` decisions for downstream visualization.
* **Dashboard `/dashboard/solve`** — pick model, set parameters via auto-form, run; result is shown by re-rendering `/dashboard/visualize` with edge widths proportional to flow and a toggle "show closed facilities".

---

### 7.1 Hand-off from the historian

* `historian.analytics.summary(...)` is the canonical source for fitted means / std-devs that feed deterministic optim parameters (e.g., expected `leadTimeDays` for a `Lane` is taken from the historic mean, not the raw attribute value, when `params={"useHistory": True}` is passed to `compile`).
* The same fetched DataFrames seed empirical distributions for future stochastic / robust extensions.

---

## 8. Phase 3 — Scenarios & Sensitivity

* **`Scenario`** = `(name, base_project, overrides, model_name, model_params, result)`. `overrides` is a small DSL: `{"nodes": {"P1": {"maxCapacity": 5000}}, "edges": {...}}`.
* **`ScenarioWorkspace`** — manages many scenarios under `<project>/scenarios/`, each with its own `manifest.yaml`, `overrides.json`, `result.parquet`.
* **`compare.py`** — KPI diff table (Δobjective, Δflow per lane, Δfacility status). Plotly bar / waterfall.
* **`sensitivity.py`** — one-way sweeps over a chosen parameter; tornado plots; ranges configurable from the dashboard.
* **Dashboard `/dashboard/scenarios`** — table of scenarios, "Clone & edit", "Run", "Compare selected (≥2)". Compare view embeds the diff table + side-by-side networks.

---

## 9. Cross-cutting Concerns

| Concern              | Approach                                                                                                |
| -------------------- | ------------------------------------------------------------------------------------------------------- |
| **Hashing / IDs**    | `utils.hashing.makeKey(kind, name)` — deterministic, stable across machines; users may pass explicit keys. |
| **Logging**          | `structlog`-style JSON logs in CLI/server; quiet by default; `-v/-vv` flags.                            |
| **Config**           | `pydantic-settings`; env vars prefixed `ARCLINE_`.                                                      |
| **Errors**           | Custom hierarchy: `ArclineError` → `ValidationError`, `IOError`, `SolverError`, `GraphError`.           |
| **Performance**      | NetworkX up to ~1M edges; igraph backend selectable via `Project.toGraph(backend="igraph")`.            |
| **Type safety**      | `mypy --strict` on `arcline/graph`, `arcline/io`, `arcline/optim`. Looser on `dashboard/callbacks`.     |
| **Testing**          | `pytest` + `pytest-cov`; golden-file tests on JSON I/O; `dash[testing]` for callback smoke tests.       |
| **Docs**             | Sphinx + `myst-parser` + `sphinx-autoapi`; hosted via GitHub Pages. Examples are runnable notebooks.    |
| **Packaging**        | `pyproject.toml` already in place; add optional extras: `[dashboard]`, `[igraph]`, `[gurobi]`, `[cplex]`. |
| **Security**         | Dashboard MVP is **localhost-only**; no auth. A future `[server]` extra adds `flask-login` + RBAC.      |
| **Versioning**       | SemVer; manifest stores `arcline_schema_version` for forward-compatible migrations under `arcline.io.migrations`. |
| **Naming convention**| **Strict camelCase EVERYWHERE** — functions, methods, parameters, locals, pydantic attrs. Exempt: PascalCase classes, dunders, `test_*` test functions, externally-mandated kwargs (Dash / Pydantic / Typer / networkx / pandas / SQLAlchemy), env vars (`UPPER_SNAKE`). Enforced by `tools/check_camel_case.py` (pre-commit + CI). Legacy `arcline/graph/registry.py` and intentional deprecation shims in `arcline/io/__init__.py` / `arcline/utils/__init__.py` are grandfathered. |

### Proposed dependency additions (to `pyproject.toml`)

```
core      : pydantic>=2, networkx>=3, pandas, pyarrow, pyyaml, typer, structlog, pydantic-settings
dashboard : dash>=2.17, dash-bootstrap-components, plotly>=5, dash-ag-grid, flask-caching
historian : sqlalchemy>=2, pyodbc                # MS-SQL driver is user-installed (msodbcsql)
optim     : pyomo>=6.7, highspy                  # CBC via apt/conda; gurobi/cplex are user-installed
igraph    : python-igraph
dev       : pytest, pytest-cov, ruff, mypy, sphinx, myst-parser, sphinx-autoapi, dash[testing]
```

---

## 10. Public API Sketch

```python
import arcline
from arcline.graph.library import Supplier, Plant, Warehouse, Customer, Lane
from arcline.graph.builder import NetworkBuilder
from arcline.io import Project
from arcline.historian import fetch, summary, rolling
from arcline.optim import compile, get_solver
from arcline.scenarios import Scenario

# --- build ---
b = NetworkBuilder()
s1 = b.add(Supplier(name="S1", hashKey="N-S1", leadTimeDays=3, latitude=12.97, longitude=77.59))
p1 = b.add(Plant(name="P1", hashKey="N-P1", maxCapacity=10_000))
b.connect(s1, p1, cls=Lane, hashKey="E-S1P1", costPerUnit=2.5, transitDays=2)
graph = b.build(backend="networkx")

# --- persist ---
proj = Project.fromGraph(graph, path="./demo_network")
proj.save()

# --- historic analysis (Phase 1.5) ---
edge = graph._edgesByKey["E-S1P1"][("N-S1", "N-P1")]
df = fetch(edge, attribute="leadTimeDays", start="2023-01-01", end="2025-01-01")
print(summary(df))                # mean / std / p95 / last value
roll = rolling(df, window=14)     # 14-period rolling mean/std

# --- optimize (mean lead time pulled from historian) ---
model = compile(graph, model="min_cost_flow",
                params={"horizon": 1, "useHistory": True})
result = get_solver("highs").solve(model)
result.apply_to(graph)

# --- dashboard ---
# $ arcline dashboard ./demo_network
```

---

## 11. Risks & Mitigations

| Risk                                                          | Mitigation                                                                          |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Plotly render lag for very large networks (>50 k nodes)       | `Scattergl`; tile/level-of-detail; server-side filtering before sending to client.  |
| Dash single-process state collides under multi-user           | Phase 1 is single-user/local; multi-user gated behind a future `[server]` extra.    |
| Pyomo solver availability varies across user environments     | CBC fallback bundled via `pulp`-style or conda; clear errors when solver missing.   |
| Schema evolution breaks saved projects                        | `manifest.yaml` carries `arcline_schema_version`; migration scripts under `io/migrations/`. |
| Auto-generated forms can't express every constraint           | Allow per-class form overrides via `class Meta: form_overrides = {...}`.            |
| MS-SQL driver / network unavailable in analyst environments   | DB access is fully optional; cached Parquet under `.cache/history/` keeps `/dashboard/history` usable offline; DB-status pill makes the mode explicit. |
| Bad / drifting `HistorySpec` definitions silently return empty results | Spec-hash in cache key + `EmptyHistoryError` surfaced as a banner on `/dashboard/history`; `arcline validate --history` runs spec smoke-checks against the live DB. |
| Large historic pulls (years × thousands of edges) overwhelm the dashboard | Server-side LTTB downsampling for >50k points; chunked fetch for >5-year ranges; bulk pre-warm via `arcline history sync` keeps interactive paths fast. |
| Credential leakage through saved projects                     | Connection string lives **only** in `ARCLINE_MSSQL_DSN`; never serialised into `manifest.yaml`, cache files, or logs (redaction filter in `utils.logging`). |

---

## 12. Open Questions (to revisit)

1. **Authentication / multi-user dashboard** — defer to a future phase, but decide on the interface (Flask blueprints vs. embedding in Django) before locking the dashboard module boundaries.
2. **Geocoding** — out of scope for now; users supply lat/lon. Worth a thin optional adapter (`arcline.utils.geo.geocode`) over Nominatim later?
3. **Solver licensing** — Gurobi/CPLEX are user-supplied; do we ship Docker images with HiGHS + CBC pre-installed?
4. **Time-series demand** — Phase 3+: how do we represent demand profiles (CSV link from node, or inline)?
5. **Advanced analytics** — outlier / changepoint detection, forecasting (statsmodels / Prophet), and cross-attribute correlation are intentionally deferred from Phase 1.5; revisit once the baseline historian is in production use.
6. **Multi-database support** — MS-SQL is the only target now; the SQLAlchemy abstraction leaves the door open to Postgres / Snowflake / BigQuery later, but no work is planned in the current roadmap.
7. **Auth for the historian** — env-var DSN is sufficient for now; Azure AD / Managed Identity / Kerberos integrated auth is parked for a later iteration.

---

## 13. Definition of Done — Phase 1  ✅ **COMPLETE** (and Phase 1.5 — see §14 ✅)

A new user can:

```bash
pip install -e .[dashboard]
arcline init my_network
arcline dashboard my_network
```

…open `http://localhost:8050`, **create** a Supplier, a Plant, a Warehouse, a Customer, **connect** them with Lanes through the UI, **see** the network on `/dashboard/visualize` (force-directed by default, switching to geo when they fill in lat/lon), and **save** — producing a clean, git-committable `nodes.json` / `edges.json` / `manifest.yaml`. Re-opening the project reproduces the exact same network. CI is green (58/58 tests, ~2 s); one example project (`examples/toy_3node/`) runs end-to-end.

**Acceptance evidence:**
- `pytest -q` → **114 passed, 2 skipped** (post-Phase 1.5 baseline; was 58 at Phase 1)
- `tools/check_camel_case.py` → **0 violations** (CI gate, enforced)
- `arcline init / validate / dashboard / history sync|clear|validate` all working with friendly error handling
- CLI cold path imports neither `dash` nor `pandas` nor `sqlalchemy` (verified)
- Reviewer + debugger + audit passes cleared (all P0s and key P1–P2s fixed; see §6.7 audit table)

**Known deferred items (tracked, not blocking):**
- dash_table fallback selection-prop mismatch in CRUD callbacks (lower priority because `[dashboard]` extras pin `dash-ag-grid>=31`).
- Plant/Warehouse `min ≤ max` cross-field pydantic validator.
- Edge hover `hoverinfo` cosmetic mismatch.
- LTTB downsampling in `dashboard/callbacks/history_cb.py` is a fast |x − mean|-argmax approximation, not the canonical triangle-area LTTB. Sufficient for current series sizes (≤ ~50 k points) but worth replacing if visual fidelity ever regresses.
- Live MS-SQL integration test matrix (`@pytest.mark.mssql`) — reserved for a future CI lane with a real warehouse fixture.

---

## 14. Definition of Done — Phase 1.5  ✅ **COMPLETE**

With `ARCLINE_MSSQL_DSN` set, an analyst can:

```bash
export ARCLINE_MSSQL_DSN="mssql+pyodbc://..."
arcline history sync ./demo_network --since 2023-01-01
arcline dashboard ./demo_network
```

…open `/dashboard/history`, pick a `Lane` between a port and a supplier, choose `transitDays`, see a populated time-series chart, distribution histogram, and summary-stats card pulled from MS-SQL (or warm cache); deep-link from any node/edge on `/dashboard/visualize` into the same view; toggle the DB-status pill from green ↔ amber by unsetting the env var and verify the dashboard still works against the cached Parquet. `arcline history validate` reports zero broken `HistorySpec` definitions for the built-in taxonomy. No credentials appear in any project file, cache file, or log line (verified via `redactDsn`).

**Acceptance evidence (this build):**
- `pytest -q` → **114 passed, 2 skipped** (~9 s)
- `python tools/check_camel_case.py` → **0 violations**
- `arcline history validate` (DSN unset) → reports catalog size, exits 0 with amber message
- `arcline history clear ./demo_network` → cache is offline-only, never touches the engine
- `redactDsn("...:secretPwd@host?password=other")` → both passwords masked in output
- Audit pass identified 6 issues (1 P0 / 2 P1 / 3 P2); all fixed (see §6.7 audit table)
