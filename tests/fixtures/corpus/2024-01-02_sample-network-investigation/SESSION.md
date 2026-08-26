# Sample Network Investigation (fixture data)

**Date:** 2024-01-02
**Host:** test-fixture-host

## Summary

Synthetic fixture content, unrelated to the GPU fixture in this test corpus
on purpose, so retrieval tests can check that a GPU-related query doesn't
just return everything indiscriminately. Describes a fictional intermittent
LAN dropout traced to a flaky ethernet cable.

## What happened

Intermittent connection drops occurred every few hours on the wired
connection. `ethtool` showed rising CRC error counts on the interface, which
pointed at a physical-layer issue rather than a driver or routing problem.
Replacing the ethernet cable resolved the drops entirely; CRC errors stopped
accumulating after the swap.

## Commands used

```bash
ethtool -S eth0 | grep -i crc
ip -s link show eth0
```

## Outcome

Resolved. No further drops after replacing the cable.
