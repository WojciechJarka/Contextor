"""
contextor/core/reporting_engine/persistent_registry.py

Persistent identity registry for analyzed repositories.

ARCHITECTURAL ROLE
------------------
This module owns persistent repository identity and index state.

The registry is NOT stored inside the analyzed repository.

All persistent repository data is stored centrally under:

    <Contextor root>/.contextor/repositories/<repo_name>_<repo_id>/

Each repository directory contains its own:

    repo.meta.json
    module_slots.json
    artifact_slots.json
    module_recovery.json
    artifact_recovery.json
    output_references.json
    module_registry.json
    artifact_registry.json
    .lock
    transaction.tmp

Repository identity is defined by `repo.meta.json`.

The repository root path is therefore metadata, not storage location.

IMPORTANT
---------
A repository may be moved to another filesystem location. Its persistent
identity remains stable as long as its repository ID is retained and the
metadata is updated by the higher-level repository/index manager.

This module deliberately does not create:

    <repo_root>/.contextor/

The analyzed repository must remain free of Contextor's central persistent
index storage.

TRANSACTION MODEL
-----------------
Registry mutations are persisted through a small transactional protocol:

1. Acquire the repository-specific lock.
2. Reload persistent state.
3. Mutate in-memory state.
4. Write every changed state file to a temporary file.
5. fsync temporary files.
6. Write transaction metadata.
7. Atomically replace the persistent JSON files.
8. Remove transaction metadata.

Interrupted transactions are recovered on the next initialization.

IDENTITY MODEL
--------------
Repository identity:

    repo_id = ctx_<8 hexadecimal characters>

Module identity:

    <slot>/<generation>

Artifact identity:

    A<slot>/<generation>

The repository ID is independent from module/artifact IDs.
"""

import datetime
import json
import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class PersistentIdentityRegistry:
    """
    Persistent identity and recovery registry for one repository.

    The registry state is stored centrally inside Contextor rather than
    inside the analyzed repository.

    Parameters
    ----------
    repo_path:
        Absolute or relative filesystem path of the repository being
        analyzed.

    Notes
    -----
    `repo_path` identifies the repository being operated on.

    It does NOT determine where persistent registry files are stored.
    Persistent storage is always resolved relative to the Contextor
    installation/package root.
    """

    SCHEMA_VERSION = 1
    REPOSITORIES_DIRNAME = "repositories"

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).expanduser().resolve()

        # ------------------------------------------------------------
        # Central Contextor persistent storage
        # ------------------------------------------------------------
        self.contextor_root = self._resolve_contextor_root()
        self.contextor_dir = self.contextor_root / ".contextor"
        self.repositories_dir = (
            self.contextor_dir / self.REPOSITORIES_DIRNAME
        )

        self.contextor_dir.mkdir(parents=True, exist_ok=True)
        self.repositories_dir.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------------------
        # Repository identity
        # ------------------------------------------------------------
        self.repo_id: str
        self.repo_name: str
        self.repo_registry_dir: Path
        self.meta_file: Path

        self._initialize_repository_identity()

        # ------------------------------------------------------------
        # Repository-local persistent state
        # ------------------------------------------------------------
        self.registry_dir = self.repo_registry_dir

        self.lock_file = self.registry_dir / ".lock"
        self.transaction_file = self.registry_dir / "transaction.tmp"

        self.files = {
            "module_slots": self.registry_dir / "module_slots.json",
            "artifact_slots": self.registry_dir / "artifact_slots.json",
            "module_recovery": self.registry_dir / "module_recovery.json",
            "artifact_recovery": self.registry_dir / "artifact_recovery.json",
            "output_references": self.registry_dir / "output_references.json",
            "module_registry": self.registry_dir / "module_registry.json",
            "artifact_registry": self.registry_dir / "artifact_registry.json",
        }

        self._state: Dict[str, Dict[str, Any]] = {}
        self._in_transaction = False
        self._lock_file_obj = None

        # Recover an interrupted transaction before loading state.
        self._recover_transaction()
        self._load_all()

    # ================================================================
    # Contextor / repository location
    # ================================================================

    def _resolve_contextor_root(self) -> Path:
        """
        Resolve the root directory of the current Contextor installation.

        The location is derived from this module's actual filesystem
        location and therefore does not depend on a hard-coded absolute
        path.

        Expected source layout:

            <Contextor root>/
                contextor/
                    core/
                        reporting_engine/
                            persistent_registry.py

        The method walks upward until it finds the `contextor` package
        directory and returns its parent.

        Raises
        ------
        RuntimeError
            If the Contextor package root cannot be determined.
        """
        module_path = Path(__file__).resolve()

        for parent in module_path.parents:
            if parent.name == "contextor":
                return parent.parent

        raise RuntimeError(
            "Unable to resolve Contextor root from persistent_registry.py"
        )

    def _safe_repository_directory_name(self, repo_name: str) -> str:
        """
        Build a filesystem-safe persistent repository directory name.

        The human-readable repository name is retained and the stable
        repository ID is appended to prevent collisions between two
        repositories having the same directory name.

        Example
        -------
        Contextor_Repo + ctx_3ff8f18f

        becomes:

            Contextor_Repo_ctx_3ff8f18f
        """
        safe_name = "".join(
            character
            if character.isalnum() or character in ("-", "_", ".")
            else "_"
            for character in repo_name
        ).strip("_")

        if not safe_name:
            safe_name = "repository"

        return f"{safe_name}_{self.repo_id}"

    def _initialize_repository_identity(self) -> None:
        """
        Resolve or create the persistent identity of this repository.

        Repository identities are looked up by `root_path` among existing
        `repo.meta.json` files.

        If no existing identity matches the repository path, a new stable
        repository ID is created and a new central repository directory is
        initialized.

        This method never creates `.contextor` inside the analyzed
        repository.
        """
        resolved_root = str(self.repo_path)

        # ------------------------------------------------------------
        # Existing repository identity
        # ------------------------------------------------------------
        for meta_file in self.repositories_dir.glob(
            "*/repo.meta.json"
        ):
            try:
                data = json.loads(
                    meta_file.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                continue

            if data.get("root_path") == resolved_root:
                repo_id = data.get("repo_id")
                repo_name = data.get("repo_name")

                if not repo_id:
                    continue

                self.repo_id = repo_id
                self.repo_name = repo_name or self.repo_path.name
                self.repo_registry_dir = meta_file.parent
                self.meta_file = meta_file

                # Keep the current physical location authoritative.
                if data.get("root_path") != resolved_root:
                    data["root_path"] = resolved_root
                    meta_file.write_text(
                        json.dumps(data, indent=2),
                        encoding="utf-8",
                    )

                return

        # ------------------------------------------------------------
        # New repository identity
        # ------------------------------------------------------------
        self.repo_id = f"ctx_{uuid.uuid4().hex[:8]}"
        self.repo_name = self.repo_path.name

        directory_name = self._safe_repository_directory_name(
            self.repo_name
        )

        self.repo_registry_dir = (
            self.repositories_dir / directory_name
        )
        self.repo_registry_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.meta_file = self.repo_registry_dir / "repo.meta.json"

        data = {
            "schema_version": self.SCHEMA_VERSION,
            "repo_id": self.repo_id,
            "repo_name": self.repo_name,
            "root_path": resolved_root,
            "created_at": datetime.datetime.now().isoformat(),
        }

        self.meta_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    # ================================================================
    # JSON state
    # ================================================================

    def _base_header(self) -> Dict[str, Any]:
        """
        Return the common identity header written to every registry JSON.
        """
        return {
            "schema_version": self.SCHEMA_VERSION,
            "repo_id": self.repo_id,
        }

    def _load_json(self, name: str) -> Dict[str, Any]:
        """
        Load one persistent registry file.

        Existing files are returned as-is, except that missing identity
        metadata is supplemented in memory.

        Corrupt or missing files receive their appropriate empty structure.
        """
        path = self.files[name]

        if path.exists():
            try:
                data = json.loads(
                    path.read_text(encoding="utf-8")
                )

                if "repo_id" not in data:
                    data["repo_id"] = self.repo_id

                if "schema_version" not in data:
                    data["schema_version"] = self.SCHEMA_VERSION

                return data

            except (OSError, json.JSONDecodeError):
                pass

        data = self._base_header()

        if "registry" in name:
            data.update(
                {
                    "path_to_id": {},
                    "id_to_path": {},
                }
            )
        elif "references" in name:
            data.update(
                {
                    "id_to_reports": {},
                    "report_to_ids": {},
                }
            )

        return data

    def _load_all(self) -> None:
        """
        Load the complete persistent state into memory.
        """
        self._state = {
            name: self._load_json(name)
            for name in self.files
        }

    # ================================================================
    # Locking
    # ================================================================

    def _lock(self) -> None:
        """
        Acquire the repository-specific persistent registry lock.
        """
        self._lock_file_obj = open(self.lock_file, "a+")

        if sys.platform == "win32":
            import msvcrt

            self._lock_file_obj.seek(0)
            msvcrt.locking(
                self._lock_file_obj.fileno(),
                msvcrt.LK_LOCK,
                1,
            )
        else:
            import fcntl

            fcntl.flock(
                self._lock_file_obj,
                fcntl.LOCK_EX,
            )

    def _unlock(self) -> None:
        """
        Release the repository-specific persistent registry lock.
        """
        if not self._lock_file_obj:
            return

        if sys.platform == "win32":
            import msvcrt

            self._lock_file_obj.seek(0)
            msvcrt.locking(
                self._lock_file_obj.fileno(),
                msvcrt.LK_UNLCK,
                1,
            )
        else:
            import fcntl

            fcntl.flock(
                self._lock_file_obj,
                fcntl.LOCK_UN,
            )

        self._lock_file_obj.close()
        self._lock_file_obj = None

    # ================================================================
    # Transaction recovery
    # ================================================================

    def _recover_transaction(self) -> None:
        """
        Recover a transaction interrupted during atomic replacement.

        Temporary JSON files are promoted only when transaction metadata
        indicates that the commit phase had started.
        """
        if not self.transaction_file.exists():
            return

        try:
            tx = json.loads(
                self.transaction_file.read_text(
                    encoding="utf-8"
                )
            )

            if tx.get("status") == "committing":
                for file_key in tx.get("files", []):
                    path = self.files.get(file_key)

                    if path is None:
                        continue

                    tmp_path = path.with_suffix(".json.tmp")

                    if tmp_path.exists():
                        os.replace(tmp_path, path)

        except (OSError, json.JSONDecodeError):
            pass

        try:
            self.transaction_file.unlink()
        except OSError:
            pass

    @contextmanager
    def transaction(self):
        """
        Execute registry mutations as one persistent transaction.

        Nested transactions reuse the outer transaction and do not acquire
        the filesystem lock twice.
        """
        if self._in_transaction:
            yield
            return

        self._lock()
        self._in_transaction = True

        try:
            self._recover_transaction()
            self._load_all()

            yield

            # --------------------------------------------------------
            # Prepare all temporary files.
            # --------------------------------------------------------
            for name, path in self.files.items():
                tmp_path = path.with_suffix(".json.tmp")

                data_str = json.dumps(
                    self._state[name],
                    indent=2,
                )

                tmp_path.write_text(
                    data_str,
                    encoding="utf-8",
                )

                with open(tmp_path, "a", encoding="utf-8") as handle:
                    handle.flush()
                    os.fsync(handle.fileno())

            # --------------------------------------------------------
            # Record commit intent before atomic replacement.
            # --------------------------------------------------------
            tx_data = {
                "transaction_id": f"tx_{uuid.uuid4().hex[:8]}",
                "repo_id": self.repo_id,
                "files": list(self.files.keys()),
                "status": "committing",
            }

            self.transaction_file.write_text(
                json.dumps(tx_data, indent=2),
                encoding="utf-8",
            )

            with open(
                self.transaction_file,
                "a",
                encoding="utf-8",
            ) as handle:
                handle.flush()
                os.fsync(handle.fileno())

            # --------------------------------------------------------
            # Atomic replacement.
            # --------------------------------------------------------
            for name in self.files:
                path = self.files[name]
                tmp_path = path.with_suffix(".json.tmp")
                os.replace(tmp_path, path)

            try:
                self.transaction_file.unlink()
            except FileNotFoundError:
                pass

        finally:
            self._in_transaction = False
            self._unlock()

    # ================================================================
    # Identity allocation
    # ================================================================

    def _allocate_slot(self, kind: str) -> str:
        """
        Allocate the smallest currently unused slot and advance its
        generation counter.
        """
        registry = self._state[f"{kind}_registry"]
        slots = self._state[f"{kind}_slots"]

        used_slots = set()

        for id_str in registry["id_to_path"].keys():
            slot_part = id_str.split("/")[0]

            if kind == "artifact" and slot_part.startswith("A"):
                slot_part = slot_part[1:]

            used_slots.add(int(slot_part))

        slot = 1

        while slot in used_slots:
            slot += 1

        slot_str = str(slot)
        generation = slots.get(slot_str, 0) + 1
        slots[slot_str] = generation

        prefix = "A" if kind == "artifact" else ""

        return f"{prefix}{slot}/{generation}"

    # ================================================================
    # Public identity API
    # ================================================================

    def get_repo_id(self) -> str:
        """
        Return the stable identity of the current repository.
        """
        return self.repo_id

    def get_repo_name(self) -> str:
        """
        Return the human-readable repository name.
        """
        return self.repo_name

    def get_repo_root(self) -> str:
        """
        Return the current physical root path of the repository.
        """
        return str(self.repo_path)

    def get_registry_dir(self) -> Path:
        """
        Return the central persistent directory assigned to this repository.
        """
        return self.registry_dir

    # ================================================================
    # Module / artifact IDs
    # ================================================================

    def get_module_id(self, path: str) -> Optional[str]:
        """
        Return the persistent ID assigned to a module path.

        A new ID is allocated only inside an active transaction.
        """
        obj_id = self._state["module_registry"][
            "path_to_id"
        ].get(path)

        if obj_id:
            return obj_id

        if self._in_transaction:
            new_id = self._allocate_slot("module")

            self._state["module_registry"][
                "path_to_id"
            ][path] = new_id

            self._state["module_registry"][
                "id_to_path"
            ][new_id] = path

            return new_id

        return None

    def get_artifact_id(self, name: str) -> Optional[str]:
        """
        Return the persistent ID assigned to an artifact name.

        A new ID is allocated only inside an active transaction.
        """
        obj_id = self._state["artifact_registry"][
            "path_to_id"
        ].get(name)

        if obj_id:
            return obj_id

        if self._in_transaction:
            new_id = self._allocate_slot("artifact")

            self._state["artifact_registry"][
                "path_to_id"
            ][name] = new_id

            self._state["artifact_registry"][
                "id_to_path"
            ][new_id] = name

            return new_id

        return None

    def list_modules(self) -> List[str]:
        """
        Return all currently active module paths.
        """
        return list(
            self._state["module_registry"][
                "path_to_id"
            ].keys()
        )

    def get_module_path(self, obj_id: str) -> Optional[str]:
        """
        Resolve a module ID.

        Active registry is checked first. Recovery is used as fallback.
        """
        path = self._state["module_registry"][
            "id_to_path"
        ].get(obj_id)

        if path:
            return path

        recovery = self._state["module_recovery"].get(obj_id)

        if recovery:
            return recovery.get("path")

        return None

    def get_artifact_name(self, obj_id: str) -> Optional[str]:
        """
        Resolve an artifact ID.

        Active registry is checked first. Recovery is used as fallback.
        """
        name = self._state["artifact_registry"][
            "id_to_path"
        ].get(obj_id)

        if name:
            return name

        recovery = self._state["artifact_recovery"].get(obj_id)

        if recovery:
            return recovery.get("name")

        return None

    # ================================================================
    # Workspace synchronization
    # ================================================================

    def sync_with_workspace(
        self,
        current_modules: Set[str],
        current_artifacts: Set[str],
    ) -> None:
        """
        Synchronize persistent identity with the current workspace.

        Missing objects are moved to recovery. Existing recovered objects
        are restored when their exact path/name reappears.
        """
        self._sync_kind("module", current_modules)
        self._sync_kind("artifact", current_artifacts)

    def _sync_kind(
        self,
        kind: str,
        current_items: Set[str],
    ) -> None:
        """
        Synchronize one identity namespace.
        """
        registry = self._state[f"{kind}_registry"]
        recovery = self._state[f"{kind}_recovery"]

        active_paths = list(
            registry["path_to_id"].keys()
        )

        # ------------------------------------------------------------
        # Move missing active objects to recovery.
        # ------------------------------------------------------------
        for path in active_paths:
            if path not in current_items:
                obj_id = registry["path_to_id"][path]

                recovery[obj_id] = {
                    "type": kind,
                    (
                        "path"
                        if kind == "module"
                        else "name"
                    ): path,
                    "removed_at": datetime.datetime.now().isoformat(),
                    "status": "orphan",
                }

                del registry["path_to_id"][path]
                del registry["id_to_path"][obj_id]

        # ------------------------------------------------------------
        # Restore recovered objects or allocate new identities.
        # ------------------------------------------------------------
        for path in current_items:
            if path in registry["path_to_id"]:
                continue

            restored_id = None

            for rec_id, rec_data in list(recovery.items()):
                if rec_id == "schema_version":
                    continue

                key = (
                    "path"
                    if kind == "module"
                    else "name"
                )

                if rec_data.get(key) == path:
                    if rec_id not in registry["id_to_path"]:
                        restored_id = rec_id
                    break

            if restored_id:
                registry["path_to_id"][path] = restored_id
                registry["id_to_path"][restored_id] = path
                del recovery[restored_id]
            else:
                new_id = self._allocate_slot(kind)

                registry["path_to_id"][path] = new_id
                registry["id_to_path"][new_id] = path

    # ================================================================
    # Report references
    # ================================================================

    def register_report_references(
        self,
        report_name: str,
        used_ids: List[str],
    ) -> None:
        """
        Register which persistent IDs are referenced by a report.
        """
        refs = self._state["output_references"]

        self.unregister_report_references(report_name)

        unique_ids = list(dict.fromkeys(used_ids))

        refs["report_to_ids"][report_name] = unique_ids

        for obj_id in unique_ids:
            if obj_id not in refs["id_to_reports"]:
                refs["id_to_reports"][obj_id] = []

            if report_name not in refs["id_to_reports"][obj_id]:
                refs["id_to_reports"][obj_id].append(report_name)

    def unregister_report_references(
        self,
        report_name: str,
    ) -> None:
        """
        Remove all persistent-ID references associated with a report.
        """
        refs = self._state["output_references"]

        if report_name not in refs["report_to_ids"]:
            return

        used_ids = refs["report_to_ids"][report_name]

        for obj_id in used_ids:
            if obj_id not in refs["id_to_reports"]:
                continue

            try:
                refs["id_to_reports"][obj_id].remove(report_name)
            except ValueError:
                pass

            if not refs["id_to_reports"][obj_id]:
                del refs["id_to_reports"][obj_id]

        del refs["report_to_ids"][report_name]

    # ================================================================
    # Garbage collection
    # ================================================================

    def run_garbage_collector(
        self,
        max_module_recovery_bytes: int = 250 * 1024,
        max_artifact_recovery_bytes: int = 100 * 1024,
    ) -> None:
        """
        Trim recovery buffers while preserving IDs referenced by reports.
        """
        self._gc_kind(
            "module",
            max_module_recovery_bytes,
        )
        self._gc_kind(
            "artifact",
            max_artifact_recovery_bytes,
        )

    def _gc_kind(
        self,
        kind: str,
        max_bytes: int,
    ) -> None:
        """
        Garbage-collect one recovery namespace.

        Oldest unreferenced orphan entries are removed first.
        Entries referenced by reports are always retained.
        """
        recovery = self._state[f"{kind}_recovery"]

        current_size = len(
            json.dumps(recovery).encode("utf-8")
        )

        if current_size <= max_bytes:
            return

        refs = self._state[
            "output_references"
        ]["id_to_reports"]

        def get_date(item):
            return item[1].get(
                "removed_at",
                "1970-01-01",
            )

        sorted_orphans = sorted(
            (
                (key, value)
                for key, value in recovery.items()
                if key != "schema_version"
            ),
            key=get_date,
        )

        for obj_id, _ in sorted_orphans:
            if obj_id in refs and refs[obj_id]:
                continue

            del recovery[obj_id]

            current_size = len(
                json.dumps(recovery).encode("utf-8")
            )

            if current_size <= max_bytes:
                break