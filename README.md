<div align = "justify">

# ✨ Supply Chain Network Optimization

</div>

<div align = "justify">

The **`arcline`** is a Python framework for building, solving, and analyzing supply chain optimization problems as network flow
models. Real supply chains are graphs. Suppliers, plants, warehouses, distribution centers, and customers are nodes; the lanes
between them are arcs (or edges); and the optimization questions that matter - where to source, how much to produce, which
routes to use, when to open or close a facility - are all decisions about flow on those arcs. The project gives you a declarative
API for modeling these networks, a solver-agnostic backend (CBC, HiGHS, Gurobi, CPLEX), and first-class tooling for the parts
of the workflow that real practitioners spend most of their time on: data ingestion, scenario comparison, sensitivity analysis,
and visualization. It is designed to bridge the gap between the academic clarity of textbook formulations and the messy practical
needs of production supply chain teams. Whether you are running a one-off facility location study, building a digital twin of
a global distribution network, or embedding a recurring optimization into a daily planning pipeline, `arcline` aims to be the
layer that makes the network the first-class object - and the math, the I/O, and the solver plumbing fade into the background.

</div>

> **Status:** Phase 1 (Graph + I/O + Dashboard) and Phase 1.5 (Historian + Analytics) are **shipped**. Phase 2 (Pyomo optimization) and Phase 3 (Scenarios & Sensitivity) are on the roadmap. See [`CLAUDE.md`](./CLAUDE.md) for the full design plan.

---

## Table of Contents

- [Why arcline?](#why-arcline)
- [Installation](#installation)
- [60-second quickstart](#60-second-quickstart)
- [Core concepts](#core-concepts)
- [The CLI](#the-cli)
- [Authoring a network in Python](#authoring-a-network-in-python)
- [Project file layout](#project-file-layout)
- [The Dashboard](#the-dashboard)
- [The Historian (MS-SQL Server)](#the-historian-ms-sql-server)
- [Examples shipped with the repo](#examples-shipped-with-the-repo)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Why arcline?

A typical supply-chain modelling stack forces you to glue together at least four ad-hoc layers: a graph data structure (NetworkX),
a serialization format (CSVs / pickles), a solver harness (PuLP / Pyomo) and a visualization (matplotlib / Tableau). Each switchover
is a place for entropy: silent column renames, lost types, fragile id schemes, scenarios that drift from the canonical model.

`arcline` treats **the network itself as the first-class object**. Once you have an `AbstractGraph` of typed nodes and edges, the
framework owns the rest: validating it, persisting it as a portable, git-friendly project folder, rendering it in an interactive
Dash dashboard, pulling per-attribute history from a MS-SQL Server data warehouse, and (in upcoming phases) compiling it down to
Pyomo for solving and scenario comparison.

| Capability | Status | Where it lives |
| --- | --- | --- |
| Typed taxonomy (Supplier / Plant / Warehouse / Customer / Lane / Production / Storage) | ✅ shipped | `arcline/graph/library/` |
| Pydantic validation of every node and edge | ✅ shipped | `arcline/graph/base/` |
| Project I/O (JSON · YAML · Parquet · CSV) | ✅ shipped | `arcline/io/` |
| `NetworkBuilder` fluent assembly | ✅ shipped | `arcline/graph/builder.py` |
| Multi-page Dash dashboard with CRUD on nodes / edges | ✅ shipped | `arcline/dashboard/` |
| Visualize page (force-directed · tiered · geo via Mapbox) | ✅ shipped | `arcline/dashboard/pages/visualize.py` |
| MS-SQL historian with declarative `HistorySpec`, Parquet cache, analytics primitives | ✅ shipped | `arcline/historian/` |
| `/dashboard/history` (time-series · distribution · summary) | ✅ shipped | `arcline/dashboard/pages/history.py` |
| Pyomo optimization (min-cost flow, facility location, multi-period, share-of-business) | ⏳ Phase 2 | `arcline/optim/` (planned) |
| Scenario workspace + sensitivity sweeps | ⏳ Phase 3 | `arcline/scenarios/` (planned) |

---

## Installation

`arcline` requires **Python ≥ 3.12**. Install in editable mode with the extras you need:

```bash
# core only (graph + I/O + CLI)
pip install -e .

# add the dashboard
pip install -e .[dashboard]

# add the MS-SQL historian
pip install -e .[historian]

# everything + dev tooling (pytest, ruff, etc.)
pip install -e .[dashboard,historian,dev]
```

The MS-SQL historian additionally needs the **Microsoft ODBC Driver 18 for SQL Server** installed at the OS level. The Python side (`sqlalchemy`, `pyodbc`) comes with the `[historian]` extra.

---

## 60-second quickstart

### Option A — start from a random demo network

```bash
# 1. generate a synthetic 4-tier supply chain (21 nodes, 29 edges, geo-located)
python examples/random_network.py --output ./demo_network

# 2. open it in the dashboard (port 8050)
arcline dashboard ./demo_network
```

Then visit **http://127.0.0.1:8050**. The Visualize page automatically switches to **geo mode** (Mapbox / OpenStreetMap tiles) because the generator jitters lat/lon around Bengaluru.

Customize the generator:

```bash
python examples/random_network.py \
    --output ./big_network \
    --suppliers 30 --plants 12 --warehouses 8 --customers 60 \
    --seed 7
```

### Option B — start from an empty project

```bash
arcline init ./my_network --name "My First Network"
arcline validate ./my_network
arcline dashboard ./my_network
```

`arcline init` creates the canonical project layout. The Nodes / Edges pages let you add records through pydantic-driven forms; click **Save** to persist back to disk.

---

## Core concepts

| Concept | Where | Notes |
| --- | --- | --- |
| **`AbstractNode`** / **`AbstractEdge`** | `arcline/graph/base/` | Pydantic v2 base classes; every concrete node/edge inherits validation, hashing, and serialization for free. Both expose `hashKey` (deterministic id), `name`, optional `latitude` / `longitude`. |
| **`AbstractGraph`** | `arcline/graph/base/graph.py` | Storage-agnostic interface. The default backend wraps `networkx.MultiDiGraph`; an `igraph` backend is on the roadmap for >1M-edge networks. Provides `addNode`, `addEdge`, `updateNode`, `updateEdge`, cached neighbour indices, etc. |
| **Built-in taxonomy** | `arcline/graph/library/` | Supplier · Plant · Warehouse (alias `DistributionCenter`) · Customer · Lane · Production · Storage. Each has typed attributes (e.g. `Lane.distanceKm`, `Plant.maxCapacity`) and a `kind` discriminator used for polymorphic (de)serialization. |
| **Kind registry** | `arcline/graph/registry.py` | Maps `"supplier" → Supplier`, `"lane" → Lane`, etc. Auto-populated when `arcline.graph.library` is imported. `arcline.io` triggers this side-effect on import so the CLI just works. |
| **`NetworkBuilder`** | `arcline/graph/builder.py` | Fluent assembly: `b.add(Supplier(...))`, `b.connect(src, dst, cls=Lane, ...)`, `b.build()`. Catches duplicate hash keys and dangling endpoints early. |
| **`Project`** | `arcline/io/project.py` | File-based project facade. Three constructors: `Project.init` (empty), `Project.open` (load + validate), `Project.fromGraph` (persist an in-memory graph). Use `proj.toGraph()` to materialise. |
| **`HistorySpec`** | `arcline/historian/spec.py` | Declarative mapping from a node/edge attribute to a row-set in MS-SQL. The framework synthesises a parameterised `SELECT … BETWEEN :start AND :end`; classes never write SQL by hand. |

---

## The CLI

After `pip install -e .`, an `arcline` console script is on `$PATH`:

```bash
arcline --help
arcline init       <path>               # create an empty project
arcline validate   <path>               # cross-file integrity checks
arcline dashboard  <path>               # serve the Dash UI on http://127.0.0.1:8050

arcline history sync     <path>         # pre-warm the Parquet cache from MS-SQL
arcline history clear    <path>         # delete cached parquet snapshots (offline-only)
arcline history validate                # check catalog + DB reachability
```

All commands accept relative or absolute paths. On any I/O error the CLI prints the **resolved absolute path** plus an actionable hint (e.g. _"directory exists but is missing manifest.yaml — initialise it with `arcline init <path>`"_) — no raw tracebacks.

---

## Authoring a network in Python

```python
from arcline.graph.builder import NetworkBuilder
from arcline.graph.library import Supplier, Plant, Warehouse, Customer, Lane
from arcline.io import Project

b = NetworkBuilder()

s1 = b.add(Supplier(
    name = "Acme Steel", hashKey = "N-S1",
    latitude = 12.97, longitude = 77.59,
    leadTimeDays = 3.0, reliabilityScore = 0.95,
))
p1 = b.add(Plant(
    name = "Bengaluru Plant", hashKey = "N-P1",
    productionRatePerHr = 120.0, maxCapacity = 10_000.0,
))
w1 = b.add(Warehouse(
    name = "Whitefield DC", hashKey = "N-W1",
    maxCapacity = 25_000.0,
))
c1 = b.add(Customer(
    name = "Customer A", hashKey = "N-C1",
    demandMean = 350.0, demandStd = 45.0,
))

b.connect(s1, p1, cls = Lane, name = "S1-P1", hashKey = "E-S1P1",
          distanceKm = 220.0, costPerUnit = 2.5, transitDays = 1.5, mode = "road")
b.connect(p1, w1, cls = Lane, name = "P1-W1", hashKey = "E-P1W1",
          distanceKm =  15.0, costPerUnit = 0.4, transitDays = 0.2, mode = "road")
b.connect(w1, c1, cls = Lane, name = "W1-C1", hashKey = "E-W1C1",
          distanceKm =  40.0, costPerUnit = 1.1, transitDays = 0.5, mode = "road")

graph = b.build(backend = "networkx")

# Persist as a project on disk
proj = Project.fromGraph(graph, path = "./my_network", name = "My Demo")

# Re-open later
proj2 = Project.open("./my_network")
graph2 = proj2.toGraph()
```

---

## Project file layout

`arcline init <path>` (or `Project.fromGraph(...)`) produces a self-contained, git-versionable folder:

```
my_network/
├── manifest.yaml      # name · description · arclineSchemaVersion · timestamps
├── nodes.json         # canonical flat array of node records (diff-friendly)
├── edges.json         # canonical flat array of edge records
├── nodes.parquet      # OPTIONAL bulk format (written by toParquet / random generator)
├── edges.parquet
├── icons/             # custom node/edge icons (override library defaults)
├── scenarios/         # populated in Phase 3
├── .cache/history/    # historian Parquet cache (gitignored)
└── .gitignore
```

The JSON files are the **canonical** format — that is what `Project.open` reads and what `arcline validate` checks. The Parquet pair is convenient for bulk pandas/Spark workflows but is not required.

---

## The Dashboard

`arcline dashboard <path>` (or `python -m arcline.dashboard --project <path>`) launches a multi-page Dash + Plotly + Bootstrap app on `http://127.0.0.1:8050`:

| Page | URL | What it does |
| --- | --- | --- |
| **Home** | `/` | Project picker; recent projects; new-project wizard. |
| **Nodes** | `/dashboard/nodes` | Paginated table of all nodes. Create / Edit / Delete / Duplicate via pydantic-driven forms. |
| **Edges** | `/dashboard/edges` | Same CRUD surface for edges; src/dst dropdowns are filtered to existing nodes. |
| **Visualize** | `/dashboard/visualize` | Whole-network rendering. Toggle: **geo** (Mapbox/OSM tiles, when nodes have lat/lon), **force-directed** (NetworkX `spring_layout`), **tiered** (`multipartite_layout`). Edge widths can encode flow once Phase 2 lands. |
| **History** | `/dashboard/history` | Time-series · distribution · summary stats for any (entity, attribute) that has a `HistorySpec`. Pulls from MS-SQL or warm Parquet cache. |
| **Solve** | `/dashboard/solve` | Phase 2 placeholder. |
| **Scenarios** | `/dashboard/scenarios` | Phase 3 placeholder. |

The top navbar carries a **DB-status pill** (green = live, amber = cached-only, red = DSN unset). It is TTL-cached (30 s) so navigation is not gated on a synchronous `SELECT 1`.

> **Single-user MVP:** state lives in a process-wide session slot. Multi-user / multi-tenant support is gated behind a future `[server]` extra.

---

## The Historian (MS-SQL Server)

Every node / edge attribute can be wired to a row-set in your data warehouse via a class-level `HistorySpec` mapping. The shipped taxonomy already declares specs for the common attributes; see [`examples/historian_schema.sql`](./examples/historian_schema.sql) for the matching DDL.

### Wire it up

```bash
# 1. install the extras + Microsoft ODBC Driver 18 (OS-level)
pip install -e .[historian]

# 2. point arcline at your warehouse (the only place credentials live)
export ARCLINE_MSSQL_DSN="mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+18+for+SQL+Server"

# 3. smoke-check the catalog + connection
arcline history validate

# 4. pre-warm the parquet cache for a project (offline-friendly)
arcline history sync ./demo_network --since 2023-01-01

# 5. open the dashboard — /dashboard/history is now live
arcline dashboard ./demo_network
```

### Use it from Python

```python
from arcline.historian import fetch, summary, rolling, distribution
from arcline.io import Project

proj = Project.open("./demo_network")
graph = proj.toGraph()

# pick any edge that has a HistorySpec
edge = next(e for e in graph.edges if hasattr(type(e), "history"))
spec = type(edge).history["transitDays"]

df = fetch(
    projectPath = proj.path, kind = type(edge).kind,
    hashKey = edge.hashKey, attribute = "transitDays",
    spec = spec, start = "2023-01-01", end = "2025-01-01",
)
print(summary(df))                        # count · mean · std · p5/p95 · last
print(rolling(df, window = 14).tail())    # 14-period rolling mean / std
print(distribution(df, bins = 30))        # histogram bins
```

### Design tenets

- **Credentials never leave the env var.** No DSN ever appears in `manifest.yaml`, the Parquet cache, or logs (`redactDsn` masks both URL and ODBC keyword forms).
- **Spec-hash invalidation.** Each Parquet file is keyed by a hash of its `HistorySpec`, so swapping a `valueColumn` automatically busts the old cache.
- **Offline-friendly.** The dashboard remains functional against the warm cache when the warehouse is unreachable; the DB-status pill goes amber.
- **Identifier whitelist.** Every `table` / `keyColumn` / `valueColumn` / `tsColumn` / filter key must match `^[A-Za-z_][A-Za-z0-9_]*$` before being interpolated; values are always parameter-bound.

---

## Examples shipped with the repo

| Path | What it shows |
| --- | --- |
| [`examples/toy_3node/`](./examples/toy_3node/) | Hand-curated 3-node project (Supplier → Plant → Customer). Open with `arcline dashboard examples/toy_3node`. |
| [`examples/random_network.py`](./examples/random_network.py) | Parametric random 4-tier supply-chain generator. Writes a full project + bulk Parquet pair. Defaults: 6 / 4 / 3 / 8 entities, seed 42 → 21 nodes, 29 edges. |
| [`examples/historian_schema.sql`](./examples/historian_schema.sql) | DDL for the MS-SQL fact tables that match the built-in `HistorySpec` catalog (`fact_lane_lead_time`, `fact_lane_cost`, `fact_plant_throughput`, `fact_warehouse_throughput`, `fact_customer_demand`). |

---

## Troubleshooting

### `arcline dashboard ./demo_network` → "Project not found"

`arcline` resolves your path against the **current working directory**. If you ran the random generator from one shell and then opened a fresh shell to launch the dashboard, the cwd may differ. The CLI now prints the **resolved absolute path** plus an actionable hint:

```
Project not found at ./demo_network (resolved: C:\...\demo_network).
Directory does not exist. Either pass a different path, or generate one first:
  arcline init ./demo_network
  # or, for a random demo network:
  python examples/random_network.py --output ./demo_network
```

Either `cd` to the right directory or pass an absolute path.

### `unknown-node-kind: 'supplier'`

Means the kind registry is empty when `Project.open()` runs. The `arcline.io` package triggers the registry side-effect on import — but if you import lower-level modules in an unusual order, force the side-effect explicitly:

```python
import arcline.graph.library  # noqa: F401
from arcline.io import Project
proj = Project.open("./my_network")
```

### `/dashboard/history` shows nothing

- Open the navbar: pill should be **green** (DB live) or **amber** (cached-only). If **red**, `ARCLINE_MSSQL_DSN` is unset.
- Run `arcline history validate` to confirm catalog + connection.
- For an offline demo: run `arcline history sync ./demo_network` from a machine that *does* have access; the `.cache/history/` directory is portable.

### Solver not found / Pyomo errors

Phase 2 (Pyomo + solver backends) has not yet shipped. Track it on the [`CLAUDE.md`](./CLAUDE.md) §7 roadmap.

---

## Contributing

- **Naming:** strict camelCase across all Python identifiers (functions, methods, attributes, parameters, locals). Enforced by `tools/check_camel_case.py` (CI gate; 0 violations as of v0.2.0-dev). Exemptions: `def test_*`, dunders, environment variables, external library kwargs.
- **Tests:** `pytest -q` should be green before any PR (currently **115 passed, 2 skipped** in ~9 s).
- **Design intent:** every architectural decision lives in [`CLAUDE.md`](./CLAUDE.md) — read it before proposing structural changes.

```bash
pytest -q                               # full suite
python tools/check_camel_case.py        # naming guardrail
```

