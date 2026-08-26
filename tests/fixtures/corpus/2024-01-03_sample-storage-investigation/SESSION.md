# Sample Storage Investigation (fixture data)

**Date:** 2024-01-03
**Host:** test-fixture-host

## Summary

Third synthetic fixture file, present so the interactive-labeling test has a
chunk left over after labeling the first two, letting it exercise a manual
retrain (`t`) with unlabeled candidates still remaining. Describes a
fictional external drive that kept unmounting under sustained write load.

## What happened

An external USB drive would unmount itself mid-transfer during large sequential
writes. `dmesg` showed USB reset events correlating with the drops. Switching
from a USB hub to a direct port connection resolved the issue; the drive has
completed several large transfers since without disconnecting.

## Commands used

```bash
dmesg -w | grep -i usb
lsusb -t
```

## Outcome

Resolved. No further unmounts since switching to a direct port.
