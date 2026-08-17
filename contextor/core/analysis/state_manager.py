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


@dataclass
class RepositoryAnalysisState:
    """Canonical runtime state of the repository analysis."""
    modules: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    dependency_graph: Optional[Any] = None
    artifact_consumption: Dict[str, Any] = field(default_factory=dict)
    layer_information: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    file_state: Dict[str, FileState] = field(default_factory=dict)
    module_usages: Dict[str, Any] = field(default_factory=dict)
    topology_analytics: Dict[str, Any] = field(default_factory=dict)
    topology_metrics_state: str = "deferred"
    cached_analytics: Dict[str, Any] = field(default_factory=dict)
    cached_analytics_state: str = "deferred"
    
    # Required for canonical graph edge resolution


    trie: Optional[Any] = None
    package_root: str = ""




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
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "_meta" in data:
                        self.state_id = data["_meta"].get("state_id", "")
                        files_data = data.get("files", {})
                    else:
                        files_data = data
                        
                    self._state = {
                        path: FileState.from_dict(fs) 
                        for path, fs in files_data.items()
                    }
            except (json.JSONDecodeError, KeyError):
                self._state = {}

    def save(self, state_id: str = ""):
        self.state_id = state_id
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({
                "_meta": {"state_id": state_id},
                "files": {path: fs.to_dict() for path, fs in self._state.items()}
            }, f, indent=2)

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
        save_snapshot(
            state,
            cache_dir,
            state_id,
            writer=writer,
            repo_id=repo_id,
            root_path=root_path,
        )
        return True
    except Exception as e:
        import sys
        print(f"Failed to save engine state: {e}", file=sys.stderr)
        return False

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
