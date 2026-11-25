#!/usr/bin/env python3
"""Control a XINJI COBEE C1 smartwatch (OnWear Pro / szfission "AT" protocol) from Linux.

Usage:
  watch.py sync-time            set watch clock to this machine's current time (UTC) and verify
  watch.py wake on|off          raise-to-wake (lift wrist to light screen) on/off  [AT+FSS:19,<1|0>]
  watch.py info                 read battery, versions, timezone, screen time, clock
  watch.py raw 'AT+GBS?' ...    send arbitrary AT commands, print replies

Needs: BlueZ + `gatttool` (bluez-deprecated tools), watch already paired/bonded (see README.md).
Why gatttool in a burst: the watch drops the BLE link ~6 s after connecting, so all commands
are piped in one go the instant "Connection successful" appears; we retry until replies arrive.
"""
import os, re, select, subprocess, sys, time

def _mac():
    """MAC from $WATCH_MAC, else WATCH_MAC=... in local.conf next to watch.py."""
    if os.environ.get("WATCH_MAC"): return os.environ["WATCH_MAC"]
    try:
        for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "local.conf")):
            if l.startswith("WATCH_MAC="): return l.split("=", 1)[1].strip()
    except OSError: pass
    sys.exit("Set your watch's Bluetooth address: export WATCH_MAC=AA:BB:CC:DD:EE:FF "
             "(or put WATCH_MAC=... in local.conf next to watch.py). Find it with `bluetoothctl scan on` (XINJI-C1).")


MAC = _mac()
H_CMD = "0x0015"      # c2e6ffb3  write  (AT commands)
H_NOTIFY_CCC = "0x0018"  # CCC of c2e6ffb4 notify (replies, handle 0x0017)
TRIES = int(os.environ.get("TRIES", "30"))


def term(c):
    """Commands are ASCII terminated with NUL (a trailing space also works)."""
    return c.replace("\\0", "\0") if "\0" in c or "\\0" in c else c + "\0"


def run_once(cmds, wait=5.0):
    p = subprocess.Popen(["gatttool", "-b", MAC, "-t", "public", "-I"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    fd = p.stdout.fileno(); os.set_blocking(fd, False)

    def rd(t):
        end = time.time() + t; out = b""
        while time.time() < end:
            if select.select([fd], [], [], 0.05)[0]:
                try: d = os.read(fd, 4096)
                except BlockingIOError: continue
                if not d: break
                out += d
        return re.sub(rb"\x1b\[[0-9;]*[mK]|\r", b"", out).decode(errors="ignore")

    def w(s): p.stdin.write(s.encode()); p.stdin.flush()
    w("connect\n"); t = ""; end = time.time() + 12
    while time.time() < end and "Connection successful" not in t and "Error" not in t:
        t += rd(0.1)
    if "Connection successful" not in t:
        w("exit\n"); return None
    lines = [f"char-write-req {H_NOTIFY_CCC} 0100"]
    lines += [f"char-write-cmd {H_CMD} {term(c).encode().hex()}" for c in cmds]
    w("\n".join(lines) + "\n")
    r = rd(wait); w("exit\n")
    return [bytes.fromhex(m.replace(" ", "")).decode(errors="replace").strip("\0 ")
            for m in re.findall(r"value: ([0-9a-f ]+)", r)]


def talk(cmds):
    """Retry until the watch answers every command (or give up)."""
    subprocess.run(["bluetoothctl", "disconnect", MAC], capture_output=True)
    best = []
    for i in range(TRIES):
        r = run_once(cmds)
        if r and len(r) > len(best): best = r
        if r and len(r) >= len(cmds): return r
    return best


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == "sync-time":
        now = int(time.time())
        r = talk([f"AT+SUT:{now}", "AT+GUT?"])
        print("\n".join(r) or "no reply - see README troubleshooting")
        for x in r:
            if x.startswith("AT+GUT:"):
                d = int(x.split(":")[1]) - int(time.time())
                print("watch clock offset vs this PC: %ds %s" % (d, "OK" if abs(d) < 30 else "MISMATCH"))
    elif a[0] == "wake" and len(a) == 2 and a[1] in ("on", "off"):
        cmd = "AT+FSS:19,%d" % (a[1] == "on")
        r = talk([cmd])
        print("\n".join(r) if r else "no echo - resend (link flaps); verify by raising your wrist")
    elif a[0] == "info":
        names = ["GBS", "GSV", "GPV", "GUV", "GBT", "GTZ", "GUT"]
        r = talk([f"AT+{n}?" for n in names])
        print("\n".join(r))
    elif a[0] == "raw":
        print("\n".join(talk(a[1:])))
    else: sys.exit(__doc__)


if __name__ == "__main__":
    main()
