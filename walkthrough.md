# SP-T4-I2B3 — SHARED TYPE_ONLY POLICY EXTRACTION

Audyt i implementacja: 2026-11-16. Zakres obejmował wyłącznie wydzielenie istniejącej klasyfikacji, wskazane testy i ten raport.

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP przed zmianą wskazywał revision 1422. Canonical state był fresh, `resync_required=false`, a `syntax_errors=0` i fresh. HEAD przed zmianą: `ad7f13ff5846cfbc0937aee61c788515554c2489`; status roboczy był czysty.
- Przed edycją potwierdzono `indexer.py` i `tests/test_p1d3_d2b2_type_only.py` jako pliki w zakresie. Anchory kodu: `_project_typing_imports_closed` 559, `_classify_type_only_modules` 647–779, `read_imports` 782, lokalny finalizer 2784, jego wywołania w ścieżce inline 2880 i process-pool 3134.
- Zmiana kodu i testów ograniczyła się do `contextor/core/symbol_engine/indexer.py` oraz `tests/test_p1d3_d2b2_type_only.py`. Nie zmieniono grafu, planera, incremental engine, state manager, issues.md ani Spiral Prophet.

## MECHANICAL EXTRACTION

- DIRECT_EVIDENCE: Porównanie starego finalizatora z HEAD `ad7f13f` i aktualnej implementacji potwierdza przeniesienie istniejących reguł bez zmiany ich kolejności ani warunków. Jedyna wskazana adaptacja to `not skipped` → `not skipped_source_paths`; finalizer przekazuje `tuple(item.path for item in skipped)`, więc bramka nadal rozróżnia pusty i niepusty zbiór pominiętych plików.
- Nowa funkcja w `indexer.py:647–779` zachowuje: `typing_shadowed`; kompletność i zgodność fingerprintów `project_marker_safe`; bramki `project_effects_closed`; koniunkcję `global_policy_satisfied`; per-module `parents_proved`; pozostawienie kandydatury przy obu pozytywnych wynikach; cofnięcie `type_only=True` do `False` w przeciwnym przypadku.
- Funkcja zaczyna od `classified = dict(modules)`. Moduły wymagające cofnięcia flagi są tworzone przez `dataclasses.replace`; dla ich importów tworzony jest nowy `ImportRef` wyłącznie dla `type_only=True`. Nie ma odczytu plików, parsowania AST, wykonania analizowanego kodu ani tworzenia/przeliczania grafu w tej funkcji.
- Finalizer nadal zapisuje `candidate_imports_by_module` przed klasyfikacją (`indexer.py:2784–2799`), wywołuje funkcję (`2800–2825`) i aplikuje zwróconą mapę przez `modules.update(classified)` (`2826`). Schema evidence v2 i oba wejścia do finalizatora pozostały bez zmian.

## SHARED POLICY CONTRACT

- CODE_PATH_PROVED: Ten sam finalizer jest wywoływany na ścieżce inline (`indexer.py:2880`) i process-pool (`3134`); obie ścieżki więc używają wydzielonego helpera.
- DIRECT_EVIDENCE: MCP `get_source_range` dla zakresów `indexer.py:559–765` i `2760–2935` pokazał aktualne reguły, zachowany capture przed finalizacją oraz podłączenie helpera.
- LINEAGE LIMIT: `get_symbol_lineage` rozwiązał `_classify_type_only_modules` jako artifact `A9389/1` na revision 1427, ale jego `calls_interfaces` zawiera nierozstrzygnięte lub dynamiczne krawędzie. `get_symbol_call_context` zwrócił 0 intra-module caller edges. Te projekcje nie dowodzą callerów; bezpośrednie wywołanie potwierdza źródło MCP w `indexer.py:2800–2826`, a oba wejścia finalizatora są widoczne w źródle pod liniami 2880 i 3134. Udokumentowane `contextor_fact_lineage` v1 nie ma rodziny TYPE_CHECKING/type_only, więc nie daje lineage tego faktu.
- CONTRACT_PROVED: Testy odbudowują wejściowe kandydatury z `candidate_imports_by_module` wytworzonego przez rzeczywisty `index_repository`; nie odtwarzają kandydatur z końcowych flag `type_only=False`.

## FULL CLASSIFICATION PARITY

- T28: dla bezpiecznego syntetycznego repo polityka zwraca true, a pełna lista `ImportRef` modułu `pkg.a` oraz hard/soft krawędzie są zgodne z wynikiem FULL.
- T29–T30: shadowing przez `typing.py` i pominięty błędny plik powodują `global_policy_satisfied=False`; zarówno wynik FULL, jak i helper cofają import `pkg.a -> pkg.b` do hard, bez soft edge.
- T31: globalna polityka pozostaje true, lecz dowód pasywności `pkg.__init__` jest false. Oddzielna bramka `parents_proved` powoduje `type_only=False` w obu wynikach.
- T32: niezależnie marker mutation oraz opaque effects powodują projektowy veto; oba przypadki pozostawiają końcowy import hard.
- T33: fingerprint dowodu niezgodny ze źródłem daje politykę false i nie dopuszcza `type_only=True`.
- Testy używają wyłącznie izolowanych repozytoriów syntetycznych i nie wykonują ich modułów.

## COPY-ON-WRITE PROOF

- T34 potwierdza, że funkcja zwraca osobny słownik i nie zmienia wejściowego `pkg.a` ani jego `type_only=True`. W wyniku zmieniony jest wyłącznie moduł wymagający cofnięcia flagi; pozostałe obiekty `Module` są współdzielone przez tożsamość. W kodzie zmienione `Module` i `ImportRef` powstają przez `dataclasses.replace`, a oryginalne obiekty nie są przypisywane ani mutowane.
- Capture kandydatur odbywa się przed wywołaniem helpera i zachowuje oddzielne listy `names`; helper nie zapisuje ani nie modyfikuje mapy evidence.

## TARGETED TESTS

- Interpreter: `Python 3.15.2` (`.venv\Scripts\python.exe --version`).
- Osobny run T28–T34: **8 passed, 256 deselected**; T32 jest parametryzowany na dwa przypadki.
- Pełny wymagany wybór ukierunkowany: **50 passed, 214 deselected, 9.28 s**. Obejmował T28–T34, T01–T05, T09–T12, T22–T27 oraz wskazane wcześniej ukierunkowane regresje finalizacji i pasywności parent initializer.
- Wybranie testów: `pytest -q tests/test_p1d3_d2b2_type_only.py -k 'sp_t4_i2b3 or sp_t4_i2b2c or sp_t4_i1_t0 or sp_t4_i1c_t0 or source_changes_and_typing_shadow_add_remove_reclassify or inline_and_process_pool_typing_shadow_veto_parity or d2b2_r2_negative_parent_initializer_matrix or d2b2_r2_positive_parent_initializer_matrix or d2b2_r2_parent_source_fingerprint_change_reclassifies_child'`.
- `git diff --check` nie zgłosił błędów whitespace; Git wyświetlił wyłącznie ostrzeżenie normalizacji LF/CRLF dla pliku testowego.

## MCP POST-CHANGE AUDIT

- DIRECT_EVIDENCE: `get_project_architecture(fields=[])` odczytał revision 1427, `canonical_state=fresh`, `provenance=live`, `module_count=669`, `resync_required=false` oraz `syntax_errors=0/fresh`. Projekcja raportów historycznych zwróciła `status=partial`, bo `report_diff` jest niedostępny; osobna projekcja `live_state` była dostępna i świeża.
- File-scoped `get_file_edit_context` dla obu zmienionych modułów zwrócił revision 1427, `workspace_sync=verified`, canonical state fresh oraz `syntax_diagnostics=checked_and_none`, `errors=[]`.
- W agregatowej projekcji architektury `workspace_sync=unverified`; wynik ten jest odrębny od zweryfikowanego sync obu plików.
- Rodziny module, graph, topology, artifact_consumption, cycles, collisions i lineage były fresh. `cycle_semantics` pozostało stale. Aktualne structural diagnostics: 16 DFS back-edge paths oraz 1 soft-dependent potential cycle; nie są to dowody wykonania runtime. `resync_required=false`.
- Nie wykonano FULL, SCC02, MCP `update_file` ani restartu.

## FINAL_VERDICT

**I2B3_PASS** — kontrola porównawcza potwierdziła mechaniczne przeniesienie dotychczasowych warunków, a focused regressions T28–T34 i wymagany zestaw ukierunkowany przeszły. Dowody nie oznaczają nowej walidacji rodziny `cycle_semantics` ani runtime atestacji; ta rodzina pozostaje stale.

## FILES_CHANGED

- `contextor/core/symbol_engine/indexer.py` — implementacja.
- `tests/test_p1d3_d2b2_type_only.py` — testy T28–T34.
- `walkthrough.md` — nadpisany raport; jego własny diff jest pominięty jako samoodnoszący się. Pełne diffy pozostałych zmienionych plików są poniżej.

## FULL_DIFFS

Diffy są pełnym rzeczywistym wynikiem `git diff --no-color --unified=0` względem HEAD `ad7f13ff5846cfbc0937aee61c788515554c2489`. Użycie zera linii kontekstu zachowuje wszystkie zmienione linie i hunki, bez ukrywania fragmentów.

### contextor/core/symbol_engine/indexer.py

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 2c5aa93..176d013 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -646,0 +647,135 @@ def _project_typing_imports_closed(
+def _classify_type_only_modules(
+    modules: dict[str, Module],
+    *,
+    source_fingerprints_by_module: dict[str, str],
+    initializer_passivity_by_module: dict[str, tuple[bool, str]],
+    marker_mutation_by_module: dict[str, tuple[bool, str]],
+    opaque_effects_by_module: dict[str, tuple[bool, str]],
+    skipped_source_paths: tuple[str, ...],
+    unindexed_python_sources_present: bool,
+    unindexed_import_artifacts_present: bool,
+) -> tuple[dict[str, Module], bool]:
+    classified = dict(modules)
+    typing_shadowed = (
+        "typing" in modules
+        or "typing.__init__" in modules
+    )
+    project_marker_safe = (
+        not skipped_source_paths
+        and len(marker_mutation_by_module)
+        == len(modules)
+        and all(
+            (
+                module_id
+                in marker_mutation_by_module
+                and type(
+                    marker_mutation_by_module[
+                        module_id
+                    ][0]
+                ) is bool
+                and marker_mutation_by_module[
+                    module_id
+                ][0] is False
+                and marker_mutation_by_module[
+                    module_id
+                ][1] == (
+                    source_fingerprints_by_module.get(
+                        module_id
+                    )
+                )
+            )
+            for module_id in modules
+        )
+    )
+    project_effects_closed = (
+        not skipped_source_paths
+        and not unindexed_python_sources_present
+        and not unindexed_import_artifacts_present
+        and len(opaque_effects_by_module)
+        == len(modules)
+        and all(
+            (
+                module_id
+                in opaque_effects_by_module
+                and type(
+                    opaque_effects_by_module[
+                        module_id
+                    ][0]
+                ) is bool
+                and opaque_effects_by_module[
+                    module_id
+                ][0] is False
+                and opaque_effects_by_module[
+                    module_id
+                ][1] == (
+                    source_fingerprints_by_module.get(
+                        module_id
+                    )
+                )
+            )
+            for module_id in modules
+        )
+        and _project_typing_imports_closed(
+            modules
+        )
+    )
+    global_policy_satisfied = (
+        not typing_shadowed
+        and project_marker_safe
+        and project_effects_closed
+    )
+
+    for module_id, module in modules.items():
+        if not any(
+            import_ref.type_only
+            for import_ref in module.imports
+        ):
+            continue
+
+        parents_proved = all(
+            (
+                parent_id in modules
+                and parent_id
+                in initializer_passivity_by_module
+                and type(
+                    initializer_passivity_by_module[
+                        parent_id
+                    ][0]
+                ) is bool
+                and initializer_passivity_by_module[
+                    parent_id
+                ][0] is True
+                and initializer_passivity_by_module[
+                    parent_id
+                ][1] == (
+                    source_fingerprints_by_module.get(
+                        parent_id
+                    )
+                )
+            )
+            for parent_id in (
+                _typing_guard_parent_initializers(
+                    module_id
+                )
+            )
+        )
+
+        if global_policy_satisfied and parents_proved:
+            continue
+
+        classified[module_id] = dataclasses.replace(
+            module,
+            imports=[
+                dataclasses.replace(
+                    import_ref,
+                    type_only=False,
+                )
+                if import_ref.type_only
+                else import_ref
+                for import_ref in module.imports
+            ],
+        )
+
+    return classified, global_policy_satisfied
+
+
@@ -2665,61 +2800,24 @@ def index_repository(
-        typing_shadowed = (
-            "typing" in modules
-            or "typing.__init__" in modules
-        )
-        project_marker_safe = (
-            not skipped
-            and len(marker_mutation_by_module)
-            == len(modules)
-            and all(
-                (
-                    module_id
-                    in marker_mutation_by_module
-                    and type(
-                        marker_mutation_by_module[
-                            module_id
-                        ][0]
-                    ) is bool
-                    and marker_mutation_by_module[
-                        module_id
-                    ][0] is False
-                    and marker_mutation_by_module[
-                        module_id
-                    ][1] == (
-                        source_fingerprints_by_module.get(
-                            module_id
-                        )
-                    )
-                )
-                for module_id in modules
-            )
-        )
-        project_effects_closed = (
-            not skipped
-            and not unindexed_python_sources_present
-            and not unindexed_import_artifacts_present
-            and len(opaque_effects_by_module)
-            == len(modules)
-            and all(
-                (
-                    module_id
-                    in opaque_effects_by_module
-                    and type(
-                        opaque_effects_by_module[
-                            module_id
-                        ][0]
-                    ) is bool
-                    and opaque_effects_by_module[
-                        module_id
-                    ][0] is False
-                    and opaque_effects_by_module[
-                        module_id
-                    ][1] == (
-                        source_fingerprints_by_module.get(
-                            module_id
-                        )
-                    )
-                )
-                for module_id in modules
-            )
-            and _project_typing_imports_closed(
-                modules
+        classified, global_policy_satisfied = (
+            _classify_type_only_modules(
+                modules,
+                source_fingerprints_by_module=(
+                    source_fingerprints_by_module
+                ),
+                initializer_passivity_by_module=(
+                    initializer_passivity_by_module
+                ),
+                marker_mutation_by_module=(
+                    marker_mutation_by_module
+                ),
+                opaque_effects_by_module=(
+                    opaque_effects_by_module
+                ),
+                skipped_source_paths=tuple(
+                    item.path for item in skipped
+                ),
+                unindexed_python_sources_present=(
+                    unindexed_python_sources_present
+                ),
+                unindexed_import_artifacts_present=(
+                    unindexed_import_artifacts_present
+                ),
@@ -2728,57 +2826 @@ def index_repository(
-
-        global_policy_satisfied = (
-            not typing_shadowed
-            and project_marker_safe
-            and project_effects_closed
-        )
-
-        for module_id, module in modules.items():
-            if not any(
-                import_ref.type_only
-                for import_ref in module.imports
-            ):
-                continue
-
-            parents_proved = all(
-                (
-                    parent_id in modules
-                    and parent_id
-                    in initializer_passivity_by_module
-                    and type(
-                        initializer_passivity_by_module[
-                            parent_id
-                        ][0]
-                    ) is bool
-                    and initializer_passivity_by_module[
-                        parent_id
-                    ][0] is True
-                    and initializer_passivity_by_module[
-                        parent_id
-                    ][1] == (
-                        source_fingerprints_by_module.get(
-                            parent_id
-                        )
-                    )
-                )
-                for parent_id in (
-                    _typing_guard_parent_initializers(
-                        module_id
-                    )
-                )
-            )
-
-            if global_policy_satisfied and parents_proved:
-                continue
-
-            modules[module_id] = dataclasses.replace(
-                module,
-                imports=[
-                    dataclasses.replace(
-                        import_ref,
-                        type_only=False,
-                    )
-                    if import_ref.type_only
-                    else import_ref
-                    for import_ref in module.imports
-                ],
-            )
+        modules.update(classified)
```

### tests/test_p1d3_d2b2_type_only.py

```diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 81827c6..0f1caef 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -3161,0 +3162,159 @@ def test_sp_t4_i2b2c_t27_inline_process_pool_evidence_parity(
+
+def _i2b3_classify(index, evidence=None):
+    evidence = evidence or index.typing_guard_evidence
+    modules = dict(index.modules)
+    for module_id, candidate_imports in evidence[
+        "candidate_imports_by_module"
+    ].items():
+        modules[module_id] = replace(
+            modules[module_id],
+            imports=list(candidate_imports),
+        )
+    classified, policy = indexer._classify_type_only_modules(
+        modules,
+        source_fingerprints_by_module=evidence[
+            "source_fingerprints_by_module"
+        ],
+        initializer_passivity_by_module=evidence[
+            "initializer_passivity_by_module"
+        ],
+        marker_mutation_by_module=evidence[
+            "marker_mutation_by_module"
+        ],
+        opaque_effects_by_module=evidence[
+            "opaque_effects_by_module"
+        ],
+        skipped_source_paths=evidence["skipped_source_paths"],
+        unindexed_python_sources_present=evidence[
+            "unindexed_python_sources_present"
+        ],
+        unindexed_import_artifacts_present=evidence[
+            "unindexed_import_artifacts_present"
+        ],
+    )
+    return modules, classified, policy
+
+
+def _i2b3_graph_edges(modules):
+    graph = build_graph(modules)
+    return (
+        set(graph.hard_edges.get("pkg.a", set())),
+        set(graph.soft_edges.get("pkg.a", set())),
+    )
+
+
+def _i2b3_guarded_import(modules):
+    return next(
+        item for item in modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    )
+
+
+def test_sp_t4_i2b3_t28_safe_classifier_matches_full(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    index, _ = _index_graph(root)
+    _, classified, policy = _i2b3_classify(index)
+    assert policy is True
+    assert classified["pkg.a"].imports == index.modules["pkg.a"].imports
+    assert _i2b3_graph_edges(classified) == _i2b3_graph_edges(index.modules)
+
+
+def test_sp_t4_i2b3_t29_typing_shadow_veto_matches_full(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(
+        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
+    )
+    index, _ = _index_graph(root)
+    _, classified, policy = _i2b3_classify(index)
+    assert policy is False
+    assert _i2b3_guarded_import(classified).type_only is False
+    full_hard, full_soft = _i2b3_graph_edges(index.modules)
+    pure_hard, pure_soft = _i2b3_graph_edges(classified)
+    assert "pkg.b" in full_hard and "pkg.b" not in full_soft
+    assert (pure_hard, pure_soft) == (full_hard, full_soft)
+
+
+def test_sp_t4_i2b3_t30_skipped_veto_matches_full(tmp_path, isolated_dirs):
+    root = write_synthetic_repository(
+        tmp_path / "repo", {**_I1_SAFE, "broken.py": "def invalid(:\n"},
+    )
+    index, _ = _index_graph(root)
+    _, classified, policy = _i2b3_classify(index)
+    assert policy is False
+    assert _i2b3_guarded_import(classified).type_only is False
+    full_hard, full_soft = _i2b3_graph_edges(index.modules)
+    pure_hard, pure_soft = _i2b3_graph_edges(classified)
+    assert "pkg.b" in full_hard and "pkg.b" not in full_soft
+    assert (pure_hard, pure_soft) == (full_hard, full_soft)
+
+
+def test_sp_t4_i2b3_t31_parent_passivity_veto_is_preserved(
+    tmp_path, isolated_dirs,
+):
+    fixture = {**_I1_SAFE, "pkg/__init__.py": "import typing\n"}
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, _ = _index_graph(root)
+    evidence = index.typing_guard_evidence
+    assert evidence["global_policy_satisfied"] is True
+    assert evidence["initializer_passivity_by_module"]["pkg.__init__"][0] is False
+    _, classified, policy = _i2b3_classify(index)
+    assert policy is True
+    assert _i2b3_guarded_import(classified).type_only is False
+    assert _i1_guarded_import(index).type_only is False
+
+
+@pytest.mark.parametrize(
+    "extra_source,evidence_key",
+    [
+        ("import typing\ntyping.TYPE_CHECKING = True\n", "marker_mutation_by_module"),
+        ("eval('0')\n", "opaque_effects_by_module"),
+    ],
+    ids=["marker-mutation", "opaque-effects"],
+)
+def test_sp_t4_i2b3_t32_project_veto_is_preserved(
+    tmp_path, isolated_dirs, extra_source, evidence_key,
+):
+    fixture = {**_I1_SAFE, "pkg/c.py": extra_source}
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, _ = _index_graph(root)
+    evidence = index.typing_guard_evidence
+    assert evidence["global_policy_satisfied"] is False
+    assert evidence[evidence_key]["pkg.c"][0] is True
+    _, classified, policy = _i2b3_classify(index)
+    assert policy is False
+    assert _i2b3_guarded_import(classified).type_only is False
+    assert _i1_guarded_import(index).type_only is False
+
+
+def test_sp_t4_i2b3_t33_fingerprint_mismatch_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
+    index, _ = _index_graph(root)
+    evidence = dict(index.typing_guard_evidence)
+    marker_facts = dict(evidence["marker_mutation_by_module"])
+    marker_facts["pkg.a"] = (False, "stale-fingerprint")
+    evidence["marker_mutation_by_module"] = marker_facts
+    _, classified, policy = _i2b3_classify(index, evidence)
+    assert policy is False
+    assert _i2b3_guarded_import(classified).type_only is False
+
+
+def test_sp_t4_i2b3_t34_classifier_is_copy_on_write(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(
+        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
+    )
+    index, _ = _index_graph(root)
+    modules, classified, policy = _i2b3_classify(index)
+    assert policy is False
+    assert classified is not modules
+    assert set(classified) == set(modules)
+    assert classified["pkg.a"] is not modules["pkg.a"]
+    assert _i2b3_guarded_import(modules).type_only is True
+    assert _i2b3_guarded_import(classified).type_only is False
+    for module_id in modules:
+        if module_id != "pkg.a":
+            assert classified[module_id] is modules[module_id]
+    assert _i2b3_guarded_import(modules).type_only is True
+
```
