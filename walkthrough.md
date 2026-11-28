# P17-F3-I3-R1 — read-only registry inventory

## Wynik

- Dodano `contextor/core/registry_migration_inventory.py`: odczytowy inwentarz plików rejestru, kontrola typów i spójności danych oraz odrzucanie komponentów ścieżki z flagą reparse point.
- Dodano `tests/test_registry_migration_inventory.py`: dziewięć celowanych testów, w tym test rzeczywistej Windows junction.
- `.venv/Scripts/python.exe -m pytest -q tests/test_registry_migration_inventory.py`: **9 passed in 0.92s**.
- Parsowanie AST obu nowych plików: **OK**.
- Rzeczywista junction została utworzona w katalogu tymczasowym i odrzucona przez `inspect_registry_for_migration` (test przeszedł).

## Granice dowodu

- Inwentarz jest obserwacją tylko do odczytu. Nie stanowi autoryzacji migracji, dowodu historycznej autentyczności identity ani atomowej ochrony przed podmianą ścieżki podczas odczytu.
- Testy potwierdzają kontrakt na izolowanych fixture, nie stan aktywnego rejestru.

## FILES_CHANGED

- `contextor/core/registry_migration_inventory.py`
- `tests/test_registry_migration_inventory.py`

## Werdykt

I3_PASS — dosłowna implementacja R1, celowane testy i kontrola składni przeszły.

## FULL_DIFFS

### contextor/core/registry_migration_inventory.py

```diff
diff --git a/contextor/core/registry_migration_inventory.py b/contextor/core/registry_migration_inventory.py
new file mode 100644
index 0000000..f5de519
--- /dev/null
+++ b/contextor/core/registry_migration_inventory.py
@@ -0,0 +1,297 @@
+from __future__ import annotations
+
+import hashlib
+import json
+import os
+import stat
+from dataclasses import dataclass
+from pathlib import Path
+
+from contextor.core.repository_identity import (
+    RepositoryIdentity,
+    RepositoryIdentityError,
+    _identity_from_meta,
+)
+
+
+class RegistryMigrationError(RuntimeError):
+    """Registry cannot be inventoried for migration."""
+
+
+@dataclass(frozen=True)
+class RegistryFileEvidence:
+    name: str
+    sha256: str
+    size: int
+
+
+@dataclass(frozen=True)
+class RegistryMigrationInventory:
+    identity: RepositoryIdentity
+    directory: Path
+    files: tuple[RegistryFileEvidence, ...]
+
+
+REGISTRY_JSON_FILES = frozenset({
+    "repo.meta.json",
+    "module_slots.json",
+    "artifact_slots.json",
+    "module_recovery.json",
+    "artifact_recovery.json",
+    "output_references.json",
+    "module_registry.json",
+    "artifact_registry.json",
+})
+
+
+def _assert_plain_directory_path(path: str | Path) -> Path:
+    """
+    Reject existing path components that are links or
+    Windows reparse points before following the path.
+
+    This is a read-only observation, not an atomic
+    filesystem security boundary.
+    """
+    supplied = Path(path).expanduser()
+
+    if ".." in supplied.parts:
+        raise RegistryMigrationError(
+            "Registry path contains parent traversal"
+        )
+
+    directory = Path(os.path.abspath(supplied))
+    components = tuple(
+        reversed((directory, *directory.parents))
+    )
+
+    for component in components:
+        try:
+            info = component.lstat()
+        except OSError as exc:
+            raise RegistryMigrationError(
+                f"Registry path component is inaccessible: "
+                f"{component}"
+            ) from exc
+
+        if stat.S_ISLNK(info.st_mode):
+            raise RegistryMigrationError(
+                f"Registry path contains a symbolic link: "
+                f"{component}"
+            )
+
+        if os.name == "nt" and (
+            getattr(info, "st_file_attributes", 0)
+            & stat.FILE_ATTRIBUTE_REPARSE_POINT
+        ):
+            raise RegistryMigrationError(
+                f"Registry path contains a reparse point: "
+                f"{component}"
+            )
+
+        if not stat.S_ISDIR(info.st_mode):
+            raise RegistryMigrationError(
+                f"Registry path component is not a directory: "
+                f"{component}"
+            )
+
+    return directory
+
+
+def _read_stable_file(path: Path) -> bytes:
+    before = path.stat(follow_symlinks=False)
+
+    if not stat.S_ISREG(before.st_mode):
+        raise RegistryMigrationError(
+            f"Not a regular registry file: {path.name}"
+        )
+
+    if os.name == "nt" and (
+        getattr(before, "st_file_attributes", 0)
+        & stat.FILE_ATTRIBUTE_REPARSE_POINT
+    ):
+        raise RegistryMigrationError(
+            f"Registry file is a reparse point: {path.name}"
+        )
+
+    with path.open("rb") as stream:
+        data = stream.read()
+
+    after = path.stat(follow_symlinks=False)
+
+    def file_identity(info):
+        return (
+            info.st_dev,
+            info.st_ino,
+            info.st_size,
+            info.st_mtime_ns,
+            info.st_ctime_ns,
+        )
+
+    if file_identity(before) != file_identity(after):
+        raise RegistryMigrationError(
+            f"Registry file changed during read: {path.name}"
+        )
+
+    if len(data) != after.st_size:
+        raise RegistryMigrationError(
+            f"Registry file size changed: {path.name}"
+        )
+
+    return data
+
+
+def inspect_registry_for_migration(
+    repo_root: str | Path,
+    registry_directory: str | Path,
+) -> RegistryMigrationInventory:
+    """
+    Read-only migration inventory.
+
+    Does not authorize migration or prove historical
+    authenticity. Does not provide race-free access.
+    """
+    root = Path(repo_root).expanduser().resolve()
+
+    try:
+        directory = _assert_plain_directory_path(
+            registry_directory
+        )
+
+        entries = tuple(directory.iterdir())
+        names = {entry.name for entry in entries}
+
+        if len(entries) != len(names):
+            raise RegistryMigrationError(
+                "Duplicate registry entries"
+            )
+
+        if (
+            "transaction.tmp" in names
+            or any(name.endswith(".json.tmp") for name in names)
+        ):
+            raise RegistryMigrationError(
+                "Registry contains an unfinished transaction"
+            )
+
+        if not REGISTRY_JSON_FILES <= names:
+            raise RegistryMigrationError(
+                "Registry is missing required files"
+            )
+
+        unexpected = names - REGISTRY_JSON_FILES - {".lock"}
+        if unexpected:
+            raise RegistryMigrationError(
+                "Registry contains unexpected files"
+            )
+
+        for entry in entries:
+            info = entry.lstat()
+
+            if not stat.S_ISREG(info.st_mode):
+                raise RegistryMigrationError(
+                    f"Unexpected registry entry type: {entry.name}"
+                )
+
+            if os.name == "nt" and (
+                getattr(info, "st_file_attributes", 0)
+                & stat.FILE_ATTRIBUTE_REPARSE_POINT
+            ):
+                raise RegistryMigrationError(
+                    f"Registry entry is a reparse point: "
+                    f"{entry.name}"
+                )
+
+        evidence = []
+        payloads = {}
+
+        for name in sorted(REGISTRY_JSON_FILES):
+            data = _read_stable_file(directory / name)
+
+            try:
+                payload = json.loads(data)
+            except (UnicodeDecodeError, ValueError) as exc:
+                raise RegistryMigrationError(
+                    f"Malformed registry JSON: {name}"
+                ) from exc
+
+            if not isinstance(payload, dict):
+                raise RegistryMigrationError(
+                    f"Registry JSON is not an object: {name}"
+                )
+
+            payloads[name] = payload
+            evidence.append(
+                RegistryFileEvidence(
+                    name=name,
+                    sha256=hashlib.sha256(data).hexdigest(),
+                    size=len(data),
+                )
+            )
+
+        try:
+            identity = _identity_from_meta(
+                directory / "repo.meta.json",
+                root,
+            )
+        except RepositoryIdentityError as exc:
+            raise RegistryMigrationError(
+                "Repository identity is inconsistent"
+            ) from exc
+
+        for kind in ("module", "artifact"):
+            registry = payloads[f"{kind}_registry.json"]
+            forward = registry.get("path_to_id")
+            reverse = registry.get("id_to_path")
+
+            if not isinstance(forward, dict) or not isinstance(
+                reverse, dict
+            ):
+                raise RegistryMigrationError(
+                    f"Invalid {kind} registry mappings"
+                )
+
+            if (
+                len(set(forward.values())) != len(forward)
+                or len(forward) != len(reverse)
+                or any(
+                    reverse.get(identifier) != name
+                    for name, identifier in forward.items()
+                )
+            ):
+                raise RegistryMigrationError(
+                    f"Inconsistent {kind} registry mappings"
+                )
+
+        for item in evidence:
+            current = _read_stable_file(
+                directory / item.name
+            )
+            if (
+                len(current) != item.size
+                or hashlib.sha256(current).hexdigest()
+                != item.sha256
+            ):
+                raise RegistryMigrationError(
+                    f"Registry changed during inventory: "
+                    f"{item.name}"
+                )
+
+        if {entry.name for entry in directory.iterdir()} != names:
+            raise RegistryMigrationError(
+                "Registry entries changed during inventory"
+            )
+
+        _assert_plain_directory_path(registry_directory)
+
+        return RegistryMigrationInventory(
+            identity=identity,
+            directory=directory,
+            files=tuple(evidence),
+        )
+
+    except RegistryMigrationError:
+        raise
+    except (OSError, ValueError, TypeError) as exc:
+        raise RegistryMigrationError(
+            "Cannot inspect registry for migration"
+        ) from exc
```

### tests/test_registry_migration_inventory.py

```diff
diff --git a/tests/test_registry_migration_inventory.py b/tests/test_registry_migration_inventory.py
new file mode 100644
index 0000000..b8ef693
--- /dev/null
+++ b/tests/test_registry_migration_inventory.py
@@ -0,0 +1,211 @@
+from __future__ import annotations
+
+import json
+import os
+import stat
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.registry_migration_inventory import (
+    REGISTRY_JSON_FILES,
+    RegistryMigrationError,
+    _assert_plain_directory_path,
+    inspect_registry_for_migration,
+)
+
+
+def _registry(tmp_path):
+    root = tmp_path / "source"
+    root.mkdir()
+
+    directory = tmp_path / "registry" / "source__ctx_test"
+    directory.mkdir(parents=True)
+
+    for name in REGISTRY_JSON_FILES:
+        payload = {"schema_version": 1}
+
+        if name == "repo.meta.json":
+            payload.update({
+                "repo_id": "ctx_test",
+                "repo_name": root.name,
+                "root_path": str(root.resolve()),
+            })
+
+        if name.endswith("_registry.json"):
+            payload.update({
+                "path_to_id": {},
+                "id_to_path": {},
+            })
+
+        (directory / name).write_text(
+            json.dumps(payload),
+            encoding="utf-8",
+        )
+
+    return root, directory
+
+
+def test_inventory_preserves_identity(tmp_path):
+    root, directory = _registry(tmp_path)
+
+    result = inspect_registry_for_migration(
+        root, directory
+    )
+
+    assert result.identity.repo_id == "ctx_test"
+    assert result.identity.root_path == str(root.resolve())
+    assert {item.name for item in result.files} == (
+        REGISTRY_JSON_FILES
+    )
+    assert all(len(item.sha256) == 64 for item in result.files)
+
+
+def test_missing_file_rejected(tmp_path):
+    root, directory = _registry(tmp_path)
+    (directory / "module_registry.json").unlink()
+
+    with pytest.raises(
+        RegistryMigrationError,
+        match="missing required files",
+    ):
+        inspect_registry_for_migration(root, directory)
+
+
+def test_pending_transaction_rejected(tmp_path):
+    root, directory = _registry(tmp_path)
+    (directory / "transaction.tmp").write_text(
+        "{}",
+        encoding="utf-8",
+    )
+
+    with pytest.raises(
+        RegistryMigrationError,
+        match="unfinished transaction",
+    ):
+        inspect_registry_for_migration(root, directory)
+
+
+def test_invalid_identity_rejected(tmp_path):
+    root, directory = _registry(tmp_path)
+    meta = directory / "repo.meta.json"
+    payload = json.loads(meta.read_text(encoding="utf-8"))
+    payload["root_path"] = str(tmp_path / "other")
+    meta.write_text(json.dumps(payload), encoding="utf-8")
+
+    with pytest.raises(
+        RegistryMigrationError,
+        match="identity is inconsistent",
+    ):
+        inspect_registry_for_migration(root, directory)
+
+
+def test_inconsistent_mapping_rejected(tmp_path):
+    root, directory = _registry(tmp_path)
+    target = directory / "module_registry.json"
+    payload = json.loads(target.read_text(encoding="utf-8"))
+    payload["path_to_id"] = {"example.py": "1/1"}
+    target.write_text(json.dumps(payload), encoding="utf-8")
+
+    with pytest.raises(
+        RegistryMigrationError,
+        match="Inconsistent module registry mappings",
+    ):
+        inspect_registry_for_migration(root, directory)
+
+
+def test_inventory_does_not_modify_files(tmp_path):
+    root, directory = _registry(tmp_path)
+
+    before = {
+        file.name: file.read_bytes()
+        for file in directory.iterdir()
+    }
+
+    inspect_registry_for_migration(root, directory)
+
+    after = {
+        file.name: file.read_bytes()
+        for file in directory.iterdir()
+    }
+
+    assert after == before
+
+
+def test_lexical_parent_traversal_rejected(tmp_path):
+    with pytest.raises(
+        RegistryMigrationError,
+        match="parent traversal",
+    ):
+        _assert_plain_directory_path(
+            tmp_path / "something" / ".." / "registry"
+        )
+
+
+@pytest.mark.skipif(
+    os.name != "nt",
+    reason="Windows junction and reparse-point semantics",
+)
+def test_junction_or_reparse_component_rejected(
+    tmp_path,
+    monkeypatch,
+):
+    root, directory = _registry(tmp_path)
+    original_lstat = type(directory).lstat
+
+    def flagged_lstat(self, *args, **kwargs):
+        result = original_lstat(self, *args, **kwargs)
+
+        if self == directory.parent:
+            return SimpleNamespace(
+                st_mode=result.st_mode,
+                st_file_attributes=(
+                    getattr(result, "st_file_attributes", 0)
+                    | stat.FILE_ATTRIBUTE_REPARSE_POINT
+                ),
+            )
+
+        return result
+
+    monkeypatch.setattr(
+        type(directory),
+        "lstat",
+        flagged_lstat,
+    )
+
+    with pytest.raises(
+        RegistryMigrationError,
+        match="reparse point",
+    ):
+        _assert_plain_directory_path(directory)
+
+
+@pytest.mark.skipif(
+    os.name != "nt",
+    reason="Windows junction semantics",
+)
+def test_actual_junction_rejected(tmp_path):
+    import subprocess
+
+    root, directory = _registry(tmp_path)
+    junction = tmp_path / "source__ctx_test"
+
+    subprocess.run(
+        ["cmd", "/c", "mklink", "/J", str(junction), str(directory)],
+        check=True,
+        capture_output=True,
+        text=True,
+    )
+
+    try:
+        assert junction.is_dir()
+        assert junction.is_junction()
+
+        with pytest.raises(
+            RegistryMigrationError,
+            match="reparse point",
+        ):
+            inspect_registry_for_migration(root, junction)
+    finally:
+        if junction.exists():
+            junction.rmdir()
```
