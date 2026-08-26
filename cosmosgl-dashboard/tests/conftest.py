import os
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", "28686"))
BOLT_PORT = int(os.environ.get("NEO4J_BOLT_PORT", "27687"))
BASE_URL = f"http://localhost:{DASHBOARD_PORT}"
BOLT_URL = f"bolt://localhost:{BOLT_PORT}"
NEO4J_AUTH = ("neo4j", "password123")


def _compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def _clean_data_dir():
    # Neo4j's own container writes ./data/neo4j* as its internal uid (7474),
    # which the host user can't remove. A throwaway container sidesteps that
    # permission mismatch instead of requiring sudo on the host.
    (ROOT / "data").mkdir(exist_ok=True)
    subprocess.run(
        ["docker", "run", "--rm", "-v", f"{ROOT / 'data'}:/data", "alpine",
         "sh", "-c", "rm -rf /data/neo4j /data/neo4j-logs"],
        check=True,
    )


def _wait_for_healthy(container, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", container],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() == "healthy":
            return
        time.sleep(2)
    raise TimeoutError(f"{container} did not become healthy within {timeout}s")


@pytest.fixture(scope="session")
def docker_stack():
    # Bind-mounted Neo4j data isn't cleaned up by `compose down -v` (that only
    # touches named/anonymous volumes), so wipe it explicitly for a fresh DB.
    _clean_data_dir()
    _compose("build", "server")
    _compose("up", "-d", "neo4j", "server")
    try:
        _wait_for_healthy("cosmosgl-dashboard-server")
        yield BASE_URL
    finally:
        _compose("down", "-v")
        _clean_data_dir()


@pytest.fixture(scope="session")
def seeded_graph(docker_stack):
    import neo4j

    seed_cypher = (ROOT / "tests" / "fixtures" / "seed.cypher").read_text()
    driver = neo4j.GraphDatabase.driver(BOLT_URL, auth=NEO4J_AUTH)
    try:
        with driver.session() as session:
            for statement in seed_cypher.split(";"):
                statement = statement.strip()
                if statement:
                    session.run(statement)
    finally:
        driver.close()
    return docker_stack
