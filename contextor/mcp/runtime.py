from pathlib import Path
from typing import Any


_live_engines: dict[str, Any] = {}
_live_engine_revisions: dict[str, int] = {}
_live_engine_provenance: dict[str, str] = {}
_live_sessions: dict[str, str] = {}
_live_journal_revisions: dict[str, int] = {}


def publish_live_status(root: Path, message: str) -> None:
    try:
        from contextor.core.live_state import connect

        client = connect(root)
        if client is not None:
            client.status(message, origin="mcp")
    except (OSError, EOFError, RuntimeError):
        pass


def get_or_init_engine(root: Path):
    """
    Returns the live engine from RAM. If absent, HYDRATES from the .contextor cache.
    Does NOT silently trigger analyze_project.
    """
    from contextor.core.live_state import connect

    root_key = str(root)
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
            _live_engines[str(root)] = engine
            _live_engine_provenance[str(root)] = "snapshot"
            if rev is not None:
                _live_engine_revisions[str(root)] = rev
            else:
                _live_engine_revisions.pop(str(root), None)
        else:
            _live_engines.pop(str(root), None)
            _live_engine_revisions.pop(str(root), None)
            _live_engine_provenance.pop(str(root), None)
            _live_sessions.pop(str(root), None)
            _live_journal_revisions.pop(str(root), None)
    return engine
