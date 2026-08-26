#!/usr/bin/env python3
"""
End-to-end integration test for `sessionarchive label`'s raw-TTY interaction.

`_getch()` in label.py needs a real tty device (termios.tcgetattr/tty.setraw
raise "Inappropriate ioctl for device" on a plain pipe) -- so this can't be
tested by just piping bytes into stdin. Instead it allocates a real
pseudo-terminal (Python's `pty` module) and drives `docker compose run --rm
-it app label` through it, sending single-byte keystrokes exactly as a human
would. This exercises the identical code path a real terminal session does.

Requires the full stack already up (this is an integration test, not a unit
test):
    docker compose up -d neo4j
    ollama serve   # with at least one model pulled

Usage:
    python3 tests/test_label_interactive.py

Ingests the fixture corpus into a throwaway temp index dir (mounted ad hoc
via `docker compose run -v`, since it's outside the paths docker-compose.yml
mounts by default), labels 3 chunks (y, n, y), forces a retrain (t), quits
(q), and asserts the results actually persisted to disk with the expected
content. Cleans up the temp index dir afterward regardless of outcome.
"""
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_CORPUS = Path(__file__).resolve().parent / "fixtures" / "corpus"
CONTAINER_CORPUS = "/data/test_corpus"
CONTAINER_INDEX = "/data/test_index"


def run_compose(extra_mounts, *args, timeout=300):
    mount_flags = []
    for host_path, container_path, mode in extra_mounts:
        suffix = f":{mode}" if mode else ""
        mount_flags += ["-v", f"{host_path}:{container_path}{suffix}"]
    result = subprocess.run(
        ["docker", "compose", "run", "--rm"] + mount_flags + list(args),
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout,
    )
    return result


def drive_pty(argv, keystrokes, initial_wait=90, per_key_wait=10):
    """Run argv attached to a real pty, sending `keystrokes` (list of bytes)
    with `per_key_wait` seconds between each. Returns (all_output, exit_code)."""
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        argv, stdin=slave, stdout=slave, stderr=slave, cwd=REPO_ROOT, close_fds=True,
    )
    os.close(slave)

    all_output = b""

    def read_for(seconds):
        nonlocal all_output
        end = time.time() + seconds
        while time.time() < end:
            r, _, _ = select.select([master], [], [], 0.5)
            if master in r:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                all_output += chunk

    read_for(initial_wait)
    for key in keystrokes:
        os.write(master, key)
        read_for(per_key_wait)

    try:
        exit_code = proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        exit_code = -9

    os.close(master)
    return all_output, exit_code


def main():
    tmp_index = Path(tempfile.mkdtemp(prefix="sessionarchive_test_index_"))
    print(f"Using temp index dir: {tmp_index}")

    corpus_mount = (str(FIXTURE_CORPUS), CONTAINER_CORPUS, "ro")
    index_mount = (str(tmp_index), CONTAINER_INDEX, None)

    try:
        print("\n=== ingesting fixture corpus ===")
        r = run_compose(
            [corpus_mount, index_mount],
            "app", "ingest",
            "--root", CONTAINER_CORPUS,
            "--index-dir", CONTAINER_INDEX,
        )
        print(r.stdout[-2000:])
        if r.returncode != 0:
            print(r.stderr[-2000:])
            sys.exit(f"ingest failed with exit code {r.returncode}")

        id_map_path = tmp_index / "id_map.json"
        assert id_map_path.exists(), "ingest did not produce id_map.json"
        id_map = json.loads(id_map_path.read_text())
        # The three fixture files are short (<4000 chars, the default chunk
        # size), so each produces exactly one chunk -- 3 total. Labeling only
        # 2 of them (below) deliberately leaves one candidate remaining, so
        # `t` exercises a manual retrain mid-session rather than the loop
        # just ending naturally once every candidate is labeled.
        assert len(id_map) == 3, f"expected 3 chunks from fixture corpus, got {len(id_map)}"
        print(f"Ingested {len(id_map)} chunks across the fixture corpus.")

        print("\n=== driving label interactively via a real pty ===")
        output, exit_code = drive_pty(
            ["docker", "compose", "run", "--rm", "-v", f"{tmp_index}:{CONTAINER_INDEX}",
             "-it", "app", "label", "--index-dir", CONTAINER_INDEX],
            keystrokes=[b"y", b"n", b"t", b"q"],
        )
        text = output.decode(errors="replace")
        print(text)

        assert exit_code == 0, f"label exited with {exit_code}, expected 0"
        assert "Auto-retraining probe" in text, "retrain (t) did not trigger"
        assert "Session done" in text, "quit (q) did not print session summary"

        labels_path = tmp_index / "relevance_labels.json"
        probe_path = tmp_index / "relevance_probe.pt"
        assert labels_path.exists(), "relevance_labels.json was not persisted"
        assert probe_path.exists(), "relevance_probe.pt was not persisted"
        labels = json.loads(labels_path.read_text())
        assert len(labels) == 2, f"expected 2 persisted labels, got {len(labels)}"
        assert [r["label"] for r in labels] == [1, 0], "labels don't match the y/n sent"

        print("\nPASS: label's interactive TTY loop behaves correctly end to end.")
    finally:
        shutil.rmtree(tmp_index, ignore_errors=True)


if __name__ == "__main__":
    main()
