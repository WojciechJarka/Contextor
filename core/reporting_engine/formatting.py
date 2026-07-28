# -*- coding: utf-8 -*-

"""
core/reporting_engine/formatting.py

Text output classifications and functions for saving reporting
structures to disk.
"""

import os
import orjson


def _collision_severity(artifact_type: str, symbol_details: list, code_snippets: dict) -> str:
    if artifact_type == "class":
        if code_snippets:
            lengths = [len(code.splitlines()) for code in code_snippets.values()]
            if lengths:
                min_len = min(lengths)
                max_len = max(lengths)
                if min_len > 0 and max_len / min_len >= 2.0:
                    return "critical"
                if max_len - min_len > 5:
                    return "warning"
        return "info"

    if artifact_type == "function":
        if code_snippets:
            lengths = [len(code.splitlines()) for code in code_snippets.values()]
            if lengths and max(lengths) > 0:
                if min(lengths) / max(lengths) < 0.4:
                    return "warning"
        return "warning"

    if artifact_type == "variable":
        return "warning"

    return "info"


def _compute_status(cycles: list, real_collisions: list, hotspots: list | None = None) -> str:
    has_cycles = bool(cycles)
    has_collisions = bool(real_collisions)
    has_hotspots = any(
        h.get("type") in ("HUB", "HOTSPOT", "OUTBOUND_HOTSPOT")
        for h in (hotspots or [])
    )

    if has_cycles and has_collisions:
        return "CRITICAL"
    if has_cycles or has_collisions:
        return "BROKEN"
    if has_hotspots:
        return "WARNING"
    return "HEALTHY"


def save_json(report: dict, path: str, log=None, label: str = "", compact: bool = False) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if log and label:
        log(f"Serializing and saving: {label} ({path})...")

    option = orjson.OPT_NON_STR_KEYS | orjson.OPT_SORT_KEYS
    if not compact:
        option |= orjson.OPT_INDENT_2

    serialized = orjson.dumps(report, option=option)
    with open(path, "wb") as f:
        f.write(serialized)

    if log and label:
        log(f"Successfully saved: {label}")
