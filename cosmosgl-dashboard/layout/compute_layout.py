#!/usr/bin/env python3
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# compute_layout.py
# One-shot GPU ForceAtlas2 layout: pulls the graph topology out of Neo4j,
# runs cuGraph's force_atlas2 on the GPU, and writes the resulting (x, y)
# back onto each node as fx/fy. cosmos_server.py's /api/graph then serves
# those coordinates directly, so the CosmosGL frontend renders a static
# layout (enableSimulation: false) instead of simulating in the browser.
#
# Adapted from paper_processor/neo4j_viz/compute_layout.py for standalone
# containerized use: connection details are env-configurable instead of
# hardcoded. Run via `docker compose run --rm layout` — this is not a
# long-running daemon.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import sys
import time

import cudf
import cugraph
import neo4j
import pandas as pd

NEO4J_URL = os.environ.get("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password123")
MAX_ITER = int(os.environ.get("LAYOUT_MAX_ITER", "500"))
SCALE = float(os.environ.get("LAYOUT_SCALE", "20"))

print("Connecting to Neo4j...")
driver = neo4j.GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    print("Fetching edges for GPU layout...")
    res = session.run("""
        MATCH (s)-[r]->(t)
        RETURN id(s) as source, id(t) as target
    """)
    edges = [(r["source"], r["target"]) for r in res]

    if not edges:
        print("No edges found. Graph is empty.")
        sys.exit(0)

    print(f"Loaded {len(edges)} edges. Transloading to GPU VRAM...")

    pdf = pd.DataFrame(edges, columns=['source', 'target'])
    gdf = cudf.DataFrame(pdf)

    print("Building cuGraph topology...")
    G = cugraph.Graph()
    G.from_cudf_edgelist(gdf, source='source', destination='target', renumber=True)

    print("Running GPU ForceAtlas2 Physics Simulation...")
    t0 = time.time()
    pos_df = cugraph.force_atlas2(G, max_iter=MAX_ITER, strong_gravity_mode=False, outbound_attraction_distribution=True, lin_log_mode=False)
    t1 = time.time()
    print(f"GPU Layout computed in {t1-t0:.4f} seconds!")

    pos_pdf = pos_df.to_pandas()

    print("Pushing computed (x,y) coordinates back to Neo4j...")
    updates = pos_pdf.to_dict('records')

    session.run("""
        UNWIND $updates AS row
        MATCH (n) WHERE id(n) = row.vertex
        SET n.fx = row.x * $scale, n.fy = row.y * $scale
    """, updates=updates, scale=SCALE)
    print("Update complete! The frontend is now a static WebGL renderer.")
