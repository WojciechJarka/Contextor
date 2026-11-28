# P17-F3-I4-I1 — prevent unsafe repository cache deletion

## FILES_CHANGED

- `contextor/core/paths.py`
- `tests/test_paths_and_cache.py`

## TESTS

- `.venv/Scripts/python.exe -m pytest -q tests/test_paths_and_cache.py`: **12 passed in 1.20s**.
- Brak innych testów bezpośrednio wywołujących `prune_startup_caches()` lub `prune_orphaned_repository_caches()` poza wskazanym plikiem.
- `git diff --check` dla obu plików: bez błędów whitespace.

## WERYFIKACJA

- Startup zachowuje repo-ID cache przy pustym registry root; test z izolowanym cache przeszedł.
- `prune_orphaned_repository_caches()` nadal zwraca słownik `{"removed": [], "errors": []}`.
- `prune_startup_caches()` i pozostałe funkcje cleanup nie zostały zmienione.
- Nie dodano zależności ani wyjątków dla konkretnych repozytoriów.
- W drzewie roboczym istnieją wcześniejsze, niezwiązane zmiany w plikach I3-R2; nie były częścią tego zadania.

## VERDICT

I4_I1_PASS — automatyczny startup nie usuwa repo-ID cache na podstawie braku identity; celowane testy przeszły.

## FULL_DIFFS

### contextor/core/paths.py

```diff
diff --git a/contextor/core/paths.py b/contextor/core/paths.py
index 4bf3fba..a7d8e78 100644
--- a/contextor/core/paths.py
+++ b/contextor/core/paths.py
@@ -205,31 +205,16 @@ def legacy_repo_cache_dir(root_path: str | Path) -> Path:
 
 
 def prune_orphaned_repository_caches() -> dict[str, list[str]]:
-    """Remove repo-ID caches that no longer have a central identity record."""
+    """Preserve repo-ID caches when registry authority is uncertain.
 
-    from contextor.core.repository_identity import registered_repository_ids
+    Absence of an identity entry does not establish that its cache
+    is disposable. Registry migration, unavailable storage or a
+    temporarily incomplete registry can all produce missing IDs.
 
-    cache_root = app_cache_dir() / "repositories"
-    result = {"removed": [], "errors": []}
-    if not cache_root.is_dir():
-        return result
-    registered = registered_repository_ids()
-    resolved_root = cache_root.resolve()
-    for candidate in cache_root.iterdir():
-        if not candidate.is_dir() or not candidate.name.startswith("ctx_"):
-            continue
-        if candidate.name in registered:
-            continue
-        resolved_candidate = candidate.resolve()
-        if resolved_candidate.parent != resolved_root:
-            result["errors"].append(f"unsafe cache path: {resolved_candidate}")
-            continue
-        try:
-            shutil.rmtree(resolved_candidate)
-            result["removed"].append(candidate.name)
-        except OSError as exc:
-            result["errors"].append(f"{candidate.name}: {exc}")
-    return result
+    Destructive cleanup requires a separate, explicit authority
+    contract and must not run as an automatic startup operation.
+    """
+    return {"removed": [], "errors": []}
 
 
 _TEST_CACHE_DIRECTORY = re.compile(
```

### tests/test_paths_and_cache.py

```diff
diff --git a/tests/test_paths_and_cache.py b/tests/test_paths_and_cache.py
index 97483fa..df28c19 100644
--- a/tests/test_paths_and_cache.py
+++ b/tests/test_paths_and_cache.py
@@ -55,28 +55,67 @@ def test_registered_repo_cache_is_keyed_by_durable_repo_id(tmp_path, monkeypatch
     assert repo_cache_dir(repo) != legacy
 
 
-def test_orphaned_repo_id_cache_is_removed_but_registered_and_unrelated_remain(
+def test_repository_caches_are_preserved_without_deletion_authority(
     tmp_path, monkeypatch
 ):
     cache_root = tmp_path / "cache"
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+
     repo = tmp_path / "repo"
     repo.mkdir()
     registry = PersistentIdentityRegistry(str(repo))
+
     repositories = cache_root / "repositories"
     valid = repositories / registry.repo_id
     orphan = repositories / "ctx_orphaned"
     unrelated = repositories / "legacy-path-cache"
+
     for directory in (valid, orphan, unrelated):
         directory.mkdir(parents=True)
-        (directory / "marker.txt").write_text("keep?", encoding="utf-8")
+        (directory / "marker.txt").write_text(
+            "preserve", encoding="utf-8"
+        )
 
     result = prune_orphaned_repository_caches()
 
-    assert result == {"removed": ["ctx_orphaned"], "errors": []}
-    assert valid.is_dir()
-    assert unrelated.is_dir()
-    assert not orphan.exists()
+    assert result == {"removed": [], "errors": []}
+    assert all(
+        (directory / "marker.txt").read_text(
+            encoding="utf-8"
+        ) == "preserve"
+        for directory in (valid, orphan, unrelated)
+    )
+
+
+def test_startup_preserves_repo_id_cache_when_registry_is_empty(
+    tmp_path, monkeypatch
+):
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    monkeypatch.setenv(
+        "CONTEXTOR_REGISTRY_DIR",
+        str(tmp_path / "empty-registry"),
+    )
+
+    repositories = cache_root / "repositories"
+    committed = repositories / "ctx_existing"
+    committed.mkdir(parents=True)
+
+    metadata = committed / "engine_state.meta.json"
+    metadata.write_text(
+        '{"state_id":"existing"}',
+        encoding="utf-8",
+    )
+
+    result = prune_startup_caches()
+
+    assert result["orphaned_repository_caches"] == {
+        "removed": [],
+        "errors": [],
+    }
+    assert metadata.read_text(encoding="utf-8") == (
+        '{"state_id":"existing"}'
+    )
 
 
 def test_startup_cleanup_removes_only_pytest_cache_directories(tmp_path, monkeypatch):
```
