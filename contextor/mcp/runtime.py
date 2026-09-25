from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any, Iterator

from contextor.core.lineage_query.live_query import (
    LiveSymbolLineageQueryResult,
)


_live_engines: dict[str, Any] = {}
_live_engine_revisions: dict[str, int] = {}
_live_engine_provenance: dict[str, str] = {}
_live_sessions: dict[str, str] = {}
_live_journal_revisions: dict[str, int] = {}
_engine_cache_locks_guard = threading.Lock()
_engine_cache_locks: dict[str, Any] = {}


@dataclass(frozen=True)
class LiveSymbolLineageTransportResult:
    status: str
    revision: int | None = None
    result: LiveSymbolLineageQueryResult | None = None
    error: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class LiveDiagnosticsSummaryTransportResult:
    status: str
    revision: int | None = None
    summary: dict[str, Any] | None = None
    error: str | None = None
    detail: str | None = None


def _bounded_live_query_detail(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value[:500]


def _valid_live_diagnostics_summary(
    value: object,
) -> bool:
    if not isinstance(value, Mapping):
        return False

    availability = value.get(
        "availability"
    )

    if not isinstance(
        availability,
        Mapping,
    ):
        return False

    for family in (
        "syntax_errors",
        "name_collisions",
        "cycles",
    ):
        if not isinstance(
            value.get(family),
            Mapping,
        ):
            return False

        if family not in availability:
            return False

    return (
        type(
            value.get(
                "attention_required"
            )
        )
        is bool
    )


def query_live_diagnostics_summary_narrow(
    root: Path,
) -> LiveDiagnosticsSummaryTransportResult:
    if not isinstance(root, Path):
        raise TypeError(
            "root must be a Path."
        )

    from contextor.core.live_state import connect

    try:
        client = connect(root)
    except (
        OSError,
        EOFError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
    ) as exc:
        return LiveDiagnosticsSummaryTransportResult(
            status="error",
            error="canonical_live_transport_error",
            detail=_bounded_live_query_detail(
                str(exc)
            ),
        )

    if client is None:
        return LiveDiagnosticsSummaryTransportResult(
            status="unavailable",
            error="canonical_live_unavailable",
        )

    try:
        response = client.canonical_query(
            "diagnostics_summary",
            payload={},
        )
    except (
        OSError,
        EOFError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
    ) as exc:
        return LiveDiagnosticsSummaryTransportResult(
            status="error",
            error="canonical_query_transport_error",
            detail=_bounded_live_query_detail(
                str(exc)
            ),
        )

    if not isinstance(
        response,
        Mapping,
    ):
        return LiveDiagnosticsSummaryTransportResult(
            status="error",
            error="canonical_query_response_invalid",
        )

    if response.get("status") != "ok":
        remote_error = response.get(
            "error"
        )

        return LiveDiagnosticsSummaryTransportResult(
            status="error",
            error=(
                remote_error
                if (
                    isinstance(
                        remote_error,
                        str,
                    )
                    and remote_error
                )
                else "canonical_query_failed"
            ),
            detail=_bounded_live_query_detail(
                response.get("detail")
            ),
        )

    revision = response.get(
        "revision"
    )

    if (
        isinstance(revision, bool)
        or not isinstance(
            revision,
            int,
        )
        or revision < 0
    ):
        return LiveDiagnosticsSummaryTransportResult(
            status="error",
            error="canonical_query_response_invalid",
        )

    result = response.get(
        "result"
    )

    if not _valid_live_diagnostics_summary(
        result
    ):
        return LiveDiagnosticsSummaryTransportResult(
            status="error",
            revision=revision,
            error="canonical_query_response_invalid",
        )

    return LiveDiagnosticsSummaryTransportResult(
        status="ok",
        revision=revision,
        summary=dict(result),
    )


def query_live_symbol_lineage_narrow(
    root: Path,
    *,
    query: str,
    sections: tuple[str, ...],
) -> LiveSymbolLineageTransportResult:
    if not isinstance(root, Path):
        raise TypeError("root must be a Path.")
    if not isinstance(query, str):
        raise TypeError("query must be a string.")
    if not isinstance(sections, tuple):
        raise TypeError("sections must be a tuple of section names.")
    if any(not isinstance(section, str) or not section for section in sections):
        raise ValueError("sections must contain non-empty strings.")

    from contextor.core.live_state import connect
    try:
        client = connect(root)
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
        return LiveSymbolLineageTransportResult(
            status="error", error="canonical_live_transport_error",
            detail=_bounded_live_query_detail(str(exc)),
        )
    if client is None:
        return LiveSymbolLineageTransportResult(
            status="unavailable", error="canonical_live_unavailable"
        )
    try:
        response = client.canonical_query(
            "symbol_lineage",
            payload={"query": query, "sections": list(sections)},
        )
    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError) as exc:
        return LiveSymbolLineageTransportResult(
            status="error", error="canonical_query_transport_error",
            detail=_bounded_live_query_detail(str(exc)),
        )
    if not isinstance(response, Mapping):
        return LiveSymbolLineageTransportResult(
            status="error", error="canonical_query_response_invalid"
        )
    if response.get("status") != "ok":
        remote_error = response.get("error")
        return LiveSymbolLineageTransportResult(
            status="error",
            error=remote_error if isinstance(remote_error, str) and remote_error else "canonical_query_failed",
            detail=_bounded_live_query_detail(response.get("detail")),
        )
    revision = response.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        return LiveSymbolLineageTransportResult(status="error", error="canonical_query_response_invalid")
    result = response.get("result")
    if not isinstance(result, LiveSymbolLineageQueryResult):
        return LiveSymbolLineageTransportResult(status="error", revision=revision, error="canonical_query_response_invalid")
    if result.state_freshness.get("canonical_revision") != revision:
        return LiveSymbolLineageTransportResult(status="error", revision=revision, error="canonical_query_revision_mismatch")
    if result.selected is not None and result.selected.facts.metadata.revision != revision:
        return LiveSymbolLineageTransportResult(status="error", revision=revision, error="canonical_query_revision_mismatch")
    return LiveSymbolLineageTransportResult(status="ok", revision=revision, result=result)


def publish_live_status(root: Path, message: str) -> None:
    try:
        from contextor.core.live_state import connect

        client = connect(root)
        if client is not None:
            client.status(message, origin="mcp")
    except (OSError, EOFError, RuntimeError):
        pass


def _engine_cache_key(root: Path | str) -> str:
    return str(Path(root).expanduser().resolve())


@contextmanager
def _engine_cache_transaction(root: Path | str) -> Iterator[str]:
    root_key = _engine_cache_key(root)
    with _engine_cache_locks_guard:
        lock = _engine_cache_locks.get(root_key)
        if lock is None:
            lock = threading.RLock()
            _engine_cache_locks[root_key] = lock
    with lock:
        yield root_key


def _cached_engine(root: Path | str):
    with _engine_cache_transaction(root) as root_key:
        return _live_engines.get(root_key)


def _get_or_init_engine_snapshot(root: Path | str):
    root = Path(root).expanduser().resolve()
    with _engine_cache_transaction(root) as root_key:
        engine = get_or_init_engine(root)
        revision = _live_engine_revisions.get(root_key)
        return engine, revision


def get_or_init_engine(root: Path):
    """
    Returns the live engine from RAM. If absent, HYDRATES from the .contextor cache.
    Does NOT silently trigger analyze_project.
    """
    root = Path(root).expanduser().resolve()
    with _engine_cache_transaction(root) as root_key:
        from contextor.core.live_state import connect

        engine = _live_engines.get(root_key)
        client = connect(root)
        if client:
            session_id = f"{client.endpoint.host}:{client.endpoint.port}:{client.endpoint.authkey_hex}"
            cached_session_id = _live_sessions.get(root_key)
            cached_journal_rev = _live_journal_revisions.get(root_key)

            remote = client.ping()
            journal_revision = int(remote.get("revision", 0))

            needs_refresh = (
                engine is None
                or session_id != cached_session_id
                or journal_revision != cached_journal_rev
            )

            if needs_refresh:
                snapshot = client.snapshot()
                state = snapshot.get("state")
                if state is not None:
                    from contextor.core.analysis.state_manager import FileStateManager
                    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
                    from contextor.core.live_state import read_metadata
                    from contextor.core.paths import repo_cache_dir
                    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

                    setattr(state, "provenance", "live")
                    pub_rev = getattr(state, "revision", None)
                    sid = getattr(state, "state_id", None)
                    if pub_rev is None or not sid:
                        cache_meta = read_metadata(repo_cache_dir(root))
                        if pub_rev is None and cache_meta and cache_meta.revision is not None:
                            pub_rev = int(cache_meta.revision)
                            setattr(state, "revision", pub_rev)
                        if not sid and cache_meta and cache_meta.state_id:
                            sid = cache_meta.state_id
                            setattr(state, "state_id", sid)

                    manager = FileStateManager(str(repo_cache_dir(root)))
                    engine = IncrementalAnalysisEngine(
                        state,
                        PersistentIdentityRegistry(str(root)),
                        manager,
                        str(root),
                    )
                    engine.provenance = "live"
                    engine.revision = pub_rev
                    _live_engines[root_key] = engine
                    _live_sessions[root_key] = session_id
                    _live_journal_revisions[root_key] = journal_revision
                    if pub_rev is not None:
                        _live_engine_revisions[root_key] = pub_rev
                    else:
                        _live_engine_revisions.pop(root_key, None)
                    _live_engine_provenance[root_key] = "live"
        else:
            _live_sessions.pop(root_key, None)
            _live_journal_revisions.pop(root_key, None)
        if not engine:
            from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
            from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
            from contextor.core.live_state import migrate_legacy_snapshot, read_metadata
            from contextor.core.repository_identity import read_repository_identity
            from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

            identity = read_repository_identity(root)
            if identity is None:
                return None
            cache_dir = str(migrate_legacy_snapshot(root))
            metadata = read_metadata(cache_dir)
            state = load_engine_state(
                cache_dir,
                metadata.state_id if metadata else "",
                expected_repo_id=identity.repo_id,
                expected_root_path=identity.root_path,
            )
            if state:
                rev = int(metadata.revision) if metadata and metadata.revision is not None else None
                sid = metadata.state_id if metadata else ""
                setattr(state, "provenance", "snapshot")
                setattr(state, "revision", rev)
                setattr(state, "state_id", sid)
                state_mgr = FileStateManager(cache_dir)
                registry = PersistentIdentityRegistry(str(root))
                engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
                engine.provenance = "snapshot"
                engine.revision = rev
                _live_engines[root_key] = engine
                _live_engine_provenance[root_key] = "snapshot"
                if rev is not None:
                    _live_engine_revisions[root_key] = rev
                else:
                    _live_engine_revisions.pop(root_key, None)
            else:
                _live_engines.pop(root_key, None)
                _live_engine_revisions.pop(root_key, None)
                _live_engine_provenance.pop(root_key, None)
                _live_sessions.pop(root_key, None)
                _live_journal_revisions.pop(root_key, None)
        return engine
