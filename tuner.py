#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from metrics_client import snapshot

# Default policy (you can tune these)
POLICY = {
    "max_cpu_total_pct": 70.0,   # if CPU busy > 70%, delay
    "max_load_1m": 2.0,          # if load1 > 2.0, delay (maps your bash MAX_LOAD idea :contentReference[oaicite:2]{index=2})
    "max_ram_used_pct": 85.0,    # if RAM used > 85%, delay
    # disk_used_pct may be None from netdata; disk check remains in bash via df (safe fallback)
}

def decide(snap: dict) -> dict:
    reasons = []
    safe = True

    cpu = snap.get("cpu_total_pct")
    load1 = snap.get("load_1m")
    ram = snap.get("ram_used_pct")

    if cpu is not None and cpu > POLICY["max_cpu_total_pct"]:
        safe = False
        reasons.append(f"CPU busy {cpu:.1f}% > {POLICY['max_cpu_total_pct']}%")

    if load1 is not None and load1 > POLICY["max_load_1m"]:
        safe = False
        reasons.append(f"Load1 {load1:.2f} > {POLICY['max_load_1m']}")

    if ram is not None and ram > POLICY["max_ram_used_pct"]:
        safe = False
        reasons.append(f"RAM used {ram:.1f}% > {POLICY['max_ram_used_pct']}%")

    if safe and not reasons:
        reasons.append("All monitored signals within safe thresholds")

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "safe": safe,
        "reasons": reasons,
        "snapshot": snap,
        "policy": POLICY,
    }

def main():
    snap = snapshot()
    result = decide(snap)
    print(json.dumps(result, indent=2))

    # exit code used by wrapper
    if result["safe"]:
        return 0
    return 2

if __name__ == "__main__":
    sys.exit(main())
