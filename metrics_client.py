#!/usr/bin/env python3
import requests
from typing import Any, Dict, Optional, Tuple, List

BASE = "http://localhost:19999"

class NetdataError(RuntimeError):
    pass

def _get_json(url: str) -> Dict[str, Any]:
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()

def list_charts() -> Dict[str, Any]:
    return _get_json(f"{BASE}/api/v1/charts")

def find_chart_id(prefixes: List[str]) -> Optional[str]:
    """
    Find the first chart id that starts with any of the given prefixes.
    Example prefixes: ["system.cpu"], ["disk_space."], ["system.ram"]
    """
    charts = list_charts().get("charts", {})
    for cid in charts.keys():
        for p in prefixes:
            if cid.startswith(p):
                return cid
    return None

def get_chart_data(chart_id: str) -> Dict[str, Any]:
    return _get_json(f"{BASE}/api/v1/data?chart={chart_id}")

def latest_row(chart_data: Dict[str, Any]) -> Tuple[Optional[int], List[Optional[float]]]:
    """
    Returns (timestamp, values) for the latest row that has at least one non-null value.
    Netdata can return many rows with nulls when values don't change.
    """
    data = chart_data.get("data", [])
    if not data:
        return None, []

    # data rows format: [ts, v1, v2, ...]
    for row in reversed(data):
        ts = row[0]
        vals = row[1:]
        if any(v is not None for v in vals):
            # Cast numeric-ish to float where possible
            out = []
            for v in vals:
                out.append(float(v) if v is not None else None)
            return int(ts), out
    # fallback
    row = data[-1]
    return int(row[0]), [float(v) if v is not None else None for v in row[1:]]

def latest_dimension_value(chart_id: str, preferred_dim: Optional[str] = None) -> Optional[float]:
    """
    Returns a single numeric value from a chart:
    - If preferred_dim is provided and exists, return that dimension's latest value.
    - Else return the first non-null dimension from latest row.
    """
    charts = list_charts().get("charts", {})
    chart = charts.get(chart_id)
    if not chart:
        raise NetdataError(f"Chart not found: {chart_id}")

    dims = list(chart.get("dimensions", {}).keys())
    if not dims:
        raise NetdataError(f"No dimensions in chart: {chart_id}")

    data = get_chart_data(chart_id)
    _, vals = latest_row(data)
    if not vals:
        return None

    dim_to_idx = {d: i for i, d in enumerate(dims)}

    if preferred_dim and preferred_dim in dim_to_idx:
        v = vals[dim_to_idx[preferred_dim]]
        return v

    for v in vals:
        if v is not None:
            return v
    return None

def snapshot() -> Dict[str, Any]:
    """
    Produce a simple snapshot used by tuner:
    - cpu_total_pct: system.cpu 'user+system+...' total could be derived, but Netdata system.cpu is multi-dim.
      We'll compute total as sum of non-null dims for latest row (clamped 0..100).
    - ram_used_pct: system.ram is typically in MiB; we'll compute used% if possible
      BUT chart dims vary. We'll prefer common dims if present.
    - load_1m: system.load typically has dim 'load1'
    - disk_space_used_pct: find a disk_space chart and compute used% if chart already provides it, else None
    """
    charts = list_charts().get("charts", {})

    # CPU
    cpu_id = find_chart_id(["system.cpu"])
    cpu_total = None
    if cpu_id:
        cpu_data = get_chart_data(cpu_id)
        _, cpu_vals = latest_row(cpu_data)
        # Sum non-null dims (often user/system/nice/iowait/irq/softirq/steal/guest)
        s = sum(v for v in cpu_vals if v is not None)
        # Some systems report total close to 100; clamp.
        cpu_total = max(0.0, min(100.0, float(s)))

    # Load
    load_id = find_chart_id(["system.load"])
    load_1m = None
    if load_id:
        # prefer common 'load1' dimension if present
        try:
            load_1m = latest_dimension_value(load_id, preferred_dim="load1")
        except Exception:
            # fallback: first non-null
            load_1m = latest_dimension_value(load_id)

    # RAM (varies by chart; often dims include 'used'/'free' or absolute values)
    ram_id = find_chart_id(["system.ram"])
    ram_used_pct = None
    if ram_id and ram_id in charts:
        dims = charts[ram_id].get("dimensions", {})
        # Try common names
        # Depending on netdata, system.ram may have: used, free, cached, buffers
        # We'll compute used% = used / (used+free+cached+buffers) if possible.
        ram_data = get_chart_data(ram_id)
        _, vals = latest_row(ram_data)
        dim_names = list(dims.keys())
        d = {name: vals[i] if i < len(vals) else None for i, name in enumerate(dim_names)}
        candidates = ["used", "free", "cached", "buffers"]
        if all(k in d for k in ["used", "free"]) and d["used"] is not None and d["free"] is not None:
            total = d["used"] + d["free"]
            if "cached" in d and d["cached"] is not None:
                total += d["cached"]
            if "buffers" in d and d["buffers"] is not None:
                total += d["buffers"]
            if total > 0:
                ram_used_pct = (d["used"] / total) * 100.0

    # Disk space chart discovery (varies: disk_space.root, disk_space.mnt_c, disk_space._, etc.)
    disk_id = find_chart_id(["disk_space."])
    disk_used_pct = None
    if disk_id:
        # Some disk_space charts include a dimension like 'used' or 'avail' or percent.
        # We'll try common dims; else just return None and let bash handle df.
        try:
            disk_used = latest_dimension_value(disk_id, preferred_dim="used")
            disk_avail = None
            # Try to find avail in the same chart
            charts_disk = charts.get(disk_id, {})
            dim_names = list(charts_disk.get("dimensions", {}).keys())
            if "avail" in dim_names:
                disk_avail = latest_dimension_value(disk_id, preferred_dim="avail")
            if disk_used is not None and disk_avail is not None and (disk_used + disk_avail) > 0:
                disk_used_pct = (disk_used / (disk_used + disk_avail)) * 100.0
        except Exception:
            pass

    return {
        "cpu_total_pct": cpu_total,
        "load_1m": load_1m,
        "ram_used_pct": ram_used_pct,
        "disk_used_pct": disk_used_pct,
        "chart_ids": {
            "cpu": cpu_id,
            "load": load_id,
            "ram": ram_id,
            "disk_space": disk_id,
        }
    }

if __name__ == "__main__":
    snap = snapshot()
    print(snap)
