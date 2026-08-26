# Container smoke tests: builds the real image, starts neo4j + server via
# docker compose, seeds a small known graph, and hits the live HTTP API.
# Excludes the `layout` (GPU) service — see cosmosgl-dashboard/README.md for
# how to verify that one manually with `docker compose run --rm layout`.
import requests

from conftest import BASE_URL


def test_dashboard_root_serves_html(docker_stack):
    res = requests.get(f"{BASE_URL}/", timeout=10)
    assert res.status_code == 200
    assert "CosmosGL Dashboard" in res.text


def test_api_graph_returns_seeded_nodes_and_edges(seeded_graph):
    res = requests.get(f"{BASE_URL}/api/graph", timeout=10)
    assert res.status_code == 200
    body = res.json()

    labels = {n["label"] for n in body["nodes"]}
    assert {"Test Paper", "Test Concept", "Isolated Theorem"} <= labels
    assert len(body["edges"]) >= 1

    isolated = next(n for n in body["nodes"] if n["label"] == "Isolated Theorem")
    assert isolated["fx"] == 0.0
    assert isolated["fy"] == 0.0


def test_api_node_detail_found_and_missing(seeded_graph):
    nodes = requests.get(f"{BASE_URL}/api/graph", timeout=10).json()["nodes"]
    paper = next(n for n in nodes if n["label"] == "Test Paper")

    detail_res = requests.get(f"{BASE_URL}/api/node/{paper['id']}", timeout=10)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["type"] == "Paper"
    assert detail["props"]["name"] == "Test Paper"

    missing_res = requests.get(f"{BASE_URL}/api/node/999999999", timeout=10)
    assert missing_res.status_code == 404


def test_pdf_not_on_disk_returns_404_with_explanation(seeded_graph):
    nodes = requests.get(f"{BASE_URL}/api/graph", timeout=10).json()["nodes"]
    paper = next(n for n in nodes if n["label"] == "Test Paper")

    pdf_res = requests.get(f"{BASE_URL}/pdf/{paper['id']}", timeout=10)
    assert pdf_res.status_code == 404
    assert "not available on disk" in pdf_res.text
    assert "/nonexistent/paper.pdf" in pdf_res.text
