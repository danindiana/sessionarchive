# cosmosgl-dashboard

A standalone, containerized rebuild of the [CosmosGL](https://cosmos.gl) (`@cosmos.gl/graph`)
WebGL graph viewer — a GPU-rendered dashboard over a Neo4j graph, with a Python HTTP/API
backend and a GPU-accelerated layout precompute step.

## Relationship to `paper_processor`

This started life as `paper_processor/neo4j_viz/cosmos_server.py` +
`cosmos_dashboard.html` (the "Lobster Graph — CosmosGL Dashboard", port 8686 in that
project). That version has no Dockerfile for the dashboard itself (only its Neo4j is
containerized), and its JS bundle (`cosmos_bundle.js`) was committed pre-built with no
source ever checked in — only `node_modules/` and a lockfile survive.

Everything here is a fresh, self-contained build of the same behavior:
- The Python backend and cuGraph layout script are containerized, not bare-metal.
- The frontend glue code (`frontend/src/app.js`) is reconstructed as readable source,
  restoring real names from the decompiled bundle, and is built from source inside the
  Docker image via esbuild — no prebuilt JS artifact is shipped or committed.
- It bundles its own Neo4j instance, independent of `paper_processor`'s. It does not read
  from or write to that project's live database, and nothing in `paper_processor` was
  modified to build this.

## What it does

- **`server`** — `cosmos_server.py` serves the dashboard's static assets and three JSON/
  binary endpoints backed by Neo4j:
  - `GET /api/graph` — all nodes (id, type, label, `fx`/`fy` layout coordinates) and edges
  - `GET /api/node/<id>` — a single node's full properties, for the detail modal
  - `GET /pdf/<id>` — streams a `Paper` node's source PDF, if it exists on disk
- **`layout`** — `compute_layout.py`, a one-shot GPU job: pulls the graph topology from
  Neo4j, runs cuGraph's `force_atlas2` on the GPU, and writes the resulting `(x, y)` back
  onto each node as `fx`/`fy`. The frontend then renders a **static** layout
  (`enableSimulation: false`) instead of simulating in the browser.
- **`frontend`** — the CosmosGL-based viewer itself: color/size-coded nodes by type
  (`Paper`, `Concept`, `Theorem`, `Algorithm`, `CodeSnippet`, `Diagram`), hover tooltips,
  and a double-click-to-open detail modal (with a source-PDF link for `Paper` nodes).

## Quickstart

```bash
cd cosmosgl-dashboard
docker compose up -d --build neo4j server
```

Then open `http://localhost:28686` (or whatever `DASHBOARD_PORT` is set to in `.env`).
The dashboard will show an empty graph until you load data into the bundled Neo4j — point
any Cypher client at `bolt://localhost:27687` (`neo4j`/`password123`, both overridable via
`.env`) and load nodes labeled `Paper`/`Concept`/`Theorem`/`Algorithm`/`CodeSnippet`/
`Diagram`.

### Running the GPU layout step

```bash
docker compose run --rm layout
```

Requires the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
on the host. Re-run this any time the graph topology changes and you want node positions
recomputed — it's a one-shot job, not a daemon. Verify it worked by checking that nodes
in the bundled Neo4j now have non-null `fx`/`fy` properties (e.g. via the Neo4j Browser at
`http://localhost:27474`), and that the dashboard renders them at those positions instead
of all stacked at the origin.

## Testing

```bash
pip install -r requirements-test.txt
pytest tests/test_cosmos_server_unit.py -v   # fast, no Docker/GPU required
pytest tests/test_container_smoke.py -v      # builds + runs the real stack, seeds data, hits the live API
```

The smoke test suite builds the `server` image, starts it alongside a fresh bundled
Neo4j, seeds a small known graph (`tests/fixtures/seed.cypher`), and verifies `/`,
`/api/graph`, `/api/node/<id>` (both found and 404 cases), and `/pdf/<id>` (404-with-
explanation when the stored path doesn't exist on disk) against the real running
container — then tears the stack down. It does not require a GPU and excludes the
`layout` service; verify that one manually as described above.

## License

MIT (same as the parent [`sessionarchive`](../README.md) project).
