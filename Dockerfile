FROM python:3.11-slim

# Without this, `import torch` (the CUDA-capable PyPI wheel, no GPU passthrough
# configured) segfaults inside this container with a C++ std::length_error in
# its OpenMP thread-count init path — see diagrams/catch22s.png.
ENV OMP_NUM_THREADS=1

WORKDIR /app

# python:3.11-slim ships pip 24.0. It reproducibly failed with "PACKAGES DO
# NOT MATCH THE HASHES" on the exact same small file (h11-0.16.0, 37KB)
# across every network configuration tried (default bridge, host-networked
# build) — ruling out network corruption. Matches a known class of hash-
# verification bugs in older pip under concurrent/parallel downloads,
# fixed upstream since. See diagrams/catch22s.png.
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY sessionarchive/ sessionarchive/
RUN pip install --no-cache-dir --no-deps -e . \
 || pip install --no-cache-dir --no-deps -e .

ENTRYPOINT ["sessionarchive"]
