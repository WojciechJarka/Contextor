import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class FileState:
    """Minimal state for tracking file changes."""
    mtime_ns: int
    size: int
    sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"mtime_ns": self.mtime_ns, "size": self.size, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileState":
        return cls(mtime_ns=data.get("mtime_ns", 0), size=data.get("size", 0), sha256=data.get("sha256", ""))


@dataclass
class FileDelta:
    """Represents the difference between the old module state and the newly parsed AST."""
    module_path: str
    is_new: bool = False
    is_deleted: bool = False
    
    # Delta details
    imports_added: list = field(default_factory=list)
    imports_removed: list = field(default_factory=list)
    imports_changed: list = field(default_factory=list)
    
    artifacts_added: list = field(default_factory=list)
    artifacts_removed: list = field(default_factory=list)
    artifacts_changed: list = field(default_factory=list)
    
    metadata_changes: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return (
            not self.is_new
            and not self.is_deleted
            and not self.imports_added
            and not self.imports_removed
            and not self.imports_changed
            and not self.artifacts_added
            and not self.artifacts_removed
            and not self.artifacts_changed
            and not self.metadata_changes
        )

@dataclass
class AnalysisResult:
    """Canonical in-memory result of a full project analysis."""
    repo_name: str
    root_path: str
    modules: Dict[str, Any]
    graph: Optional[Any]
    metrics: Dict[str, Any]
    cycles: list
    debt: Dict[str, Any]
    collisions: list
    hotspots: list
    layer_index: list
    artifacts: Dict[str, Any]
    compact_artifacts: Dict[str, Any]
    summary_data: Dict[str, Any]
    report_header: Dict[str, Any]
    trie: Optional[Any] = None
    package_root: str = ""
    collision_facts: Optional[Dict[str, Any]] = None
    live_publish_status: str = "not_attempted"
    live_publish_revision: Optional[int] = None
    live_publish_warning: Optional[str] = None


@dataclass
class RepositoryAnalysisState:
    """Canonical runtime state of the repository analysis."""
    modules: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    dependency_graph: Optional[Any] = None
    artifact_consumption: Dict[str, Any] = field(default_factory=dict)
    artifact_consumption_state: str = "deferred"
    layer_information: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    file_state: Dict[str, FileState] = field(default_factory=dict)
    module_parse_freshness: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    module_usages: Dict[str, Any] = field(default_factory=dict)
    topology_analytics: Dict[str, Any] = field(default_factory=dict)
    topology_metrics_state: str = "deferred"
    cached_analytics: Dict[str, Any] = field(default_factory=dict)
    cached_analytics_state: str = "deferred"
    cycles: list = field(default_factory=list)
    cycles_state: str = "deferred"
    collision_facts: Dict[str, list] = field(default_factory=dict)
    collisions: list = field(default_factory=list)
    collisions_state: str = "deferred"

    # Canonical derived analytics: Dependency Matrix
    dependency_matrix: Dict[str, Any] = field(default_factory=dict)
    dependency_matrix_state: str = "deferred"

    # Canonical derived analytics: Shared Usage Clusters
    shared_usage_clusters: list = field(default_factory=list)
    shared_usage_clusters_state: str = "deferred"

    # Required for canonical graph edge resolution


    trie: Optional[Any] = None
    package_root: str = ""


def module_current_truth(state: RepositoryAnalysisState, module_name: str) -> Dict[str, Any]:
    """Return authoritative per-module parse freshness and provenance."""
    freshness = getattr(state, "module_parse_freshness", {}) or {}
    entry = freshness.get(module_name)
    if not isinstance(entry, dict) or entry.get("state") != "stale":
        return {"available": True, "state": "fresh", "provenance": "current"}
    return {
        "available": False,
        "state": "stale",
        "provenance": "last_known_good",
        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
        "parse_failure": {
            key: entry.get(key)
            for key in ("error", "line_number", "column_number")
            if entry.get(key) is not None
        },
    }


def mark_module_parse_failure(
    state: RepositoryAnalysisState,
    module_name: str,
    *,
    error: str | None,
    line_number: int | None,
    column_number: int | None,
) -> None:
    """Mark retained module facts as last-known-good after a parse failure."""
    freshness = getattr(state, "module_parse_freshness", None)
    if not isinstance(freshness, dict):
        freshness = {}
        state.module_parse_freshness = freshness
    freshness[module_name] = {
        "state": "stale",
        "error": error,
        "line_number": line_number,
        "column_number": column_number,
    }


def clear_module_parse_failure(
    state: RepositoryAnalysisState, module_name: str
) -> bool:
    """Clear parse failure and report whether this is a recovery transition."""
    freshness = getattr(state, "module_parse_freshness", None)
    if not isinstance(freshness, dict):
        return False
    entry = freshness.get(module_name)
    recovered = isinstance(entry, dict) and entry.get("state") == "stale"
    freshness.pop(module_name, None)
    return recovered




class FileStateManager:
    """Tracks analyzed files, detects changes, and stores metadata for incremental analysis."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.state_file = self.cache_dir / "file_state.json"
        self._state: Dict[str, FileState] = {}
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        self.state_id = ""
        self.revision = None
        metadata_file = self.cache_dir / "engine_state.meta.json"
        state_file = self.state_file
        expected_engine_revision = None
        expected_engine_state_id = ""
        referenced_generation = False
        metadata_invalid = False
        if metadata_file.exists():
            try:
                engine_meta = json.loads(metadata_file.read_text(encoding="utf-8"))
                expected_engine_revision = engine_meta.get("revision")
                expected_engine_state_id = str(engine_meta.get("state_id", ""))
                referenced = engine_meta.get("file_state_file")
                if referenced:
                    referenced_generation = True
                    state_file = self.cache_dir / str(referenced)
            except (
                OSError,
                json.JSONDecodeError,
                TypeError,
                AttributeError,
                ValueError,
            ):
                metadata_invalid = True
        if metadata_invalid:
            return
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "_meta" in data:
                        file_meta = data["_meta"]
                        if not isinstance(file_meta, dict):
                            raise ValueError("FileState metadata must be a mapping")
                        self.state_id = file_meta.get("state_id", "")
                        self.revision = file_meta.get("revision", None)
                        files_data = data.get("files", {})
                    else:
                        if referenced_generation:
                            raise ValueError("Referenced FileState generation lacks metadata")
                        files_data = data
                        
                    self._state = {
                        path: FileState.from_dict(fs) 
                        for path, fs in files_data.items()
                    }
                    if (
                        referenced_generation
                        and (
                            not self.state_id
                            or self.revision is None
                        )
                    ):
                        raise ValueError("Referenced FileState generation metadata is incomplete")
                    if (
                        expected_engine_revision is not None
                        and self.revision is not None
                        and self.revision != expected_engine_revision
                    ) or (
                        expected_engine_state_id
                        and self.state_id
                        and self.state_id != expected_engine_state_id
                    ):
                        self._state = {}
                        self.state_id = ""
                        self.revision = None
            except (
                OSError,
                json.JSONDecodeError,
                KeyError,
                TypeError,
                AttributeError,
                ValueError,
            ):
                self._state = {}
                self.state_id = ""
                self.revision = None

    def save(self, state_id: str = "", revision: int | None = None):
        payload = self.build_payload(state_id, revision)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        self.state_id = state_id
        if revision is not None:
            self.revision = revision

    def build_payload(self, state_id: str = "", revision: int | None = None) -> dict:
        effective_revision = self.revision if revision is None else revision
        meta: Dict[str, Any] = {"state_id": state_id}
        if effective_revision is not None:
            meta["revision"] = effective_revision
        return {
            "_meta": meta,
            "files": {path: fs.to_dict() for path, fs in self._state.items()},
        }

    def _compute_hash(self, file_path: str) -> str:
        import hashlib
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def get_current_file_state(self, file_path: str, compute_hash: bool = False) -> Optional[FileState]:
        """Gets the current mtime and size from the filesystem."""
        try:
            stat = os.stat(file_path)
            h = self._compute_hash(file_path) if compute_hash else ""
            return FileState(mtime_ns=stat.st_mtime_ns, size=stat.st_size, sha256=h)
        except FileNotFoundError:
            return None

    def has_changed(self, file_path: str) -> bool:
        """Returns True if the file was modified since it was last tracked."""
        current = self.get_current_file_state(file_path, compute_hash=False)
        if not current:
            # File does not exist on disk -> deleted or new non-existent path
            return True

            
        tracked = self._state.get(file_path)
        if not tracked:
            return True # New file
            
        if (tracked.mtime_ns != current.mtime_ns) or (tracked.size != current.size):
            return True
            
        # Fallback: mtime and size match, but content might be different
        if not tracked.sha256:
            return True
            
        current_hash = self._compute_hash(file_path)
        return tracked.sha256 != current_hash

    def tracked_paths(self) -> set[str]:
        """Return the persisted file domain used by incremental analysis."""
        return set(self._state)

    def update_state(self, file_path: str):
        """
        Updates the tracked state for a given file in RAM.
        Disk persistence (save) should be debounced or handled asynchronously 
        to ensure < 100ms real-time latency.
        """
        current = self.get_current_file_state(file_path, compute_hash=True)
        if current:
            self._state[file_path] = current
        elif file_path in self._state:
            del self._state[file_path]

ENGINE_CACHE_SCHEMA_VERSION = "1.1"

def save_engine_state(
    state: RepositoryAnalysisState,
    cache_dir: str,
    state_id: str,
    *,
    writer: str = "unknown",
    repo_id: str = "",
    root_path: str = "",
):
    from contextor.core.live_state import save_snapshot
    try:
        return save_snapshot(
            state,
            cache_dir,
            state_id,
            writer=writer,
            repo_id=repo_id,
            root_path=root_path,
        )
    except Exception as e:
        import sys
        print(f"Failed to save engine state: {e}", file=sys.stderr)
        return None

def load_engine_state(
    cache_dir: str,
    expected_state_id: str,
    *,
    expected_repo_id: str = "",
    expected_root_path: str = "",
) -> Optional[RepositoryAnalysisState]:
    from contextor.core.live_state import load_snapshot
    try:
        loaded = load_snapshot(
            cache_dir,
            expected_state_id,
            expected_repo_id=expected_repo_id,
            expected_root_path=expected_root_path,
        )
        return loaded[0] if loaded else None
    except Exception as e:
        import sys
        print(f"Failed to load engine state: {e}", file=sys.stderr)
        return None


CANONICAL_USAGE_CHANNELS: frozenset[str] = frozenset({
    "direct_calls",
    "runtime_calls",
    "qualified_refs",
    "callback_calls",
    "event_bindings",
    "api_imports",
    "inheritance",
})


def is_legacy_artifact_consumption(consumption: Any) -> bool:
    """
    Returns True if consumption matches a known legacy persisted structure
    that is safe and expected to migrate in RAM:
    - Dict containing "_report" (historical reporting payload snapshot).
    """
    if consumption is None:
        return True
    if isinstance(consumption, dict) and "_report" in consumption:
        return True
    return False


def validate_canonical_artifact_consumption(consumption: Any) -> bool:
    """
    Validates that consumption adheres strictly to the canonical per-target contract:
    - Dict with target keys strictly of shape "<non-empty definer>::<non-empty symbol>"
    - Rejects legacy "_report" payload
    - Each value is dict with "consumers" (sorted unique list[str]) and "channels" (dict[str, sorted unique list[str]])
    - channels keys are a subset of consumers (set(channels) <= set(consumers))
    - all channel names belong to CANONICAL_USAGE_CHANNELS
    - deterministic ordering: consumers == sorted(set(consumers)), ch_list == sorted(set(ch_list))
    """
    if not isinstance(consumption, dict):
        return False
    if "_report" in consumption:
        return False

    for target, entry in consumption.items():
        if not isinstance(target, str) or not target:
            return False

        definer, sep, symbol = target.partition("::")
        if not sep or not definer or not symbol:
            return False

        if not isinstance(entry, dict):
            return False

        consumers = entry.get("consumers")
        if not isinstance(consumers, list):
            return False

        for c in consumers:
            if not isinstance(c, str) or not c:
                return False

        # Deterministic sorting and uniqueness invariant
        if consumers != sorted(set(consumers)):
            return False

        consumer_set = set(consumers)

        channels = entry.get("channels")
        if not isinstance(channels, dict):
            return False

        # Invariant: set(channels.keys()) <= set(consumers)
        if not set(channels.keys()).issubset(consumer_set):
            return False

        for c_mod, ch_list in channels.items():
            if not isinstance(ch_list, list):
                return False
            if ch_list != sorted(set(ch_list)):
                return False
            for ch in ch_list:
                if not isinstance(ch, str) or ch not in CANONICAL_USAGE_CHANNELS:
                    return False

    return True


def canonical_artifact_consumption_targets(
    artifacts: dict[str, Any] | None,
) -> set[str]:
    """
    Computes the exact set of expected canonical target keys (f"{module_path}::{symbol}")
    from defined symbols in artifacts fact dictionaries.
    """
    targets: set[str] = set()
    if not isinstance(artifacts, dict):
        return targets

    for module_path, module_data in artifacts.items():
        if not isinstance(module_path, str) or not isinstance(module_data, dict):
            continue

        # 1. Check own_symbols if available
        own_symbols = module_data.get("own_symbols")
        if isinstance(own_symbols, (list, set, tuple)) and own_symbols:
            for sym in own_symbols:
                if isinstance(sym, str) and sym:
                    targets.add(f"{module_path}::{sym}")
            continue

        # 2. Check symbols dict if available
        symbols = module_data.get("symbols")
        if isinstance(symbols, dict):
            has_syms = False
            for cat in ("classes", "functions", "methods", "globals"):
                cat_syms = symbols.get(cat, [])
                if isinstance(cat_syms, (list, set, tuple)):
                    for sym in cat_syms:
                        if isinstance(sym, str) and sym:
                            targets.add(f"{module_path}::{sym}")
                            has_syms = True
            if has_syms:
                continue

        # 3. Fallback for legacy format where only consumers dict is present
        consumers_by_symbol = module_data.get("consumers", {})
        if isinstance(consumers_by_symbol, dict):
            for symbol, entry in consumers_by_symbol.items():
                if isinstance(symbol, str) and symbol and isinstance(entry, dict):
                    targets.add(f"{module_path}::{symbol}")

    return targets


def validate_canonical_artifact_consumption_coverage(
    consumption: Any,
    artifacts: Any,
) -> bool:
    """
    Validates that consumption contains exactly the expected set of canonical targets
    derived from artifacts:
    - consumption must be structurally valid (validate_canonical_artifact_consumption)
    - set(consumption.keys()) == canonical_artifact_consumption_targets(artifacts)
    """
    if not validate_canonical_artifact_consumption(consumption):
        return False

    expected = canonical_artifact_consumption_targets(artifacts)
    actual = set(consumption.keys()) if isinstance(consumption, dict) else set()

    return actual == expected


def artifact_consumption_is_fresh(state: Any) -> bool:
    """
    Determines if state.artifact_consumption is genuinely fresh:
    - state must not have resync_required == True
    - state.artifact_consumption_state must be exactly 'fresh'
    - state.artifact_consumption must pass validate_canonical_artifact_consumption_coverage(state.artifact_consumption, state.artifacts)
    """
    if getattr(state, "resync_required", False):
        return False

    if getattr(state, "artifact_consumption_state", None) != "fresh":
        return False

    consumption = getattr(state, "artifact_consumption", None)
    artifacts = getattr(state, "artifacts", {}) or {}

    return validate_canonical_artifact_consumption_coverage(consumption, artifacts)


def dependency_matrix_inputs_are_fresh(state: Any) -> bool:
    """
    Determines if canonical inputs required for Dependency Matrix are genuinely fresh:
    - state must not have resync_required == True
    - artifact_consumption must be genuinely fresh (artifact_consumption_is_fresh(state))
    - dependency_graph must be available and valid (not None, has hard_edges dict mapping)
    """
    if getattr(state, "resync_required", False):
        return False

    if not artifact_consumption_is_fresh(state):
        return False

    graph = getattr(state, "dependency_graph", None)
    if graph is None:
        return False

    hard_edges = getattr(graph, "hard_edges", None)
    if not isinstance(hard_edges, dict):
        return False

    return True


def build_canonical_artifact_consumption(
    artifacts: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Transform raw analysis module artifacts into normalized canonical per-target
    artifact_consumption mapping.

    Schema:
        {
            "<definer_module>::<qualified_symbol>": {
                "consumers": sorted_list_of_consumers,
                "channels": {
                    "<consumer_module>": sorted_list_of_channels,
                },
            },
        }
    """
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(artifacts, dict):
        return result

    # Pre-populate all expected canonical targets with empty consumers/channels
    for target in canonical_artifact_consumption_targets(artifacts):
        result[target] = {"consumers": [], "channels": {}}

    for module_path, module_data in artifacts.items():
        if not isinstance(module_data, dict):
            continue

        consumers_by_symbol = module_data.get("consumers", {})
        if not isinstance(consumers_by_symbol, dict):
            continue

        for symbol, entry in consumers_by_symbol.items():
            if not isinstance(symbol, str) or not isinstance(entry, dict):
                continue

            target = f"{module_path}::{symbol}"

            raw_consumers = entry.get("consumers", [])
            consumers = sorted(
                {
                    consumer
                    for consumer in raw_consumers
                    if isinstance(consumer, str) and consumer
                }
            )
            consumer_set = set(consumers)

            usage = entry.get("usage", {})
            channels_by_consumer: dict[str, list[str]] = {}

            if isinstance(usage, dict):
                for channel, channel_consumers in usage.items():
                    if channel not in CANONICAL_USAGE_CHANNELS:
                        continue

                    if not isinstance(channel_consumers, (list, tuple, set)):
                        continue

                    for consumer in channel_consumers:
                        if (
                            isinstance(consumer, str)
                            and consumer
                            and consumer in consumer_set
                        ):
                            channels_by_consumer.setdefault(
                                consumer, []
                            ).append(channel)

            result[target] = {
                "consumers": consumers,
                "channels": {
                    consumer: sorted(set(channels))
                    for consumer, channels in channels_by_consumer.items()
                },
            }

    return result
