"""Sequential bounded runner for one registered atomic operation."""

import math
import statistics
from pathlib import Path
from time import perf_counter_ns

from contextor.core.profiling.atomic import AtomicRecorder
from contextor.core.profiling.registry import SCHEMA, get_scope, validate_scope_presets

MAX_OUTPUT_BYTES = 15 * 1024


def validate_probe_request(scope: object, presets: object, samples: object, warmup: object,
                           result_view: object) -> tuple[str, ...]:
    if not isinstance(scope, str) or get_scope(scope) is None:
        raise ValueError("Unknown profiling scope.")
    selected = validate_scope_presets(scope, presets)
    if type(samples) is not int or not 1 <= samples <= 10:
        raise ValueError("samples must be an integer from 1 to 10.")
    if type(warmup) is not int or not 0 <= warmup <= 3:
        raise ValueError("warmup must be an integer from 0 to 3.")
    if result_view not in ("summary", "spans"):
        raise ValueError("Invalid result_view.")
    return selected


def _stats(values: list[int]) -> dict[str, object]:
    ms = sorted(value / 1_000_000 for value in values)
    return {
        "count": len(ms),
        "min_ms": min(ms) if ms else None,
        "median_ms": statistics.median(ms) if ms else None,
        "max_ms": max(ms) if ms else None,
        "p95_ms": ms[math.ceil(.95 * len(ms)) - 1] if len(ms) >= 5 else None,
    }


def _safe_failure(exc: Exception) -> dict[str, str]:
    return {"category": type(exc).__name__[:80], "reason": "scope_operation_failed"}


def _consistency(scope: str, revisions: list[int]) -> dict[str, object]:
    if scope == "reports.summary":
        return {"status": "historical_unverified"}
    if scope == "snapshot.metadata":
        return {"status": "durable_metadata_only"}
    if not revisions:
        return {"status": "unverified"}
    return {"status": "revision_changed" if len(set(revisions)) > 1 else "observed_revisions_equal",
            "observed_revisions": revisions}


def _base(scope: str, selected: tuple[str, ...], samples: int, warmup: int,
          result_view: str) -> dict[str, object]:
    return {
        "schema": SCHEMA, "mode": "probe", "scope": scope,
        "selected_presets": list(selected), "samples": samples, "warmup": warmup,
        "result_view": result_view,
        "measurement": {
            "timing_unit": "ms", "clock": "perf_counter_ns",
            "absolute_wall_authoritative": False, "includes_worker_startup": False,
            "measurement_atomicity": "timing_span_only",
        },
    }


def run_probe(repo_path: str | Path, scope: str, presets: list[str], samples: int,
              warmup: int, result_view: str) -> dict[str, object]:
    selected = validate_probe_request(scope, presets, samples, warmup, result_view)
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Repository root must exist.")
    spec = get_scope(scope)
    base = _base(scope, selected, samples, warmup, result_view)
    for index in range(warmup):
        try:
            outcome = spec.run_scope(root, AtomicRecorder(scope, frozenset(), index))
        except Exception as exc:
            failure = _safe_failure(exc)
            return {**base, "status": "warmup_failed", "wall": _stats([]),
                    "presets": {name: _stats([]) for name in selected},
                    "consistency": _consistency(scope, []),
                    "outcomes": {"successful": 0, "failed": 0, "iterations": [],
                                 "warmup_failure": failure}}
        if outcome.get("status") != "ok":
            return {**base, "status": "warmup_failed", "wall": _stats([]),
                    "presets": {name: _stats([]) for name in selected},
                    "consistency": _consistency(scope, []),
                    "outcomes": {"successful": 0, "failed": 0, "iterations": [],
                                 "warmup_failure": {"category": outcome.get("status"),
                                                    "reason": outcome.get("reason")}}}

    walls: list[int] = []
    durations: dict[str, list[int]] = {name: [] for name in selected}
    span_records: list[dict[str, object]] = []
    outcomes: list[dict[str, object]] = []
    revisions: list[int] = []
    for index in range(samples):
        recorder = AtomicRecorder(scope, frozenset(selected), index)
        start = perf_counter_ns()
        try:
            outcome = spec.run_scope(root, recorder)
        except Exception as exc:
            outcome = {"status": "failed", **_safe_failure(exc)}
        elapsed = perf_counter_ns() - start
        status = outcome.get("status", "failed")
        if status == "ok":
            walls.append(elapsed)
            if type(outcome.get("observed_revision")) is int:
                revisions.append(outcome["observed_revision"])
        public_fields = ("reason", "category", "bytes_read", "json_root_type", "data_source",
                         "live_binding_verified", "observed_revision", "operation",
                         "durable_revision", "snapshot_schema_version", "identity_verified")
        outcomes.append({"iteration": index, "status": status,
                         **{key: outcome[key] for key in public_fields if key in outcome}})
        for record in recorder.records():
            if record["status"] == "ok" and status == "ok":
                durations[record["preset"]].append(record["duration_ns"])
            if result_view == "spans":
                span_records.append({"preset": record["preset"], "iteration": index,
                                     "duration_ms": record["duration_ns"] / 1_000_000,
                                     "status": record["status"]})

    successes = len(walls)
    consistency = _consistency(scope, revisions)
    result = {
        **base,
        "status": "ok" if successes == samples else "partial" if successes else "failed",
        "wall": _stats(walls),
        "presets": {name: _stats(durations[name]) for name in selected},
        "consistency": consistency,
        "outcomes": {"successful": successes, "failed": samples - successes, "iterations": outcomes},
    }
    if result_view == "spans":
        result["spans"] = span_records
    import json
    size = len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    if size > MAX_OUTPUT_BYTES:
        return {"schema": SCHEMA, "status": "confirmation_required", "mode": "probe",
                "estimated_bytes": size, "size_limit": MAX_OUTPUT_BYTES,
                "suggested_result_view": "summary", "scope": scope,
                "selected_presets": list(selected)}
    return result
