import os
import json
import sys
import uuid
import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, List, Set, Optional


class PersistentIdentityRegistry:
    SCHEMA_VERSION = 1

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).expanduser().resolve()
        from contextor.core.repository_identity import ensure_repository_identity

        identity, self.registry_dir = ensure_repository_identity(self.repo_path)
        self.repo_id = identity.repo_id

        self.meta_file = self.registry_dir / "repo.meta.json"

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

        self._state = {}
        self._in_transaction = False
        self._lock_file_obj = None

        self._recover_transaction()
        self._load_all()

    def _lock(self):
        self._lock_file_obj = open(self.lock_file, "w")

        if sys.platform == "win32":
            import msvcrt

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

    def _unlock(self):
        if self._lock_file_obj:
            if sys.platform == "win32":
                import msvcrt

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

    def _load_json(self, name: str) -> Dict[str, Any]:
        path = self.files[name]

        if path.exists():
            try:
                return json.loads(
                    path.read_text(encoding="utf-8")
                )
            except Exception:
                pass

        if "registry" in name:
            return {
                "schema_version": self.SCHEMA_VERSION,
                "path_to_id": {},
                "id_to_path": {},
            }
        elif "references" in name:
            return {
                "schema_version": self.SCHEMA_VERSION,
                "id_to_reports": {},
                "report_to_ids": {},
            }
        else:
            return {
                "schema_version": self.SCHEMA_VERSION
            }

    def _load_all(self):
        self._state = {
            name: self._load_json(name)
            for name in self.files
        }
        self._repair_kind("module")
        self._repair_kind("artifact")

    def ensure_initialized(self) -> None:
        """Persist the complete dictionary set once for a new repository."""

        if all(path.is_file() for path in self.files.values()):
            return
        with self.transaction():
            pass

    def _repair_kind(self, kind: str) -> None:
        """Repair one-sided registry mappings loaded from older/corrupt state."""
        registry = self._state[f"{kind}_registry"]
        recovery = self._state[f"{kind}_recovery"]
        slots = self._state[f"{kind}_slots"]
        path_to_id = registry["path_to_id"]
        id_to_path = registry["id_to_path"]
        value_key = "path" if kind == "module" else "name"

        def record_generation(obj_id: str) -> None:
            try:
                head, raw_generation = str(obj_id).split("/", 1)
                slot = head.removeprefix("A") if kind == "artifact" else head
                generation = int(raw_generation)
                slots[slot] = max(int(slots.get(slot, 0)), generation)
            except (TypeError, ValueError):
                return

        for obj_id, path in list(id_to_path.items()):
            record_generation(obj_id)
            if isinstance(path, str) and path.strip() and path_to_id.get(path) == obj_id:
                continue
            if isinstance(path, str) and path.strip():
                recovery.setdefault(obj_id, {
                    "type": kind,
                    value_key: path,
                    "removed_at": datetime.datetime.now().isoformat(),
                    "status": "orphan",
                })
            del id_to_path[obj_id]

        for path, obj_id in list(path_to_id.items()):
            record_generation(obj_id)
            if not isinstance(path, str) or not path.strip():
                del path_to_id[path]
                id_to_path.pop(obj_id, None)
                continue
            id_to_path[obj_id] = path

        for obj_id in recovery:
            if obj_id != "schema_version":
                record_generation(obj_id)

    def _recover_transaction(self):
        if self.transaction_file.exists():
            try:
                tx = json.loads(
                    self.transaction_file.read_text(
                        encoding="utf-8"
                    )
                )

                if tx.get("status") == "committing":
                    for file_key in tx.get("files", []):
                        path = self.files.get(file_key)

                        if path:
                            tmp_path = path.with_suffix(".json.tmp")

                            if tmp_path.exists():
                                os.replace(tmp_path, path)

            except Exception:
                pass

            try:
                os.remove(self.transaction_file)
            except OSError:
                pass

    @contextmanager
    def transaction(self):
        if self._in_transaction:
            yield
            return

        self._lock()
        self._in_transaction = True

        try:
            self._recover_transaction()
            self._load_all()

            yield

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

                with open(tmp_path, "a") as f:
                    f.flush()
                    os.fsync(f.fileno())

            tx_data = {
                "transaction_id": f"tx_{uuid.uuid4().hex[:8]}",
                "files": list(self.files.keys()),
                "status": "committing",
            }

            self.transaction_file.write_text(
                json.dumps(tx_data),
                encoding="utf-8",
            )

            with open(self.transaction_file, "a") as f:
                f.flush()
                os.fsync(f.fileno())

            for name in list(self.files.keys()):
                path = self.files[name]
                tmp_path = path.with_suffix(".json.tmp")
                os.replace(tmp_path, path)

            try:
                os.remove(self.transaction_file)
            except FileNotFoundError:
                pass

        finally:
            self._in_transaction = False
            self._unlock()

    # ---- Logic Methods ----

    def _allocate_slot(self, kind: str) -> str:
        """Find the smallest available slot, update generation, return ID."""
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
        gen = slots.get(slot_str, 0) + 1
        slots[slot_str] = gen

        prefix = "A" if kind == "artifact" else ""
        return f"{prefix}{slot}/{gen}"

    def get_module_id(self, path: str) -> str:
        if not isinstance(path, str) or not path.strip():
            return None
        obj_id = self._state["module_registry"]["path_to_id"].get(path)

        if obj_id:
            return obj_id

        if self._in_transaction:
            new_id = self._allocate_slot("module")
            self._state["module_registry"]["path_to_id"][path] = new_id
            self._state["module_registry"]["id_to_path"][new_id] = path
            return new_id

        return None

    def get_artifact_id(self, name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            return None
        obj_id = self._state["artifact_registry"]["path_to_id"].get(name)

        if obj_id:
            return obj_id

        if self._in_transaction:
            new_id = self._allocate_slot("artifact")
            self._state["artifact_registry"]["path_to_id"][name] = new_id
            self._state["artifact_registry"]["id_to_path"][new_id] = name
            return new_id

        return None

    def list_modules(self) -> list[str]:
        return list(
            self._state["module_registry"]["path_to_id"].keys()
        )

    def get_module_path(self, obj_id: str) -> Optional[str]:
        path = self._state["module_registry"]["id_to_path"].get(obj_id)

        if path:
            return path

        rec = self._state["module_recovery"].get(obj_id)

        if rec:
            return rec.get("path")

        return None

    def get_artifact_name(self, obj_id: str) -> Optional[str]:
        name = self._state["artifact_registry"]["id_to_path"].get(obj_id)

        if name:
            return name

        rec = self._state["artifact_recovery"].get(obj_id)

        if rec:
            return rec.get("name")

        return None

    def sync_with_workspace(
        self,
        current_modules: Set[str],
        current_artifacts: Set[str],
    ):
        """Sync active workspace items, handle orphans, and restore if needed."""
        self._sync_kind("module", current_modules)
        self._sync_kind("artifact", current_artifacts)

    def _sync_kind(
        self,
        kind: str,
        current_items: Set[str],
    ):
        registry = self._state[f"{kind}_registry"]
        recovery = self._state[f"{kind}_recovery"]

        active_paths = list(
            registry["path_to_id"].keys()
        )

        for path in active_paths:
            if path not in current_items:
                obj_id = registry["path_to_id"][path]

                recovery[obj_id] = {
                    "type": kind,
                    "path" if kind == "module" else "name": path,
                    "removed_at": datetime.datetime.now().isoformat(),
                    "status": "orphan",
                }

                del registry["path_to_id"][path]
                del registry["id_to_path"][obj_id]

        for path in current_items:
            if path not in registry["path_to_id"]:
                restored_id = None

                for rec_id, rec_data in list(recovery.items()):
                    if rec_id == "schema_version":
                        continue

                    if rec_data.get(
                        "path" if kind == "module" else "name"
                    ) == path:
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

    def register_report_references(
        self,
        report_name: str,
        used_ids: List[str],
    ):
        refs = self._state["output_references"]

        self.unregister_report_references(report_name)

        refs["report_to_ids"][report_name] = list(set(used_ids))

        for obj_id in used_ids:
            if obj_id not in refs["id_to_reports"]:
                refs["id_to_reports"][obj_id] = []

            if report_name not in refs["id_to_reports"][obj_id]:
                refs["id_to_reports"][obj_id].append(report_name)

    def unregister_report_references(self, report_name: str):
        refs = self._state["output_references"]

        if report_name in refs["report_to_ids"]:
            used_ids = refs["report_to_ids"][report_name]

            for obj_id in used_ids:
                if obj_id in refs["id_to_reports"]:
                    try:
                        refs["id_to_reports"][obj_id].remove(report_name)

                        if not refs["id_to_reports"][obj_id]:
                            del refs["id_to_reports"][obj_id]

                    except ValueError:
                        pass

            del refs["report_to_ids"][report_name]

    def run_garbage_collector(
        self,
        max_module_recovery_bytes: int = 250 * 1024,
        max_artifact_recovery_bytes: int = 100 * 1024,
    ):
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
    ):
        recovery = self._state[f"{kind}_recovery"]

        current_size = len(
            json.dumps(recovery).encode("utf-8")
        )

        if current_size <= max_bytes:
            return

        refs = self._state["output_references"]["id_to_reports"]

        def get_date(item):
            return item[1].get(
                "removed_at",
                "1970-01-01",
            )

        sorted_orphans = sorted(
            [
                (k, v)
                for k, v in recovery.items()
                if k != "schema_version"
            ],
            key=get_date,
        )

        for obj_id, _ in sorted_orphans:
            if obj_id in refs and len(refs[obj_id]) > 0:
                continue

            del recovery[obj_id]

            current_size = len(
                json.dumps(recovery).encode("utf-8")
            )

            if current_size <= max_bytes:
                break
