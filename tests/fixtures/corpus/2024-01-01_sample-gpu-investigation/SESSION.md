# Sample GPU Investigation (fixture data)

**Date:** 2024-01-01
**Host:** test-fixture-host

## Summary

This is synthetic fixture content for testing `sessionarchive`'s ingest and
label pipelines end to end. It describes a fictional GPU display issue: a
secondary graphics card stopped being detected after a firmware update, and
the fix involved re-seating the card and disabling a conflicting PCIe
power-management setting in the BIOS.

## What happened

The system failed to detect the secondary GPU after a routine firmware
update. `lspci` showed the device missing entirely from the bus listing,
suggesting a link-training failure rather than a driver problem. Re-seating
the card and disabling ASPM (Active State Power Management) in the BIOS
resolved the issue; the device now enumerates correctly on every boot.

## Commands used

```bash
lspci -tv
lspci -vvv -s 01:00.0
dmesg | grep -i pcie
```

## Outcome

Resolved. The secondary GPU is now stable across reboots.
