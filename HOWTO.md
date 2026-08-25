# HOWTO: cold-start setup

Setting up `sessionarchive` on a fresh box from nothing. See
[`diagrams/start_up_howto.png`](diagrams/start_up_howto.png) for the visual
flowchart version.

## 1. Prerequisites

- **Docker + Docker Compose**
- **Ollama** — installed and running (`ollama serve`), with at least one
  instruction-following model pulled (`ollama pull qwen3:14b`, or any other —
  override via `--model`)
- No GPU required — bge-m3 and FAISS's `IndexFlatIP` both run fine on CPU;
  a CUDA GPU speeds up embedding if present in the container

## 2. Clone and point it at a corpus

```bash
git clone https://github.com/danindiana/sessionarchive.git
cd sessionarchive
mkdir -p data/corpus data/index
```

Put (or symlink) your session folders under `data/corpus/` — one level of
dated folders, each with a `SESSION.md`, `README.md`, or any `.md` file as
its primary content.

## 3. Start the bundled Neo4j

```bash
docker compose up -d neo4j
```

Bound to `127.0.0.1:7474` (browser) / `127.0.0.1:7687` (Bolt) by default —
override with `NEO4J_HTTP_PORT`/`NEO4J_BOLT_PORT` (env vars or a `.env` file)
if those ports are already taken by something else on your box.

## 4. Check Ollama is reachable

```bash
curl -s http://localhost:11434/api/tags | head -c 200
```

Should return JSON, not a connection error.

**If Ollama is bound to `127.0.0.1` only** (a common default, and the case
this project was originally built against) — the `app` service in
`docker-compose.yml` already uses `network_mode: host` on Linux specifically
so it can reach a loopback-only Ollama. See
[`diagrams/catch22s.png`](diagrams/catch22s.png) for why `host.docker.internal`
+ bridge networking doesn't work for this case. On Mac/Windows, switch the
`app` service to bridge networking + `extra_hosts: ["host.docker.internal:host-gateway"]`
and set `OLLAMA_URL=http://host.docker.internal:11434` instead.

## 5. First run: smoke test on a handful of folders

```bash
docker compose run --rm app ingest --limit 5
```

The **first** ingest downloads `BAAI/bge-m3` from Hugging Face Hub (~2GB,
cached inside the container's filesystem afterward — rebuilding the image
re-downloads it, since it isn't in a volume by default). This can take a few
minutes; it isn't a hang.

## 6. Verify retrieval works

```bash
docker compose run --rm app query "<a question about one of those 5 folders>"
```

You should get the expected folder back as the top hit, with a similarity
score and a text snippet.

## 7. Ingest everything

```bash
docker compose run --rm app ingest
```

No `--limit` means "everything not already ingested." Resumable and
checkpointed — safe to interrupt and re-run.

## 8. Optional: teach it what's relevant

```bash
docker compose run --rm -it app label
```

Interactive, single-keypress (`y`/`n`/`s`/`t`/`q`) — needs a real TTY, so
`-it` is required here specifically (the `app` service deliberately does
**not** set `stdin_open`/`tty` by default — doing so made `ingest`/`query`
containers hang indefinitely after finishing, since the allocated pty never
closes; see `diagrams/catch22s.png`). Once you've labeled ~20+ chunks,
`query ... --rerank` will use the trained probe.

## You're done

```bash
docker compose run --rm app query "<question>"
docker compose run --rm app query --like <slug>
docker compose run --rm app query "<question>" --rerank
```
