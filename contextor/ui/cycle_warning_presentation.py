"""Fail-closed Desktop presentation of installed cycle warnings.

This module only filters presentation errors, never canonical cycles,
validation evidence, LIVE state, receipts or structural diagnostics.
A published generation with matching owner identity is mandatory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from contextor.core.cycle_semantics.cycle_warning_projection import (
    InstalledCycleWarningProjection,
)
from contextor.core.cycle_semantics.cycle_warning_transitions import (
    _validated_states,
)
from contextor.core.cycle_semantics.live_cycle_warning_query import (
    _AUTHORITY as _PROJECTION_AUTHORITY,
    _BINDING as _PROJECTION_BINDING,
)
from contextor.core.domain.validation import ValidationError
from contextor.core.repository_identity import read_repository_identity


_FIELDS = frozenset({
    "status",
    "binding_state",
    "revision",
    "state_id",
    "repo_id",
    "root_path",
    "service_instance_id",
    "process_start_identity",
    "activity_epoch",
    "graph_sha256",
    "structural_paths",
    "model_pass_paths",
    "active_warning_paths",
    "structural_count",
    "model_pass_count",
    "active_warning_count",
    "authority",
})


def _accepted_paths(
    result: Any,
    repo_path: str,
    report: Any,
) -> frozenset[tuple[str, ...]] | None:
    """Validate the published generation before accepting any cycle path."""
    if type(report) is not dict or set(report) != _FIELDS:
        return None

    if getattr(result, "live_publish_status", None) != "success":
        return None

    revision = getattr(result, "live_publish_revision", None)
    expected_revision = getattr(
        result, "live_publish_expected_revision", None
    )
    expected_state_id = getattr(
        result, "live_publish_expected_state_id", None
    )
    expected_service = getattr(
        result, "live_publish_service_instance_id", None
    )
    expected_process = getattr(
        result, "live_publish_process_start_identity", None
    )

    if (
        type(revision) is not int
        or revision < 1
        or type(expected_revision) is not int
        or revision != expected_revision
        or type(expected_state_id) is not str
        or not expected_state_id
        or type(expected_service) is not str
        or not expected_service
        or type(expected_process) is not str
        or not expected_process
    ):
        return None

    if (
        report["status"] != "ok"
        or report["binding_state"] != _PROJECTION_BINDING
        or report["authority"] != _PROJECTION_AUTHORITY
        or type(report["revision"]) is not int
        or report["revision"] != revision
        or report["state_id"] != expected_state_id
        or report["service_instance_id"] != expected_service
        or report["process_start_identity"] != expected_process
        or type(report["activity_epoch"]) is not str
        or not report["activity_epoch"]
    ):
        return None

    identity = read_repository_identity(repo_path)
    if identity is None:
        return None

    if (
        report["repo_id"] != identity.repo_id
        or Path(report["root_path"]).resolve()
        != Path(identity.root_path).resolve()
        or Path(repo_path).resolve()
        != Path(identity.root_path).resolve()
    ):
        return None

    digest = report["graph_sha256"]
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        return None

    for paths_field, count_field in (
        ("structural_paths", "structural_count"),
        ("model_pass_paths", "model_pass_count"),
        ("active_warning_paths", "active_warning_count"),
    ):
        paths = report[paths_field]
        count = report[count_field]
        if (
            type(paths) is not tuple
            or type(count) is not int
            or count != len(paths)
        ):
            return None

    projection = InstalledCycleWarningProjection(
        status="FRESH",
        reason=None,
        revision=revision,
        structural_paths=report["structural_paths"],
        model_pass_paths=report["model_pass_paths"],
        active_warning_paths=report["active_warning_paths"],
    )

    if _validated_states(projection) is None:
        return None

    return frozenset(report["model_pass_paths"])


def filter_installed_desktop_cycle_errors(
    errors: Any,
    analysis_result: Any,
    repo_path: str,
) -> Any:
    """Filter only proven MODEL_PASS cycle errors from Desktop messages.

    The caller runs this after full analysis, on the worker thread.
    Any missing or mismatched evidence preserves the original errors.
    """
    if type(errors) is not list or not errors:
        return errors

    if not any(
        type(error) is ValidationError
        and error.kind == "ArchitectureCycle"
        for error in errors
    ):
        return errors

    if getattr(analysis_result, "live_publish_status", None) != "success":
        return errors

    try:
        from contextor.core.live_state import connect

        client = connect(Path(repo_path))
        if client is None:
            return errors

        report = client.request(
            "get_installed_cycle_warning_projection",
            timeout=2.0,
        )

        accepted = _accepted_paths(
            analysis_result,
            repo_path,
            report,
        )

        if accepted is None or not accepted:
            return errors

        filtered = []
        for error in errors:
            if (
                type(error) is ValidationError
                and error.kind == "ArchitectureCycle"
                and type(error.nodes) in (list, tuple)
                and all(
                    type(node) is str and node
                    for node in error.nodes
                )
            ):
                path = tuple(error.nodes)
                expected_message = (
                    "Cyclic dependency detected in architecture: "
                    + " -> ".join(path)
                )
                if (
                    path in accepted
                    and error.message == expected_message
                ):
                    continue

            filtered.append(error)

        return filtered

    except Exception:
        # A presentation query must not hide diagnostics or fail analysis.
        return errors
