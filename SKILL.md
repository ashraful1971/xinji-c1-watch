---
name: xinji-c1-watch
description: Set the clock, toggle raise-to-wake, or read battery/versions on a XINJI COBEE C1 smartwatch (OnWear Pro / szfission AT protocol) from Linux over Bluetooth LE, without the phone app or touchscreen. Use when the user wants to fix the date/time, turn raise-to-wake on/off, or send AT commands to this watch.
---

# XINJI C1 watch control (Linux, BlueZ)

Everything is in this folder. Read `README.md` for protocol, handles, pairing and troubleshooting.

## Quick use
Run from any directory (python `-I` mode), watch must be bonded to this PC:

    python3 -I watch.py sync-time     # set clock to this PC's time, verifies by reading back
    python3 -I watch.py wake on       # raise-to-wake ON   (AT+FSS:19,1)
    python3 -I watch.py wake off      # raise-to-wake OFF  (AT+FSS:19,0)
    python3 -I watch.py info          # battery, versions, timezone, clock
    python3 -I watch.py raw 'AT+GBS?' # any AT command

Set the watch address first: `export WATCH_MAC=AA:BB:CC:DD:EE:FF` (or `WATCH_MAC=...` in `~/.config/xinji-c1-watch/config`). More retries with `TRIES=40`.

## Before you run it (preconditions)
1. Bluetooth on: `rfkill unblock bluetooth; bluetoothctl power on`. Needs `gatttool` (bluez).
2. Watch bonded: `bluetoothctl` -> `agent NoInputNoOutput`, `default-agent`, `scan on`, `pair <MAC>`, `trust <MAC>` (no tap on the watch needed). Check `bluetoothctl info <MAC>` shows `Paired: yes`. The watch keeps only one bond - remove it from phones/this PC first if pairing fails.
3. Tiny tool, no memory concerns.

## Things to know (hard-won)
- The watch drops the BLE link every ~6 s. The tool sends all commands in one burst right after connect and retries (up to a minute). "no reply" -> just run again; all commands are idempotent.
- Time is UTC unix seconds (`AT+SUT:<n>`); the watch is already on UTC+6 (`AT+GTZ:360`); setting the timezone is rejected - don't bother.
- Raise-to-wake state cannot be read back. Confirm by having the user raise their wrist.
- NEVER send `OFF`, `RST`, `RES`, `OTA`, `SUM`, `JMP` (power off / reset / firmware). Other untested AT/FSS commands: try one at a time, tell the user what you sent.
- Don't use python-dbus GATT, raw L2CAP sockets, or slow step-by-step gatttool sessions - all failed (see README).
- The big-data channel (c2e6ffb1/ffb2, ids like 0308) gets no replies; stick to AT commands.

## Verified
2026-11-25 on Ubuntu/BlueZ 5.x: clock set + read back; battery/version reads; raise-to-wake toggled and confirmed physically. Other firmware/hosts untested.
