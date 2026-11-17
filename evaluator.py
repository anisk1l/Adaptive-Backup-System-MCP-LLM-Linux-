#!/usr/bin/env python3
import subprocess
import time
import json
from datetime import datetime

RUNS = 5
SLEEP_SEC = 10

def run_cmd(cmd):
    start = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    end = time.time()
    return {
        "cmd": cmd,
        "returncode": p.returncode,
        "duration_sec": round(end - start, 3),
        "stdout_tail": p.stdout[-500:],
        "stderr_tail": p.stderr[-500:],
        "ts": datetime.now().isoformat(timespec="seconds"),
    }

def main():
    results = {"static": [], "adaptive": []}

    for i in range(RUNS):
        results["static"].append(run_cmd(["bash", "./easy_backup.sh"]))
        time.sleep(SLEEP_SEC)

    for i in range(RUNS):
        results["adaptive"].append(run_cmd(["bash", "./run_adaptive.sh"]))
        time.sleep(SLEEP_SEC)

    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Wrote evaluation_results.json")
    # Quick summary
    def summarize(items):
        ok = sum(1 for x in items if x["returncode"] == 0)
        return ok, len(items)

    s_ok, s_n = summarize(results["static"])
    a_ok, a_n = summarize(results["adaptive"])
    print(f"Static success:   {s_ok}/{s_n}")
    print(f"Adaptive success: {a_ok}/{a_n}")

if __name__ == "__main__":
    main()
