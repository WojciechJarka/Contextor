# SP-T4-I2B5-I4B-T66 — evidence przy no-op

## PREFLIGHT

- **DIRECT_EVIDENCE:** HEAD przed zmianą: `9fef807afccd21df3f07b64c1582f2036adf37fb`; working tree był czysty, a plik testowy nie miał diffu.
- **DIRECT_EVIDENCE:** CPython `.venv\Scripts\python.exe` ma wersję 3.15.2.
- **DIRECT_EVIDENCE:** Contextor MCP przed zmianą raportował revision `1449`, `provenance=live`, `canonical_state=fresh`, `workspace_sync=verified` dla `engine.py` i pliku testowego; syntax errors=0, graph/cycles fresh, cycles=16, `cycle_semantics=stale`, `resync_required=false`.
- **DIRECT_EVIDENCE:** koniec testowego źródła zajmował linie 4750–4792 i kończył się T65. T66 nie występował; dokładna nazwa nowego testu nie miała trafień.
- **CODE_PATH_PROVED:** aktualny no-op branch `update_file` wywołuje `_commit_syntax_candidate`, aktualizuje fingerprint w `state_manager`, po czym zwraca status `UNCHANGED`. `_commit_syntax_candidate` publikuje `self.state.typing_guard_evidence = {}`. Ten przepływ wyjaśnia oczekiwany czerwony witness bez modyfikowania produkcji.
- **SEMANTIC CHECK:** dopisanie komentarza nie zmienia wykonywanej treści Python, ale zmienia fingerprint źródła. Test sprawdza ograniczony kontrakt: no-op zachowuje tożsamość modułów i grafu, a evidence aktualizuje fingerprint w nowym Copy-on-Write mappingu. Nie generalizuje tego jednego przypadku na wszystkie możliwe semantyczne no-op.

## CHANGE

- Dopisano na końcu pliku dokładnie jeden test `test_sp_t4_i2b5_i4b_t66_noop_evidence_refresh`, zgodnie z podanym ciałem.
- Nie zmieniono produkcji, pozostałych testów, helperów ani monkeypatchy.

## TARGETED TEST

Uruchomiono wyłącznie T66:

```text
& .\.venv\Scripts\python.exe -m pytest -q --tb=long tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t66_noop_evidence_refresh
```

Pełny wynik:

```text
F                                                                        [100%]
================================== FAILURES ===================================
________________ test_sp_t4_i2b5_i4b_t66_noop_evidence_refresh ________________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1285/test_sp_t4_i2b5_i4b_t66_noop_e0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-1285/test_sp_t4_i2b5_i4b_t66_noop_e0')

    def test_sp_t4_i2b5_i4b_t66_noop_evidence_refresh(
        tmp_path, isolated_dirs,
    ):
        root = write_synthetic_repository(
            tmp_path / "repo", _I1_SAFE
        )
        _, engine = _i1_full_engine(root)
    
        before_modules = engine.state.modules
        before_evidence = engine.state.typing_guard_evidence
        before_graph = engine.state.dependency_graph
    
        assert before_evidence["schema_version"] == 2
        assert before_evidence[
            "global_policy_satisfied"
        ] is True
    
        before_fingerprint = before_evidence[
            "source_fingerprints_by_module"
        ]["pkg.c"]
    
        target = root / "pkg/c.py"
        with target.open("a", encoding="utf-8") as stream:
            stream.write("\n# unrelated comment\n")
    
        result = engine.update_file(str(target.resolve()))
    
        assert result.status == "UNCHANGED"
    
        after_evidence = engine.state.typing_guard_evidence
    
>       assert after_evidence["schema_version"] == 2
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'schema_version'

tests\test_p1d3_d2b2_type_only.py:4825: KeyError
=========================== short test summary info ============================
FAILED tests/test_p1d3_d2b2_type_only.py::test_sp_t4_i2b5_i4b_t66_noop_evidence_refresh
1 failed in 4.26s
```

- **DIRECT_EVIDENCE:** awaria nastąpiła przy odczycie `after_evidence["schema_version"]` po `assert result.status == "UNCHANGED"`. Zatem faktyczny status zwrócony przez `update_file` w tym przebiegu to `UNCHANGED`.
- **CODE_PATH_PROVED:** traceback potwierdza, że po no-op `typing_guard_evidence` nie zawiera klucza `schema_version`; źródło `_commit_syntax_candidate` wskazuje, że jest ono zerowane do `{}`.
- Test zakończył się oczekiwanym FAIL; zgodnie z poleceniem nie wykonywano poprawek.

## MCP POST-CHANGE AUDIT

- **DIRECT_EVIDENCE:** event `desktop_watcher`, `operation=update_file`, `status=UPDATED` dla `tests/test_p1d3_d2b2_type_only.py`, revision `1450`; `continuity=continuous`, `resync_required=false`, `resync_reason=null`; `blast_radius_state=deferred`, `affected_modules.total=0`.
- **DIRECT_EVIDENCE:** MCP pobrał pełny T66 z `workspace_sync=verified`, `canonical_state=fresh`, `provenance=live`, revision `1450`.
- **DIRECT_EVIDENCE:** syntax diagnostics=0/fresh; graph/module/topology/artifact-consumption/cycles/collisions/lineage families fresh; cycles=16/fresh; cycle warning view fresh. `cycle_semantics=stale`.
- **LIMITATION:** synchronizacja źródła przez watcher nie jest dowodem adopcji kodu przez proces; tu zmieniono wyłącznie test. Restartu nie wykonywano.

## FINAL VERDICT

**T66_FAIL_REPRODUCED** — test został dodany dokładnie w wymaganym zakresie; ujawnia brak odświeżenia evidence w no-op branch. Brak zmian produkcyjnych.

## FILES_CHANGED

- `tests/test_p1d3_d2b2_type_only.py` — jedyny zmieniony plik testowy.
- `walkthrough.md` — wymagany raport, bez własnego diffu.

## FULL_DIFFS

### `tests/test_p1d3_d2b2_type_only.py`

```diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index c53f911..09eabef 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4790,3 +4790,57 @@ def test_sp_t4_i2b5_i4b_t65_invalid_baseline_fails_closed(
         .soft_edges["pkg.a"]
     )
 
+
+def test_sp_t4_i2b5_i4b_t66_noop_evidence_refresh(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    _, engine = _i1_full_engine(root)
+
+    before_modules = engine.state.modules
+    before_evidence = engine.state.typing_guard_evidence
+    before_graph = engine.state.dependency_graph
+
+    assert before_evidence["schema_version"] == 2
+    assert before_evidence[
+        "global_policy_satisfied"
+    ] is True
+
+    before_fingerprint = before_evidence[
+        "source_fingerprints_by_module"
+    ]["pkg.c"]
+
+    target = root / "pkg/c.py"
+    with target.open("a", encoding="utf-8") as stream:
+        stream.write("\n# unrelated comment\n")
+
+    result = engine.update_file(str(target.resolve()))
+
+    assert result.status == "UNCHANGED"
+
+    after_evidence = engine.state.typing_guard_evidence
+
+    assert after_evidence["schema_version"] == 2
+    assert after_evidence[
+        "global_policy_satisfied"
+    ] is True
+
+    assert after_evidence[
+        "source_fingerprints_by_module"
+    ]["pkg.c"] != before_fingerprint
+
+    assert after_evidence is not before_evidence
+
+    assert before_evidence[
+        "source_fingerprints_by_module"
+    ]["pkg.c"] == before_fingerprint
+
+    assert engine.state.modules is before_modules
+    assert engine.state.dependency_graph is before_graph
+
+    assert _i1_guarded_import(
+        engine.state
+    ).type_only is True
+
```
