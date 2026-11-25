# XINJI COBEE C1 smartwatch - control from Linux over BLE (no phone, no touchscreen)

> **Unofficial, use at your own risk.** Not affiliated with XINJI/Linwear. Never send `OFF`, `RST`, `RES`, `OTA`, `SUM`, `JMP`.

Verified 2026-11-25 on Ubuntu (BlueZ 5.x, kernel 7.0, `gatttool` present). Watch: **XINJI-C1**,
BLE public address (use your own MAC, see below), advertises as `XINJI-C1`.
Problem solved: touchscreen dead, so the phone app (OnWear Pro) could not bind (needs a tap on
the watch) and the date/time could not be fixed. The watch's clock was ~70 days wrong; fixed from the laptop.

## TL;DR - set the clock (works)
First `export WATCH_MAC=AA:BB:CC:DD:EE:FF` (find it via `bluetoothctl scan on`, device `XINJI-C1`), or save it as `WATCH_MAC=...` in `~/.config/xinji-c1-watch/config`.
```
bluetoothctl pair/trust the watch once (see "Pairing"), then:
python3 -I watch.py sync-time     # sets UTC clock = this PC, verifies by reading it back
python3 -I watch.py info          # battery, versions, tz, clock
python3 -I watch.py raw 'AT+GBS?' # any AT command
```
`watch.py` is in this folder. It needs `gatttool` (package `bluez`, deprecated tools) and the watch bonded.

## The protocol (reverse-engineered from the OnWear Pro APK, package `com.linwear.top`, v1.5.1.35)
The vendor SDK is `com.szfission.wear.sdk` (class `CMDHelper`). It is a **plain-text AT protocol**, no auth/bind step.
- GATT service `c2e6ffb0-e966-1000-8000-bef9c223df6a`
  - `c2e6ffb3` (decl handle 0x0014, **value handle 0x0015**) - WRITE: AT commands
  - `c2e6ffb4` (decl 0x0016, value 0x0017, **CCC 0x0018**) - NOTIFY: replies
  - `c2e6ffb1` write / `c2e6ffb2` notify (decl 0x000f/0x0011) - "big data" channel (dial/watch-face/OTA/GPS files), not used here
  - `c2e6ffb6` notify (decl 0x0019) - other notifications
- Other services (not needed): Battery 180f, HID 1812 (camera shutter), `d0ff-3c17-d293-8e48-14fe2e4da212`, `6287-3c17-...` (Realtek/JL style OTA/DFU).
- Frame: ASCII `AT+<CMD>?` to read, `AT+<CMD>:<value>` to set, **terminated by a NUL byte (0x00)**. A trailing space also worked.
- Replies arrive as notifications on 0x0017: `AT+<CMD>:<value>` (set echoes the value), or `AT+ERR:INVAL PARA` for a bad argument.
- Replies are truncated to 20 bytes (default ATT payload); a bigger MTU (`mtu 185`) did not change this for GSV.
- To receive replies you must first write `0100` to CCC 0x0018.

### Verified commands (exact replies seen)
| Command | Meaning | Reply seen |
|---|---|---|
| `AT+GUT?` | get clock, unix seconds **UTC** | `AT+GUT:1795625757` |
| `AT+SUT:<unix_utc_seconds>` | **set clock** | echoes `AT+SUT:<n>`, then GUT matches |
| `AT+GTZ?` | timezone in **minutes** | `AT+GTZ:360` (already UTC+6, correct) |
| `AT+STZ:<x>` | set timezone | `AT+STZ:360` and `:6` -> `AT+ERR:INVAL PARA` (unchanged tz; value format still unknown) |
| `AT+GBS?` | battery `percent,charging` | `AT+GBS:72,0` |
| `AT+GSV?` | firmware version (truncated) | `AT+GSV:HB-V1.00,SV0.` |
| `AT+GPV?` | protocol version | `AT+GPV:Pv1.0` |
| `AT+GUV?` | UI/watchface version | `AT+GUV:415-01` |
| `AT+GBT?` | screen-on time (s) | `AT+GBT:10` (set with `AT+SBT:<n>`) |
| `AT+GES?` | sport state | `AT+GES:0` |
| `AT+FSS:19,<0\|1>` | **raise-to-wake (lift wrist to light screen)** on/off. VERIFIED physically 2026-11-25: was off; `19,1` -> screen wakes on wrist raise | echoes `AT+FSS:19,1` |

### Known but NOT tested (names from `CMDHelper`; semantics inferred) - treat as untested
Settings: `SLG` language, `SHM` 12/24h mode, `SDU` units, `SWF` watchface, `SBT` screen time, `SMI`, `ESS`, `ETM`, `NRS`, `SFP`, `STU`, `BDC/BDQ`, `CCS/CHD/CWS/CVS/CPM/CLS/CLU/CDC/DCC/CSC/PCC` (toggle flags), `TTP` camera, `SPS` phone OS, `SUI` update UI.
Reads: `GRH`, `GPV`, `GAI`, `TFD/TFP`, `DFP`, `FDL` (file/dial transfer; FSS is the function-switch setter above), `GPS/SGP/CFD` (gps/files), `MTU`.
**Dangerous - never send casually:** `OFF` (power off), `RST`/`RES` (reset/restore), `OTA`/`SUM`/`JMP` (firmware update). 
Time-model detail from the app: if the watch supports timezones the app sends `SUT`=UTC seconds and `STZ`=offset minutes; otherwise `SUT`=UTC+offset seconds and tz 0. This watch behaved as the first kind (clock displays right with UTC SUT + tz 360).

## Pairing / connection - the real struggle (read before debugging)
1. Bluetooth may be soft-blocked: `rfkill unblock bluetooth; bluetoothctl power on`.
2. Pairing needs **no tap on the watch** from Linux: `bluetoothctl` -> `agent NoInputNoOutput`, `default-agent`, `scan on`, `pair <MAC>`, `trust <MAC>`. An unbonded device refuses connections. If connections act weird, `remove <MAC>`, rescan (it advertises only when disconnected from other hosts), re-pair. The watch holds ONE bond: remove it here before pairing a phone.
3. **The link flaps**: the watch connects ~6 s, drops, reconnects ~3 s later, forever. BlueZ's battery/HID(HOG) plugins hit ATT "unlikely error" against this watch (journal spam) and BlueZ keeps the ATT channel busy, so interactive/slow tooling fails (`Device or resource busy`, `Not connected`).
4. **What works:** `gatttool -I` + a *burst*: wait for "Connection successful", then immediately pipe `char-write-req 0x0018 0100` and all `char-write-cmd 0x0015 <hex>` lines in one write; read notifications for ~5 s; retry whole thing until replies come (often 1-10 tries, sometimes 20). `watch.py` does this.
5. What did NOT work: python-dbus GATT via bluetoothctl/BlueZ (link dies before writes), raw L2CAP ATT socket (`bind` -> EBUSY, connect -> EINVAL because bluetoothd owns CID 4), spacing commands 1 s apart, sending single bytes / guessed frames to `ffb1` (no replies - wrong channel; AT goes to `ffb3`).
6. Restarting bluetoothd (`sudo systemctl restart bluetooth`) coincided with the first successful reply; plugins stayed loaded, so it may just be a cleaner state. Needs sudo (agent has no sudo password) - ask the user.
7. `bluetoothctl disconnect <MAC>` before running, so BlueZ's own reconnect doesn't hold the channel.

## How this was reverse-engineered (to extend it)
- Companion app: **OnWear Pro** (Shenzhen Linwear, Android `com.linwear.top`; older C1 used "OnWear"). The author downloaded the xapk (`OnWear+Pro_1.5.1.35_APKPure.xapk`) from a mirror; automated mirror scraping was blocked.
- No java/jadx on the machine; used `uv venv` + `uv pip install androguard` and scripted dex searches: find `c2e6ffb0` string -> `classes7.dex` -> `com/szfission/wear/sdk/parse/CMDHelper` (`getSetTimeBytes` = `"SUT"`, `getSetATBytes` builds `AT+<cmd>:<val>\0`, `sendAT` writes `ffb3`, notifies `ffb4`) and callers `FissionSdkBleManage.setTimes/setTimezone` (classes3) and `lw/commonsdk/sdk/FissionSdk.topTime` (classes6).
- Searching the web for the UUID found nothing useful; the APK was the answer.

## Safety notes
- Only read commands and `SUT` were sent to the real watch. No resets/OTA/off.
- The watch is left bonded to the Linux laptop; `bluetoothctl remove <WATCH_MAC>` frees it for a phone.

## Settings notes (added after raise-to-wake test)
- `AT+FSS:<index>,<0|1>` is a general "function switch" setter; index 19 = raise-to-wake (SDK name `WBScreen`). Other indexes untested. State CANNOT be read back: `AT+FSS?`, `AT+CWS?`, `AT+CHD?`, `AT+CCS?`, `AT+CVS?`, `AT+CPM?` just echo the command name with no value.
- Replies to sets are sometimes missing on the first try (link flaps); just resend - setting is idempotent. Confirm by the echo or by testing on the watch.
- The app's richer raise-to-wake (time window) uses the **big-data channel**: command id `0308`, payload 8 bytes = start(2B BE minutes) end(2B BE minutes) enable(1B) + zeros; read id `0208`. Frame = 20-byte header `FF FF 42 47 01 00 <id1> <id2> <len hi> <len lo> <payload..10-17> <cksum>` where cksum = `~(sum>>8)`, `~(sum&255)` over the header with cksum bytes zero; written to `c2e6ffb1` (value handle 0x0010), replies on `c2e6ffb2` (CCC 0x0013). **Sent header-only reads (0101, 0103, 0206, 0208, 0252) with this framing: writes acked but the watch NEVER replied** - big-data framing/handshake still unsolved (or unsupported by the C1). Use AT commands instead.
- Full list of big-data ids (health records 0180-018A, alarms 0201, DND 0206, user info 0200, hardware info 0101, etc.) is in the APK class `FissionSdkBleManage`; all unverified.

## Install as a Claude Code skill
```
git clone https://github.com/ashraful1971/xinji-c1-watch ~/.claude/skills/xinji-c1-watch
```
Then ask Claude to "sync my watch time". `re-tools/` holds the APK-analysis scripts used for the research (optional).

## License
MIT - see LICENSE.
