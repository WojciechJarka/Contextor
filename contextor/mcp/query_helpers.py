import difflib
from pathlib import Path
from typing import Any

from contextor.core.analysis.state_manager import (
    artifact_consumption_is_fresh,
    canonical_artifact_consumption_targets,
    module_current_truth,
)

FUZZY_MIN_SCORE: float = 0.75
FUZZY_MAX_CANDIDATES: int = 5


def bounded_items(items: list, limit: int | None) -> tuple[list, int, bool]:
    total = len(items)
    if limit is None:
        return items, total, False
    safe_limit = max(0, int(limit))
    selected = items[:safe_limit]
    return selected, total, total > len(selected)


def read_registries(root: Path) -> tuple[dict, dict, dict, dict]:
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    registry = PersistentIdentityRegistry(str(root))
    with registry.transaction():
        mod_reg = registry._state.get("module_registry", {})
        art_reg = registry._state.get("artifact_registry", {})
    return (
        mod_reg.get("path_to_id", {}),
        mod_reg.get("id_to_path", {}),
        art_reg.get("path_to_id", {}),
        art_reg.get("id_to_path", {}),
    )


def canonical_symbol_consumers(
    state, module_name: str, symbol: str
) -> list[str]:
    if not artifact_consumption_is_fresh(state):
        raise ValueError("Canonical artifact consumption is unavailable or stale.")
    target = f"{module_name}::{symbol}"
    consumption = getattr(state, "artifact_consumption", {}) or {}
    entry = consumption.get(target, {}) if isinstance(consumption, dict) else {}
    consumers = entry.get("consumers", []) if isinstance(entry, dict) else []
    return sorted({str(item) for item in consumers})


def module_truth_unavailable(state, module_name: str) -> dict | None:
    truth = module_current_truth(state, module_name)
    if truth["available"]:
        return None
    return {
        "status": "stale",
        "available": False,
        "module": module_name,
        **{key: value for key, value in truth.items() if key != "available"},
    }


def canonical_symbol_catalog(module_data: dict) -> dict[str, str]:
    targets = canonical_artifact_consumption_targets({"module": module_data})
    result = {target.split("::", 1)[1]: "unknown" for target in targets}
    symbols = module_data.get("symbols", {}) or {}
    for category, kind in (
        ("classes", "class"),
        ("functions", "function"),
        ("methods", "method"),
        ("globals", "global"),
    ):
        raw_names = symbols.get(category, []) or []
        names = raw_names.keys() if isinstance(raw_names, dict) else raw_names
        for name in names:
            if str(name) in result:
                result[str(name)] = kind
    return result


def is_module_id(query: str) -> bool:
    raw = query.strip()
    parts = raw.split("/")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()


def is_artifact_id(query: str) -> bool:
    raw = query.strip()
    if not (raw.startswith(("A", "a")) and "/" in raw):
        return False
    parts = raw[1:].split("/")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()


def resolve_module_identity(
    query: str,
    mod_path_to_id: dict[str, str],
    mod_id_to_path: dict[str, str],
) -> dict:
    raw = query.strip()
    if not raw:
        return {
            "status": "not_found",
            "query": raw,
            "similar_candidates": [],
        }

    # 1. Module ID lookup
    if is_module_id(raw):
        exact_name = mod_id_to_path.get(raw)
        if exact_name:
            return {
                "status": "resolved",
                "resolution": "exact_id",
                "module": exact_name,
                "module_id": raw,
                "similar_candidates": [],
            }
        return {
            "status": "not_found",
            "query": raw,
            "query_kind": "module_id",
            "similar_candidates": [],
        }

    # 2. Exact canonical module name
    if raw in mod_path_to_id:
        return {
            "status": "resolved",
            "resolution": "exact_name",
            "module": raw,
            "module_id": mod_path_to_id[raw],
            "similar_candidates": [],
        }

    # 3. Fuzzy textual module suggestions
    q_cf = raw.casefold()
    scored = []
    for name in mod_path_to_id:
        raw_score = difflib.SequenceMatcher(None, q_cf, name.casefold()).ratio()
        if raw_score >= FUZZY_MIN_SCORE:
            scored.append((-raw_score, name, mod_path_to_id[name], raw_score))

    scored.sort()
    candidates = [
        {
            "module": name,
            "module_id": active_id,
            "score": round(score, 4),
        }
        for _, name, active_id, score in scored[:FUZZY_MAX_CANDIDATES]
    ]

    return {
        "status": "not_found",
        "query": raw,
        "similar_candidates": candidates,
    }


def resolve_artifact_identity(
    query: str,
    art_path_to_id: dict[str, str],
    art_id_to_path: dict[str, str],
) -> dict:
    raw = query.strip()
    if not raw:
        return {
            "status": "not_found",
            "query": raw,
            "similar_candidates": [],
        }

    # 1. Artifact ID lookup
    if is_artifact_id(raw):
        normalized_id = raw[0].upper() + raw[1:]
        exact_identity = art_id_to_path.get(normalized_id)
        if exact_identity:
            return {
                "status": "resolved",
                "resolution": "exact_id",
                "artifact": exact_identity,
                "artifact_id": normalized_id,
                "similar_candidates": [],
            }
        return {
            "status": "not_found",
            "query": raw,
            "query_kind": "artifact_id",
            "similar_candidates": [],
        }

    # 2. Exact canonical artifact identity
    if raw in art_path_to_id:
        return {
            "status": "resolved",
            "resolution": "exact_identity",
            "artifact": raw,
            "artifact_id": art_path_to_id[raw],
            "similar_candidates": [],
        }

    # 3. Exact leaf match
    exact_leaf_matches = []
    for full_name, art_id in art_path_to_id.items():
        leaf = full_name.split("::", 1)[-1] if "::" in full_name else full_name
        if leaf == raw:
            exact_leaf_matches.append((full_name, art_id))

    if len(exact_leaf_matches) == 1:
        full_name, art_id = exact_leaf_matches[0]
        return {
            "status": "resolved",
            "resolution": "exact_leaf",
            "artifact": full_name,
            "artifact_id": art_id,
            "similar_candidates": [],
        }
    elif len(exact_leaf_matches) > 1:
        exact_leaf_matches.sort(key=lambda item: item[0])
        return {
            "status": "ambiguous",
            "resolution": "exact_leaf",
            "query": raw,
            "candidates": [
                {
                    "artifact": full_name,
                    "artifact_id": art_id,
                }
                for full_name, art_id in exact_leaf_matches
            ],
        }

    # 4. Fuzzy suggestions
    q_cf = raw.casefold()
    scored = []
    for full_name, art_id in art_path_to_id.items():
        leaf = full_name.split("::", 1)[-1] if "::" in full_name else full_name
        full_score = difflib.SequenceMatcher(None, q_cf, full_name.casefold()).ratio()
        leaf_score = difflib.SequenceMatcher(None, q_cf, leaf.casefold()).ratio()
        raw_score = max(full_score, leaf_score)
        if raw_score >= FUZZY_MIN_SCORE:
            scored.append((-raw_score, full_name, art_id, raw_score))

    scored.sort()
    candidates = [
        {
            "artifact": full_name,
            "artifact_id": art_id,
            "score": round(score, 4),
        }
        for _, full_name, art_id, score in scored[:FUZZY_MAX_CANDIDATES]
    ]

    return {
        "status": "not_found",
        "query": raw,
        "similar_candidates": candidates,
    }


def build_state_freshness(
    root: Path,
    state: Any,
    target_module: str | None = None,
    target_file: Path | str | None = None,
    engine: Any = None,
) -> dict:
    """Workspace↔canonical freshness envelope. O(1) fingerprint check — no repo scan, no AST parse."""
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager, module_current_truth
    from contextor.mcp import runtime as mcp_runtime
    from contextor.mcp import analysis_jobs

    root_path = Path(root).expanduser().resolve()
    repo_key = str(root_path)

    # 1. Canonical Revision + Provenance — strictly bound to the answered state / engine
    canonical_revision = None
    if state is not None and getattr(state, "revision", None) is not None:
        canonical_revision = getattr(state, "revision")
    elif engine is not None and getattr(engine, "revision", None) is not None:
        canonical_revision = getattr(engine, "revision")
    else:
        canonical_revision = mcp_runtime._live_engine_revisions.get(repo_key)

    if canonical_revision is not None:
        try:
            canonical_revision = int(canonical_revision)
        except (ValueError, TypeError):
            canonical_revision = None

    provenance = None
    if state is not None and getattr(state, "provenance", None) is not None:
        provenance = getattr(state, "provenance")
    elif engine is not None and getattr(engine, "provenance", None) is not None:
        provenance = getattr(engine, "provenance")
    else:
        provenance = mcp_runtime._live_engine_provenance.get(repo_key, "snapshot")

    if not provenance:
        provenance = "snapshot"

    # 2. Canonical State Internal Health
    resync_required = getattr(state, "resync_required", False)
    if resync_required:
        canonical_state = "stale"
    elif target_module:
        truth = module_current_truth(state, target_module)
        canonical_state = truth.get("state", "fresh")
    else:
        canonical_state = "fresh"

    # 3. Positive Generation Coherence Proof (Blocker 1 - Fail Closed)
    state_mgr = getattr(engine, "state_manager", None)
    if state_mgr is None:
        try:
            cache_dir = repo_cache_dir(root_path)
            state_mgr = FileStateManager(str(cache_dir))
        except Exception:
            state_mgr = None

    canonical_state_id = getattr(state, "state_id", None) if state is not None else None
    filestate_state_id = getattr(state_mgr, "state_id", None) if state_mgr is not None else None
    canonical_rev = getattr(state, "revision", None) if state is not None else None
    if canonical_rev is None and engine is not None:
        canonical_rev = getattr(engine, "revision", None)
    filestate_rev = getattr(state_mgr, "revision", None) if state_mgr is not None else None

    explicit_disk_mismatch = is_explicit_generation_mismatch(root_path, state, engine=engine)

    generation_coherent = bool(
        not explicit_disk_mismatch
        and canonical_state_id
        and filestate_state_id
        and str(canonical_state_id).strip() != ""
        and str(filestate_state_id).strip() != ""
        and canonical_state_id == filestate_state_id
        and canonical_rev is not None
        and filestate_rev is not None
        and int(canonical_rev) == int(filestate_rev)
    )

    # 4. Workspace Sync — exact content fingerprint when available
    resolved_file: Path | None = None
    if target_file is not None:
        cand = Path(target_file)
        resolved_file = cand if cand.is_absolute() else (root_path / cand).resolve()
    elif target_module is not None:
        mod_obj = getattr(state, "modules", {}).get(target_module)
        if mod_obj and getattr(mod_obj, "path", None):
            cand = Path(mod_obj.path)
            resolved_file = cand if cand.is_absolute() else (root_path / cand).resolve()

    workspace_sync = "unverified"
    if resolved_file is not None and generation_coherent:
        file_path_str = str(resolved_file)
        tracked = None
        if state_mgr is not None:
            tracked = state_mgr._state.get(file_path_str)
            if not tracked:
                try:
                    rel = str(resolved_file.relative_to(root_path))
                    tracked = state_mgr._state.get(rel)
                except ValueError:
                    tracked = None

        if tracked is not None:
            if not resolved_file.is_file():
                workspace_sync = "out_of_sync"
            else:
                try:
                    stat = resolved_file.stat()
                    mtime_match = stat.st_mtime_ns == tracked.mtime_ns
                    size_match = stat.st_size == tracked.size

                    if tracked.sha256:
                        # Exact target-local content verification (QUERY_REPO_SCAN=0, QUERY_AST_PARSE=0).
                        import hashlib
                        try:
                            with open(resolved_file, "rb") as fh:
                                current_sha = hashlib.sha256(fh.read()).hexdigest()
                            if current_sha == tracked.sha256:
                                workspace_sync = "verified"
                            else:
                                workspace_sync = "out_of_sync"
                        except OSError:
                            workspace_sync = "unverified"
                    else:
                        # No stored sha256 — metadata only, cannot guarantee content equality.
                        if mtime_match and size_match:
                            workspace_sync = "metadata_match"
                        else:
                            workspace_sync = "out_of_sync"
                except OSError:
                    workspace_sync = "unverified"
        else:
            workspace_sync = "unverified"
    elif resolved_file is not None and not generation_coherent:
        # Generation mismatch between FileState and canonical snapshot -> fail closed as unverified
        workspace_sync = "unverified"

    # 5. Families
    families = {
        "module": module_current_truth(state, target_module)["state"] if target_module else "fresh",
        "graph": "fresh" if getattr(state, "dependency_graph", None) is not None else "unavailable",
        "topology": getattr(state, "topology_metrics_state", "deferred"),
        "artifact_consumption": getattr(state, "artifact_consumption_state", "deferred"),
        "cycles": getattr(state, "cycles_state", "deferred"),
        "collisions": getattr(state, "collisions_state", "deferred"),
    }

    # 6. Advisory Warning
    advisory_warning: str | None = None
    if not generation_coherent:
        advisory_warning = (
            "Generation proof incomplete or mismatched: FileState fingerprint "
            "cannot be proven to belong to the answered canonical generation."
        )
    elif workspace_sync in {"out_of_sync", "metadata_match"}:
        if workspace_sync == "out_of_sync":
            advisory_warning = "Target file on disk has been modified since canonical state revision was generated."
        else:
            advisory_warning = (
                "Canonical state fingerprint (sha256) is absent; "
                "metadata (mtime+size) matches but content equality cannot be guaranteed."
            )
    else:
        latest_job = analysis_jobs._latest_analysis_job(root_path)
        if latest_job and latest_job.get("status") in {"interrupted", "failed"}:
            if latest_job.get("live_publish_status") != "success":
                rev_str = f"revision {canonical_revision}" if canonical_revision is not None else "an earlier snapshot"
                advisory_warning = f"The last analysis job was {latest_job.get('status')}. Canonical state reflects {rev_str}."

    return {
        "canonical_state": canonical_state,
        "workspace_sync": workspace_sync,
        "canonical_revision": canonical_revision,
        "provenance": provenance,
        "families": families,
        "advisory_warning": advisory_warning,
    }


def is_explicit_generation_mismatch(
    root: str | Path,
    state: Any = None,
    *,
    engine: Any = None,
) -> bool:
    """Return True if both canonical state and FileState carry generation metadata that explicitly mismatch."""
    from contextor.core.paths import repo_cache_dir
    from contextor.core.analysis.state_manager import FileStateManager

    root_path = Path(root).expanduser().resolve()
    disk_mgr = None
    try:
        cache_dir = repo_cache_dir(root_path)
        disk_mgr = FileStateManager(str(cache_dir))
    except Exception:
        disk_mgr = None

    state_mgr = getattr(engine, "state_manager", None) or disk_mgr

    canonical_state_id = getattr(state, "state_id", None) if state is not None else None
    canonical_rev = getattr(state, "revision", None) if state is not None else None
    if canonical_rev is None and engine is not None:
        canonical_rev = getattr(engine, "revision", None)

    # A referenced generation is authoritative.  FileStateManager intentionally
    # clears malformed metadata, so inspect that generation directly before its
    # fail-closed normalization can hide an explicit mismatch from source tools.
    try:
        from contextor.core.live_state.store import read_metadata
        import json

        metadata = read_metadata(repo_cache_dir(root_path))
        referenced = getattr(metadata, "file_state_file", "") if metadata else ""
        if referenced:
            payload = json.loads((repo_cache_dir(root_path) / referenced).read_text(encoding="utf-8"))
            raw_meta = payload.get("_meta") if isinstance(payload, dict) else None
            raw_state_id = raw_meta.get("state_id") if isinstance(raw_meta, dict) else None
            raw_revision = raw_meta.get("revision") if isinstance(raw_meta, dict) else None
            if (
                not raw_state_id
                or raw_revision is None
                or (canonical_state_id and str(raw_state_id) != str(canonical_state_id))
                or (canonical_rev is not None and int(raw_revision) != int(canonical_rev))
            ):
                return True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return True

    managers_to_check = []
    if disk_mgr is not None:
        managers_to_check.append(disk_mgr)
    if state_mgr is not None and state_mgr is not disk_mgr:
        managers_to_check.append(state_mgr)

    for mgr in managers_to_check:
        filestate_state_id = getattr(mgr, "state_id", None)
        filestate_rev = getattr(mgr, "revision", None)
        state_id_mismatch = bool(
            canonical_state_id
            and filestate_state_id
            and str(canonical_state_id).strip() != ""
            and str(filestate_state_id).strip() != ""
            and str(canonical_state_id).strip() != str(filestate_state_id).strip()
        )
        rev_mismatch = bool(
            canonical_rev is not None
            and filestate_rev is not None
            and int(canonical_rev) != int(filestate_rev)
        )
        if state_id_mismatch or rev_mismatch:
            return True
    return False

