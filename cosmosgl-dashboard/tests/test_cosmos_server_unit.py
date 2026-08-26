# Fast unit tests for server/cosmos_server.py's query-wrapping functions.
# No Docker, no GPU, no real Neo4j connection — neo4j.GraphDatabase.driver
# is monkeypatched with an in-memory fake. See test_container_smoke.py for
# end-to-end HTTP-level coverage against the real containerized stack.
import sys
import types
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
sys.path.insert(0, str(SERVER_DIR))

import cosmos_server  # noqa: E402


class FakeSession:
    def __init__(self, rows_by_query):
        self.rows_by_query = rows_by_query

    def run(self, query, **params):
        return self.rows_by_query.get(query, [])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeDriver:
    def __init__(self, rows_by_query):
        self.rows_by_query = rows_by_query

    def session(self):
        return FakeSession(self.rows_by_query)

    def close(self):
        pass


def _patch_driver(monkeypatch, rows_by_query):
    monkeypatch.setattr(
        cosmos_server.neo4j,
        "GraphDatabase",
        types.SimpleNamespace(driver=lambda *a, **k: FakeDriver(rows_by_query)),
    )


def test_fetch_graph_defaults_missing_fx_fy_to_origin(monkeypatch):
    nodes = [
        {"id": 1, "type": "Paper", "label": "A Paper", "fx": 1.5, "fy": -2.0},
        {"id": 2, "type": "Concept", "label": "Isolated", "fx": None, "fy": None},
    ]
    edges = [{"source": 1, "target": 2, "type": "MENTIONS"}]
    _patch_driver(monkeypatch, {cosmos_server.NODE_QUERY: nodes, cosmos_server.EDGE_QUERY: edges})

    result = cosmos_server.fetch_graph()

    assert result["nodes"][0]["fx"] == 1.5
    assert result["nodes"][0]["fy"] == -2.0
    assert result["nodes"][1]["fx"] == 0.0
    assert result["nodes"][1]["fy"] == 0.0
    assert result["edges"] == edges


def test_fetch_node_detail_returns_none_when_missing(monkeypatch):
    _patch_driver(monkeypatch, {cosmos_server.NODE_DETAIL_QUERY: []})
    assert cosmos_server.fetch_node_detail(999) is None


def test_fetch_node_detail_returns_first_row(monkeypatch):
    row = {"type": "Paper", "props": {"name": "A Paper"}}
    _patch_driver(monkeypatch, {cosmos_server.NODE_DETAIL_QUERY: [row]})
    assert cosmos_server.fetch_node_detail(1) == row


def test_fetch_pdf_path_returns_none_when_node_missing(monkeypatch):
    _patch_driver(monkeypatch, {cosmos_server.PDF_PATH_QUERY: []})
    assert cosmos_server.fetch_pdf_path(42) is None


def test_fetch_pdf_path_returns_stored_path(monkeypatch):
    _patch_driver(monkeypatch, {cosmos_server.PDF_PATH_QUERY: [{"pdf_path": "/data/some.pdf"}]})
    assert cosmos_server.fetch_pdf_path(1) == "/data/some.pdf"
