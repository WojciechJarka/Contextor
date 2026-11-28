from __future__ import annotations

import json
import os
import stat
from types import SimpleNamespace

import pytest

from contextor.core.registry_migration_inventory import (
    REGISTRY_JSON_FILES,
    RegistryMigrationError,
    _assert_plain_directory_path,
    inspect_registry_for_migration,
)


def _registry(tmp_path):
    root = tmp_path / "source"
    root.mkdir()

    directory = tmp_path / "registry" / "source__ctx_test"
    directory.mkdir(parents=True)

    for name in REGISTRY_JSON_FILES:
        payload = {"schema_version": 1}

        if name == "repo.meta.json":
            payload.update({
                "repo_id": "ctx_test",
                "repo_name": root.name,
                "root_path": str(root.resolve()),
            })

        if name.endswith("_registry.json"):
            payload.update({
                "path_to_id": {},
                "id_to_path": {},
            })

        (directory / name).write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    return root, directory


def test_inventory_preserves_identity(tmp_path):
    root, directory = _registry(tmp_path)

    result = inspect_registry_for_migration(
        root, directory
    )

    assert result.identity.repo_id == "ctx_test"
    assert result.identity.root_path == str(root.resolve())
    assert {item.name for item in result.files} == (
        REGISTRY_JSON_FILES
    )
    assert all(len(item.sha256) == 64 for item in result.files)


def test_missing_file_rejected(tmp_path):
    root, directory = _registry(tmp_path)
    (directory / "module_registry.json").unlink()

    with pytest.raises(
        RegistryMigrationError,
        match="missing required files",
    ):
        inspect_registry_for_migration(root, directory)


def test_pending_transaction_rejected(tmp_path):
    root, directory = _registry(tmp_path)
    (directory / "transaction.tmp").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        RegistryMigrationError,
        match="unfinished transaction",
    ):
        inspect_registry_for_migration(root, directory)


def test_invalid_identity_rejected(tmp_path):
    root, directory = _registry(tmp_path)
    meta = directory / "repo.meta.json"
    payload = json.loads(meta.read_text(encoding="utf-8"))
    payload["root_path"] = str(tmp_path / "other")
    meta.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        RegistryMigrationError,
        match="identity is inconsistent",
    ):
        inspect_registry_for_migration(root, directory)


def test_inconsistent_mapping_rejected(tmp_path):
    root, directory = _registry(tmp_path)
    target = directory / "module_registry.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["path_to_id"] = {"example.py": "1/1"}
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        RegistryMigrationError,
        match="Inconsistent module registry mappings",
    ):
        inspect_registry_for_migration(root, directory)


def test_inventory_does_not_modify_files(tmp_path):
    root, directory = _registry(tmp_path)

    before = {
        file.name: file.read_bytes()
        for file in directory.iterdir()
    }

    inspect_registry_for_migration(root, directory)

    after = {
        file.name: file.read_bytes()
        for file in directory.iterdir()
    }

    assert after == before


def test_lexical_parent_traversal_rejected(tmp_path):
    with pytest.raises(
        RegistryMigrationError,
        match="parent traversal",
    ):
        _assert_plain_directory_path(
            tmp_path / "something" / ".." / "registry"
        )


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows junction and reparse-point semantics",
)
def test_junction_or_reparse_component_rejected(
    tmp_path,
    monkeypatch,
):
    root, directory = _registry(tmp_path)
    original_lstat = type(directory).lstat

    def flagged_lstat(self, *args, **kwargs):
        result = original_lstat(self, *args, **kwargs)

        if self == directory.parent:
            return SimpleNamespace(
                st_mode=result.st_mode,
                st_file_attributes=(
                    getattr(result, "st_file_attributes", 0)
                    | stat.FILE_ATTRIBUTE_REPARSE_POINT
                ),
            )

        return result

    monkeypatch.setattr(
        type(directory),
        "lstat",
        flagged_lstat,
    )

    with pytest.raises(
        RegistryMigrationError,
        match="reparse point",
    ):
        _assert_plain_directory_path(directory)


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows junction semantics",
)
def test_actual_junction_rejected(tmp_path):
    import subprocess

    root, directory = _registry(tmp_path)
    junction = tmp_path / "source__ctx_test"

    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(directory)],
        check=True,
        capture_output=True,
        text=True,
    )

    try:
        assert junction.is_dir()
        assert junction.is_junction()

        with pytest.raises(
            RegistryMigrationError,
            match="reparse point",
        ):
            inspect_registry_for_migration(root, junction)
    finally:
        if junction.exists():
            junction.rmdir()
