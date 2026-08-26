# HOWTO: cold-start setup

Setting up `cosmosgl-dashboard` on a fresh box from nothing, through to seeing a real graph
rendered and the GPU layout step working. See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) if any
step here doesn't behave as described — five real problems hit building this are documented there
in depth; this file only gives the working command.

## 1. Prerequisites

- **Docker + Docker Compose**
- GPU layout step only (optional, skip if you just want to view a graph): a host with an NVIDIA
  GPU, the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  installed, and a CDI spec regenerated against your currently installed driver
  (`sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml`) — see
  [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#1-gpu-reservation-could-not-select-device-driver-nvidia)
  if this errors.

## 2. Clone and start the dashboard + its bundled Neo4j

```bash
git clone https://github.com/danindiana/sessionarchive.git
cd sessionarchive/cosmosgl-dashboard
docker compose up -d --build neo4j server
```

Bound to `127.0.0.1:27474` (Neo4j browser), `127.0.0.1:27687` (Bolt), and `127.0.0.1:28686`
(dashboard) by default — override with `NEO4J_HTTP_PORT`/`NEO4J_BOLT_PORT`/`DASHBOARD_PORT` (env
vars or `.env`) if those ports are already taken by something else on your box (e.g. a live
`paper-processor-neo4j` instance also using 7474/7687).

## 3. Load the example dataset

The bundled Neo4j starts genuinely empty — there's nothing to look at yet. Load the small demo
graph (5 papers, 6 concepts, 2 theorems, 3 algorithms, 2 code snippets, 2 diagrams, ~20 edges):

```bash
docker compose exec -T neo4j cypher-shell -u neo4j -p password123 < examples/demo_seed.cypher
```

Wait for Neo4j to be ready first if this is a cold start — if it errors with a connection refused,
give it another 10-20 seconds and retry (see
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#4-healthcheck-racing-neo4js-slow-cold-start)).

## 4. Open the dashboard

Open `http://localhost:28686`. You should see 20 colored points (all clustered near the origin —
`compute_layout.py` hasn't run yet, so every node's `fx`/`fy` defaults to `0.0`). Double-click a
node for its detail modal; `Paper` nodes get an "Open source PDF" link (it 404s here since
`examples/demo_seed.cypher` uses placeholder paths — that's expected).

## 5. Run the GPU layout step

```bash
docker compose run --rm layout
```

Spreads those 20 nodes into a real force-directed layout via cuGraph's `force_atlas2` on the GPU.
Refresh `http://localhost:28686` afterward — the graph should now be visibly spread out instead of
stacked at the origin. Verify directly via the Neo4j Browser at `http://localhost:27474` if you
want to confirm `fx`/`fy` got written:

```cypher
MATCH (n) RETURN n.name, n.fx, n.fy LIMIT 5
```

## 6. Run the test suite

```bash
pip install -r requirements-test.txt
pytest tests/test_cosmos_server_unit.py -v   # fast, no Docker/GPU required
pytest tests/test_container_smoke.py -v      # builds + runs its own stack, seeds its own data, hits the live API
```

The smoke test suite manages its own Docker stack and test data independently of what you set up
in steps 2-3 above — safe to run either before or after manually exploring the dashboard.

## 7. Tear down

```bash
docker compose down -v
docker run --rm -v "$(pwd)/data:/data" alpine sh -c "rm -rf /data/neo4j /data/neo4j-logs"
```

The second command matters: Neo4j's container writes `./data/neo4j*` as its internal uid (7474),
which your host user can't remove directly (a plain `rm -rf ./data` will silently leave those two
directories behind). See
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#3-bind-mounted-neo4j-data-owned-by-the-containers-uid)
for why.

## You're done

```bash
docker compose up -d --build neo4j server
docker compose exec -T neo4j cypher-shell -u neo4j -p password123 < examples/demo_seed.cypher
docker compose run --rm layout
```

Same three commands, any time you want a fresh working demo from scratch.
