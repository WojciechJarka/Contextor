from pathlib import Path
from typing import Any


_live_engines: dict[str, Any] = {}
_live_engine_revisions: dict[str, int] = {}


def get_or_init_engine(root: Path):
    """
    Returns the live engine from RAM. If absent, HYDRATES from the .contextor cache.
    Does NOT silently trigger analyze_project.
    """
    from contextor.core.live_state import connect

    engine = _live_engines.get(str(root))
    client = connect(root)
    if client:
        remote = client.ping()
        remote_revision = int(remote.get("revision", 0))
        if remote_revision > _live_engine_revisions.get(str(root), -1):
            snapshot = client.snapshot()
            state = snapshot.get("state")
            if state is not None:
                from contextor.core.analysis.state_manager import FileStateManager
                from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
                from contextor.core.paths import repo_cache_dir
                from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

                manager = FileStateManager(str(repo_cache_dir(root)))
                engine = IncrementalAnalysisEngine(
                    state,
                    PersistentIdentityRegistry(str(root)),
                    manager,
                    str(root),
                )
                _live_engines[str(root)] = engine
                _live_engine_revisions[str(root)] = remote_revision
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
            state_mgr = FileStateManager(cache_dir)
            registry = PersistentIdentityRegistry(str(root))
            engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
            _live_engines[str(root)] = engine
            if metadata and metadata.revision is not None:
                _live_engine_revisions[str(root)] = int(metadata.revision)
        else:
            _live_engines.pop(str(root), None)
            _live_engine_revisions.pop(str(root), None)
    return engine
