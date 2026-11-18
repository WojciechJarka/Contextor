# SP-T4-I2B5-I4A — CLASSIFIED CANDIDATE ADOPTION

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD przed zmianą: `b3bc1d70e91ec3e7aa6fd2de3ad13bdb9c4fb00f`; `git status --short --branch` był czysty (`main...origin/main`).
- DIRECT_EVIDENCE: Contextor LIVE przed zmianą: revision `1442`, provenance `live`, canonical_state `fresh`, `resync_required=false`.
- DIRECT_EVIDENCE: Na revision 1442 `plan_executor.py` i test file miały `workspace_sync=verified`, syntax diagnostics `checked_and_none`, `errors=[]`.
- DIRECT_EVIDENCE: Wszystkie anchory pasowały: argument `force_full_graph` w sygnaturze (linia 1148), walidacja `force_full_graph` po docstringu (1154), walidacja candidate re-export przy `candidate.modules` (1269), T59 na końcu pliku testowego.
- DIRECT_EVIDENCE: `Module` oraz `deepcopy` były już importowane. `isolated_dirs`, `preparation`, `RefreshPlanner`, `replace`, `write_synthetic_repository`, `_I1_SAFE` i helpery I1 wskazane przez T60 istnieją.
- CODE_PATH_PROVED: Istniejący caller w `engine.py:940-952` nie przekazuje nowych argumentów. Podłączenie do `update_file` pozostaje poza tym zadaniem zgodnie z zakazem zmian `engine.py`.
- DIRECT_EVIDENCE: Nie zmieniano plików poza allowlistą.

## EXACT_IMPLEMENTATION

- CODE_PATH_PROVED: Po `force_full_graph` dopisano oba argumenty opcjonalne w zadanej kolejności.
- CODE_PATH_PROVED: Po docstringu, przed dotychczasową walidacją `force_full_graph`, dopisano dokładne sprawdzenie pary wartości oraz dokładnego typu `dict`; istniejąca walidacja nie została zmieniona.
- CODE_PATH_PROVED: Bezpośrednio przed walidacją pokrycia re-exportów candidate dodano kontrolę równości domeny modułów, tożsamości `Module` i ścieżek oraz typu listy `imports`; następnie candidate dostaje kopię mapy `classified_modules` i `deepcopy` dowodów.
- DIRECT_EVIDENCE: Nie zmieniono kolejności ani istniejącej logiki RECOMPUTE, PATCH, GRAPH, `build_graph` lub resolvera. Istniejący guard I3G pozostał bez zmian.
- CODE_PATH_PROVED: `reclassify_incremental_type_only` waliduje baseline schema-v2 i buduje wynik schema-v2; T60 przekazuje bezpośrednio mapę i dowody z tego helpera.

## CLASSIFIED_MODULE_ADOPTION

- CODE_PATH_PROVED: Adoption zachodzi po zwykłym przygotowaniu delta w candidate i przed walidacją domeny re-exportów oraz późniejszym wykonaniem GRAPH. Gdy domena albo tożsamość ścieżki modułu jest niezgodna, funkcja kończy się wyjątkiem przed zwróceniem outcome.
- DIRECT_EVIDENCE: T60 sprawdza odtworzenie candidate bez zmiany referencji `engine.state.modules`, `typing_guard_evidence` ani `dependency_graph`. Evidence candidate jest równoważne przekazanemu evidence, ale nie jest tym samym obiektem.
- CODE_PATH_PROVED: Nowa mapa modułów jest kopią płytką (`dict(classified_modules)`); moduły są frozen dataclass, a w tej ścieżce GRAPH je odczytuje. Helper klasyfikacji tworzy nowe obiekty dla zmienionych importów.
- INFERENCE — REVIEW LIMIT: Executor sprawdza, czy evidence jest dokładnym `dict`, lecz nie waliduje tutaj jego zawartości/schema-v2 ani elementów listy `Module.imports`. Ścieżka T60 używa wyniku helpera, który takie dane waliduje i generuje schema-v2. Bezpośrednie wywołanie z arbitralnymi słownikami nie jest tym testowanym kontraktem.
- CODE_PATH_PROVED: Aktualny production caller w `engine.py` nadal używa wartości domyślnych, więc ta zmiana sama nie wdraża classified-candidate adoption do ścieżki `update_file`. Prompt jawnie wyklucza tę integrację.

## GLOBAL_HARD_SOFT_RECLASSIFICATION

- DIRECT_EVIDENCE: T60 bazuje na istniejącym syntetycznym `_I1_SAFE`: `pkg.a` ma guarded import `pkg.b`, początkowo oznaczony `type_only=True`; zmieniany `pkg.c` dostaje `typing.TYPE_CHECKING = True`.
- CODE_PATH_PROVED: Przygotowanie źródła zapisuje marker-mutation evidence. Detektor AST rozpoznaje zapis do atrybutu `TYPE_CHECKING`; reclassifier przekazuje zachowane evidence do wspólnego klasyfikatora.
- DIRECT_EVIDENCE: T60 potwierdza schema-v2, `global_policy_satisfied is False`, zmianę importu `pkg.a -> pkg.b` na hard, brak tej krawędzi w soft graph oraz `force_full_graph is True`.
- CODE_PATH_PROVED: `plan_type_only_graph_refresh` wyznacza force-full dla zmiany importów w module innym niż zmieniony i dodaje rodziny `modules` oraz `dependency_graph`; executor przyjmuje pełną klasyfikację przed budową grafu.
- INFERENCE — REVIEW LIMIT: T60 dowodzi przepływu w modelu statycznym Contextora na syntetycznym repozytorium. Nie uruchamia importów tego repozytorium w CPython i samodzielnie nie certyfikuje zachowania runtime.

## CANDIDATE_EVIDENCE_ISOLATION

- DIRECT_EVIDENCE: T60 sprawdza, że `candidate.typing_guard_evidence == evidence` oraz `candidate.typing_guard_evidence is not evidence`.
- DIRECT_EVIDENCE: T60 sprawdza, że referencje stanu bazowego do modules, evidence i graph pozostały te same, a bazowy guarded import nadal ma `type_only=True`.
- CODE_PATH_PROVED: Nie dodano publikacji candidate ani zmian transakcji w engine; executor zwraca wynikowy candidate jak wcześniej.

## INVALID_PAYLOAD_REGRESSIONS

- DIRECT_EVIDENCE: T61 pokrywa brak jednej z pary argumentów w obu kierunkach (`ValueError`) oraz nie-dict w każdym argumencie (`TypeError`).
- DIRECT_EVIDENCE: T60 dodatkowo podaje pustą mapę o błędnej domenie i oczekuje `ValueError: Classified module domain mismatch`.
- INFERENCE — REVIEW LIMIT: T61 nie testuje wadliwego schema-v2 wewnątrz poprawnego `dict`; zgodnie z obecną ścieżką dane schema-v2 pochodzą z helpera reclassyfikacji.

## TARGETED_TESTS

- DIRECT_EVIDENCE: Interpreter repo `.venv`: CPython 3.15.2.
- DIRECT_EVIDENCE: Uruchomiono wyłącznie T60-T61, T49-T59 i T35-T48 w `tests/test_p1d3_d2b2_type_only.py`; T61 uruchomił wszystkie cztery przypadki parametryzacji.
- DIRECT_EVIDENCE: Wynik: `39 passed in 12.29s`.
- DIRECT_EVIDENCE: T60 wykonuje `_i1_full_engine` na tymczasowym syntetycznym repozytorium, zgodnie z treścią testu; nie uruchamiano osobnego FULL na `Contextor_Repo` ani pełnego pytest.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Desktop watcher zgłosił `plan_executor.py` jako UPDATED na revision 1443 oraz `tests/test_p1d3_d2b2_type_only.py` jako UPDATED na revision 1444. Event continuity była `continuous`; `resync_required=false`.
- DIRECT_EVIDENCE: Po zmianie LIVE revision 1444, provenance `live`, canonical_state `fresh`, `resync_required=false`.
- DIRECT_EVIDENCE: Oba pliki na revision 1444 miały `workspace_sync=verified`; syntax diagnostics każdego pliku: `checked_and_none`, `errors=[]`. Globalne syntax diagnostics: 0, `fresh`.
- DIRECT_EVIDENCE: Rodziny graph, topology i structural cycles były `fresh`; `cycle_semantics` pozostało `stale`.
- UNKNOWN: Odczyt LIVE/workspace nie poświadcza adopcji kodu przez już działający proces; nie wykonywano restartu ani runtime-adoption probe.
- DIRECT_EVIDENCE: Nie wywołano MCP `update_file`.

## FINAL_VERDICT

I2B5_I4A_PASS — dokładny kontrakt executor’a, adoption przed graph build, izolacja evidence i regresje payloadu zostały wdrożone; wskazane testy przechodzą. Werdykt jest ograniczony do bezpośredniego przekazania wyniku helpera do executor’a. Produkcyjna ścieżka `update_file` nie przekazuje jeszcze tych argumentów, zgodnie z zakresem promptu.

## FILES_CHANGED

- `contextor/core/analysis/incremental/plan_executor.py` — pełny rzeczywisty diff poniżej.
- `tests/test_p1d3_d2b2_type_only.py` — pełny rzeczywisty diff poniżej.
- `walkthrough.md` — raport nadpisany; self-diff pominięty zgodnie z regułą raportowania.

## FULL_DIFFS

### `contextor/core/analysis/incremental/plan_executor.py`

```diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 18dfa10..a5003bd 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -1148,0 +1149,4 @@ def execute_refresh_plan(
+    classified_modules: Optional[Dict[str, Module]] = None,
+    updated_typing_guard_evidence: Optional[
+        Dict[str, object]
+    ] = None,
@@ -1153,0 +1158,15 @@ def execute_refresh_plan(
+    if (
+        (classified_modules is None)
+        != (updated_typing_guard_evidence is None)
+    ):
+        raise ValueError(
+            "Classified modules and typing guard evidence "
+            "must be supplied together"
+        )
+    if classified_modules is not None and (
+        type(classified_modules) is not dict
+        or type(updated_typing_guard_evidence) is not dict
+    ):
+        raise TypeError(
+            "Invalid classified candidate payload"
+        )
@@ -1268,0 +1288,26 @@ def execute_refresh_plan(
+    if classified_modules is not None:
+        if set(classified_modules) != set(candidate.modules):
+            raise ValueError(
+                "Classified module domain mismatch"
+            )
+
+        for module_id, module in classified_modules.items():
+            current = candidate.modules[module_id]
+            if (
+                type(module_id) is not str
+                or type(module) is not Module
+                or type(current) is not Module
+                or module.module_id != module_id
+                or module.path != current.path
+                or module.absolute_path != current.absolute_path
+                or type(module.imports) is not list
+            ):
+                raise ValueError(
+                    "Invalid classified module identity"
+                )
+
+        candidate.modules = dict(classified_modules)
+        candidate.typing_guard_evidence = deepcopy(
+            updated_typing_guard_evidence
+        )
```

### `tests/test_p1d3_d2b2_type_only.py`

```diff
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 195f368..2e882b7 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4399,0 +4400,170 @@ def test_sp_t4_i2b5_i3g_t59_full_graph_requires_modules(
+
+def test_sp_t4_i2b5_i4a_t60_global_classification_before_graph(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.analysis.incremental import (
+        plan_executor as executor,
+    )
+    from contextor.core.analysis.incremental.type_only_policy import (
+        reclassify_incremental_type_only,
+        plan_type_only_graph_refresh,
+    )
+
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    _, engine = _i1_full_engine(root)
+
+    before_modules = engine.state.modules
+    before_evidence = engine.state.typing_guard_evidence
+    before_graph = engine.state.dependency_graph
+
+    assert _i1_guarded_import(engine.state).type_only
+
+    target = root / "pkg/c.py"
+    target.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\n",
+        encoding="utf-8",
+    )
+
+    prepared = preparation.prepare_source_update(
+        file_path=target,
+        module_path="pkg.c",
+        is_new=False,
+        old_module=engine.state.modules["pkg.c"],
+        old_artifacts=engine.state.artifacts.get("pkg.c"),
+        old_usage=engine.state.module_usages.get("pkg.c"),
+        persistent_id=engine.registry.get_module_id("pkg.c"),
+        old_collision_facts=engine.state.collision_facts.get(
+            "pkg.c"
+        ),
+        old_reexport_facts=engine.state.reexport_facts_by_module.get(
+            "pkg.c"
+        ),
+        source_key="pkg/c.py",
+    )
+    assert not prepared.has_error
+
+    provisional = dict(before_modules)
+    provisional["pkg.c"] = replace(
+        provisional["pkg.c"],
+        imports=list(prepared.new_imports),
+    )
+
+    classified, evidence = reclassify_incremental_type_only(
+        provisional,
+        previous_modules=before_modules,
+        previous_evidence=before_evidence,
+        changed_module_id="pkg.c",
+        changed_source_path="pkg/c.py",
+        changed_imports=prepared.new_imports,
+        changed_source_evidence=(
+            prepared.typing_guard_source_evidence
+        ),
+    )
+
+    assert evidence["schema_version"] == 2
+    assert evidence["global_policy_satisfied"] is False
+
+    plan = RefreshPlanner.plan_refresh(
+        prepared.delta,
+        usage_delta=prepared.usage_delta,
+        module_usages=engine.state.module_usages,
+        collision_facts_changed=prepared.collision_facts_changed,
+    )
+
+    plan, force_full_graph = plan_type_only_graph_refresh(
+        plan,
+        changed_module_id="pkg.c",
+        previous_modules=before_modules,
+        classified_modules=classified,
+    )
+
+    assert force_full_graph is True
+
+    call_args = dict(
+        state=engine.state,
+        delta=prepared.delta,
+        usage_delta=prepared.usage_delta,
+        plan=plan,
+        new_imports=prepared.new_imports,
+        new_artifacts=prepared.new_artifacts,
+        new_usage=prepared.new_usage,
+        root_path=root,
+        file_path=str(target.resolve()),
+        new_collision_facts=prepared.new_collision_facts,
+        new_reexport_facts=prepared.new_reexport_facts,
+        force_full_graph=force_full_graph,
+        classified_modules=classified,
+        updated_typing_guard_evidence=evidence,
+    )
+
+    outcome = executor.execute_refresh_plan(**call_args)
+    candidate = outcome.candidate_state
+
+    guarded = next(
+        ref for ref in candidate.modules["pkg.a"].imports
+        if ref.module == "pkg.b"
+    )
+
+    assert guarded.type_only is False
+    assert "pkg.b" in candidate.dependency_graph.hard_edges[
+        "pkg.a"
+    ]
+    assert "pkg.b" not in candidate.dependency_graph.soft_edges[
+        "pkg.a"
+    ]
+
+    assert candidate.typing_guard_evidence == evidence
+    assert candidate.typing_guard_evidence is not evidence
+
+    assert engine.state.modules is before_modules
+    assert engine.state.typing_guard_evidence is before_evidence
+    assert engine.state.dependency_graph is before_graph
+    assert _i1_guarded_import(engine.state).type_only
+
+    with pytest.raises(
+        ValueError,
+        match="Classified module domain mismatch",
+    ):
+        executor.execute_refresh_plan(
+            **{
+                **call_args,
+                "classified_modules": {},
+            }
+        )
+
+
+@pytest.mark.parametrize(
+    "modules,evidence,error",
+    [
+        (None, {}, ValueError),
+        ({}, None, ValueError),
+        ("invalid", {}, TypeError),
+        ({}, "invalid", TypeError),
+    ],
+)
+def test_sp_t4_i2b5_i4a_t61_invalid_candidate_payload(
+    tmp_path, modules, evidence, error,
+):
+    from contextor.core.analysis.incremental import (
+        plan_executor as executor,
+    )
+    from contextor.core.analysis.state_manager import FileDelta
+    from contextor.core.domain.refresh_plan import RefreshPlan
+
+    with pytest.raises(error):
+        executor.execute_refresh_plan(
+            state=RepositoryAnalysisState(),
+            delta=FileDelta(module_path="pkg.a"),
+            usage_delta=None,
+            plan=RefreshPlan(),
+            new_imports=[],
+            new_artifacts={},
+            new_usage=None,
+            root_path=tmp_path,
+            file_path=str(tmp_path / "a.py"),
+            classified_modules=modules,
+            updated_typing_guard_evidence=evidence,
+        )
+```
