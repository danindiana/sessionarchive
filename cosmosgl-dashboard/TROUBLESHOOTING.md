# Troubleshooting

Five real problems, each actually hit and fixed while building and manually testing this
subproject — not speculative. See also [`diagrams/catch22s.png`](diagrams/catch22s.png) for the
visual version of the first two.

## 1. GPU reservation: could not select device driver "nvidia"

```
Error response from daemon: could not select device driver "nvidia" with capabilities: [[gpu]]
```

This means your host has **CDI-based** GPU passthrough (the modern NVIDIA Container Toolkit
default) rather than the legacy `nvidia` Docker runtime. `docker-compose.yml`'s `layout` service
already uses the CDI device syntax:

```yaml
devices:
  - "nvidia.com/gpu=0"
```

instead of the older

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: [gpu]
```

which requires a registered `nvidia` Docker runtime. If you still hit this error, check which
mechanism your host actually has: `docker info | grep -i runtime` (look for a registered `nvidia`
runtime) vs. `docker info | grep cdi` (look for `cdi: nvidia.com/gpu=...` device entries), and
match the compose syntax accordingly.

If CDI devices show up empty or you get a follow-on error about a missing file (e.g. a Vulkan ICD
path), your CDI spec is likely stale relative to your installed driver — regenerate it:

```bash
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
```

## 2. cugraph.force_atlas2() segfault

```
Caught signal 11 (Segmentation fault: Sent by the kernel at address (nil))
...
 4  /lib/x86_64-linux-gnu/libcuda.so(+0x335718)
 5  /lib/x86_64-linux-gnu/libcuda.so(cuCtxGetDevice_v2+0x20)
...
20  .../cugraph/layout/force_atlas2_wrapper.cpython-311-x86_64-linux-gnu.so(+0x1c5cf)
```

A RAPIDS-version-vs-driver ABI mismatch, not a bug in `compute_layout.py`. Hit with
`rapidsai/base:24.12-cuda12.5-py3.11` against a driver from the CUDA-13.0 generation
(`nvidia-smi` reporting `CUDA Version: 13.0`). Two targeted workarounds were tried and **did not**
fix it:
- Restricting to a single GPU (`nvidia.com/gpu=0` instead of `=all`), in case a mismatched
  multi-GPU pair confused UCX's topology probing
- Setting `UCX_TLS=tcp` to disable UCX's GPUDirect/CUDA-IPC transport probing

What did fix it: bumping the base image to `rapidsai/base:25.10-cuda12.9-py3.11` (closer to the
host's actual driver/CUDA generation). If you hit this on a different host, check `nvidia-smi` for
your driver/CUDA version and look for a `rapidsai/base` tag built against a closer CUDA version —
`docker manifest inspect rapidsai/base:<tag>` checks whether a tag exists before you pull ~5GB to
find out.

## 3. Bind-mounted Neo4j data owned by the container's uid

`docker-compose.yml` bind-mounts `./data/neo4j` and `./data/neo4j-logs` into the `neo4j` container.
The Neo4j image writes those directories as its internal uid (`7474`), so your host user can't
remove them directly — `rm -rf ./data` either fails outright or (with a permissive parent
directory) silently leaves those two subdirectories behind. `docker compose down -v` doesn't help
either — it only removes named/anonymous volumes, not bind mounts.

The fix is a throwaway container that removes the files as root instead of relying on host-side
permissions (and doesn't require `sudo` on the host):

```bash
docker run --rm -v "$(pwd)/data:/data" alpine sh -c "rm -rf /data/neo4j /data/neo4j-logs"
```

This is exactly what `tests/conftest.py`'s `docker_stack` fixture does before and after every test
run, for the same reason.

## 4. Healthcheck racing Neo4j's slow cold start

The `server` service's healthcheck hits `/api/graph`, which queries Neo4j — but `cosmos_server.py`
starts and accepts connections well before Neo4j finishes booting its bolt listener on a cold
start. A healthcheck (or a manual `curl`) that assumes instant readiness will see connection
errors or 500s for the first 10-30+ seconds, which looks like a broken deployment but isn't.

`docker-compose.yml`'s healthcheck already accounts for this with retries and a start period:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8686/api/graph', timeout=3)"]
  interval: 5s
  timeout: 5s
  retries: 20
  start_period: 10s
```

If you're scripting against this stack yourself, poll `docker inspect -f
'{{.State.Health.Status}}' cosmosgl-dashboard-server` until it reports `healthy` rather than
assuming the container being "up" means the API is ready — exactly what
`tests/conftest.py`'s `_wait_for_healthy` helper does.

## 5. esbuild multi-stage COPY path escaping the build context (dev-facing)

Only relevant if you modify `frontend/build.mjs`. An earlier version had `build.mjs`'s `outfile`
set to `../server/static/cosmos_bundle.js` — convenient for running `node build.mjs` by hand from
inside `frontend/`, but `Dockerfile.server`'s `frontend-build` stage has `WORKDIR /build` with no
sibling `/server` directory, so the build silently wrote outside the expected location and the
final stage's `COPY --from=frontend-build` couldn't find the file.

The fix: keep build outputs local to the build stage's own `WORKDIR` (`outfile: "dist/cosmos_bundle.js"`),
and have the final stage's `COPY --from=frontend-build /build/dist/cosmos_bundle.js
./static/cosmos_bundle.js` reference that same absolute-within-the-stage path. If you change where
`build.mjs` writes its output, update the `COPY --from` line in `Dockerfile.server` to match.
