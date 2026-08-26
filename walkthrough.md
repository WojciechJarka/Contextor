# CONTEXTOR — H2B-H4 REAL HYDRATION INTEGRATION CLOSURE CERTIFICATION REPORT

## 1. Executive Summary & Acceptance Matrix

```text
H2B_H3_MATERIALIZATION_LOGIC=PASS

REAL_HYDRATE_REPOSITORY_ENGINE_USED=YES

OLD_SNAPSHOT_BEFORE_HYDRATION_REFERENCE_EVIDENCE_MATERIALIZED=NO

FIRST_PRODUCTION_HYDRATION_EXTRACTIONS=1
FIRST_PRODUCTION_HYDRATION_REFERENCE_EVIDENCE_MATERIALIZED=YES

UPGRADED_STATE_PERSISTED=YES

SECOND_PRODUCTION_HYDRATION_EXTRACTIONS=0
SECOND_PRODUCTION_HYDRATION_REFERENCE_EVIDENCE_MATERIALIZED=YES

SECOND_PRODUCTION_HYDRATION_REFERENCE_EVIDENCE_EQUAL=PASS

POST_RESTART_BUILD_SYMBOL_REFERENCES_CALLED=0
POST_RESTART_REFERENCE_REPO_SCAN=0

PRODUCTION_HYDRATION_WIRING_ALREADY_PRESENT=YES
HYDRATION_PRODUCTION_CHANGE=NO

REFERENCE_PROJECTOR_REGRESSIONS=0

FILES_CHANGED=[
    contextor/core/domain/usage_facts.py,
    contextor/core/reference/visitor.py,
    contextor/core/reference/engine.py,
    contextor/core/analysis/incremental/materialization.py,
    contextor/core/single_file/builders/layer0_builders.py,
    tests/test_canonical_reference_projection.py,
    tests/test_reporting_single_file.py,
    tests/test_symbol_call_facts.py
]

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO

VERDICT=H2B_FINAL_PASS_CANDIDATE
```

---

## 2. Invariants & Lifecycle Mechanics

### 2.1 Production Hydration Lifecycle Wiring
- `hydrate_repository_engine(repo_root)` loads snapshot metadata/state and instantiates `IncrementalAnalysisEngine(...)`, which unconditionally triggers `materialize_incremental_state(self.state)`.
- `materialize_incremental_state(self.state)` calls `ensure_module_usages(state)`, detecting legacy unmaterialized `reference_evidence` slices (`symbol_calls_materialized=True, reference_evidence_materialized=False`) and executing a single-pass authoritative source-backed extraction.
- **Production hydration wiring already present**: `contextor/core/live_state/hydration.py` already calls `IncrementalAnalysisEngine` which invokes `materialize_incremental_state`. Zero production changes required in `hydration.py`.

### 2.2 Integration Proof: One-Time Upgrade & Subsequent Fast Path
- **First Production Hydration**: Exactly 1 extraction executed for legacy module (`extract_module_usage_facts.call_count == 1`), promoting facts to `reference_evidence_materialized=True`.
- **State Persistence**: Upgraded canonical state saved to disk snapshot using standard product API (`save_engine_state(...)`).
- **Second Production Hydration**: Exactly 0 extractions (`extract_module_usage_facts.call_count == 0`), `module_usages_require_materialization(...) is False`.
- **Post-Restart Single-File Analysis**: `build_symbol_references` called **0 times** (`assert not legacy_ref_spy.called`), proving pure in-memory canonical reference projection without AST parses or file I/O.

---

## 3. Targeted Test Results

### 3.1 Lifecycle & Hydration Integration Suite (`tests/test_symbol_call_facts.py`)
```text
tests/test_symbol_call_facts.py::test_graph_analytics_full_materialization_has_canonical_symbol_edges PASSED
tests/test_symbol_call_facts.py::test_multiple_local_callers_and_callees_are_qualified PASSED
tests/test_symbol_call_facts.py::test_method_owner_nested_and_module_level_semantics PASSED
tests/test_symbol_call_facts.py::test_nested_sync_and_async_bodies_are_not_outer_calls PASSED
tests/test_symbol_call_facts.py::test_definition_time_calls_are_not_owned_by_new_function PASSED
tests/test_symbol_call_facts.py::test_legacy_reference_context_remains_for_function_and_method PASSED
tests/test_symbol_call_facts.py::test_unresolved_or_ambiguous_call_is_not_confirmed PASSED
tests/test_symbol_call_facts.py::test_symbol_call_materialization_requires_successful_authoritative_extraction PASSED
tests/test_symbol_call_facts.py::test_incremental_replace_remove_delete_and_unrelated_preservation PASSED
tests/test_symbol_call_facts.py::test_syntax_stale_is_not_current_and_recovery_matches_full_extraction PASSED
tests/test_symbol_call_facts.py::test_snapshot_roundtrip_and_artifact_consumption_contract PASSED
tests/test_symbol_call_facts.py::test_legacy_pickled_usage_facts_get_empty_symbol_call_default PASSED
tests/test_symbol_call_facts.py::test_legacy_symbol_call_class_snapshot_migrates_to_primitive_tuples PASSED
tests/test_symbol_call_facts.py::test_unrelated_invalid_pickle_is_not_migrated PASSED
tests/test_symbol_call_facts.py::test_legacy_existing_usage_is_backfilled_once_and_unrelated_is_preserved PASSED
tests/test_symbol_call_facts.py::test_materialized_empty_symbol_calls_survive_snapshot_without_rebuild PASSED
tests/test_symbol_call_facts.py::test_incremental_create_and_update_mark_symbol_calls_materialized PASSED
tests/test_symbol_call_facts.py::test_graph_analytics_legacy_usage_backfills_required_edges PASSED
tests/test_symbol_call_facts.py::test_module_usages_require_materialization_for_reference_evidence PASSED
tests/test_symbol_call_facts.py::test_legacy_reference_evidence_upgrade PASSED
tests/test_symbol_call_facts.py::test_legacy_reference_evidence_triggers_single_extraction PASSED
tests/test_symbol_call_facts.py::test_current_module_usages_untouched_during_legacy_upgrade PASSED
tests/test_symbol_call_facts.py::test_old_pickled_or_dict_shape_detected_and_upgraded PASSED
tests/test_symbol_call_facts.py::test_hydration_legacy_module_usages_authoritative_upgrade_and_roundtrip PASSED

============================= 24 passed in 7.70s ==============================
```

### 3.2 Full Targeted Test Suites
```text
tests/test_symbol_call_facts.py (24 tests) PASSED
tests/test_canonical_reference_projection.py (15 tests) PASSED
tests/test_reporting_single_file.py (13 tests) PASSED
tests/test_live_single_file_reuse.py (12 tests) PASSED
tests/test_pipeline.py (6 tests) PASSED
tests/test_incremental_reverse_context.py (19 tests) PASSED
tests/test_facade_progress_staging.py (3 tests) PASSED

============================= 92 passed in 119.42s =============================
```

---

## 4. Complete Unified Diff

### 4.1 Production Files

```diff
diff --git a/contextor/core/analysis/incremental/materialization.py b/contextor/core/analysis/incremental/materialization.py
index a0df2ec..6c1ae3b 100644
--- a/contextor/core/analysis/incremental/materialization.py
+++ b/contextor/core/analysis/incremental/materialization.py
@@ -19,7 +19,18 @@ def module_usages_require_materialization(state: RepositoryAnalysisState) -> bool
         return bool(getattr(state, "modules", {}))
     return any(
         module_name not in usages
-        or not bool(vars(usages[module_name]).get("symbol_calls_materialized", False))
+        or not bool(
+            vars(usages[module_name]).get(
+                "symbol_calls_materialized",
+                False,
+            )
+        )
+        or not bool(
+            vars(usages[module_name]).get(
+                "reference_evidence_materialized",
+                False,
+            )
+        )
         for module_name in getattr(state, "modules", {})
     )
 
@@ -26,7 +37,7 @@ def module_usages_require_materialization(state: RepositoryAnalysisState) -> bool
 def ensure_module_usages(state: RepositoryAnalysisState) -> None:
     """
-    Initializes state.module_usages for pre-existing state.modules if missing.
-    Source-backed legacy reconstruction: only missing modules read source from disk.
+    Initializes state.module_usages for pre-existing state.modules if missing or legacy.
+    Source-backed legacy reconstruction: only missing or unmaterialized modules read source from disk.
     """
     if not hasattr(state, "module_usages") or state.module_usages is None:
         state.module_usages = {}
@@ -33,11 +44,24 @@ def ensure_module_usages(state: RepositoryAnalysisState) -> None:
     missing_modules = set(state.modules.keys()) - set(state.module_usages.keys())
-    legacy_symbol_call_modules = {
+    legacy_usage_modules = {
         module_name
         for module_name, facts in state.module_usages.items()
         if module_name in state.modules
-        and not bool(vars(facts).get("symbol_calls_materialized", False))
+        and (
+            not bool(
+                vars(facts).get(
+                    "symbol_calls_materialized",
+                    False,
+                )
+            )
+            or not bool(
+                vars(facts).get(
+                    "reference_evidence_materialized",
+                    False,
+                )
+            )
+        )
     }
-    modules_to_materialize = missing_modules | legacy_symbol_call_modules
+    modules_to_materialize = missing_modules | legacy_usage_modules
     if modules_to_materialize:
         from contextor.core.reference.engine import extract_module_usage_facts

diff --git a/contextor/core/domain/usage_facts.py b/contextor/core/domain/usage_facts.py
index a5bca74..ee62ecb 100644
--- a/contextor/core/domain/usage_facts.py
+++ b/contextor/core/domain/usage_facts.py
@@ -11,6 +11,7 @@ from typing import Any, Dict, Tuple
 
 
 SymbolCallFact = Tuple[str, str, int, str]
+ReferenceEvidenceFact = Tuple[str, str, str, int]
 
 
 @dataclass(frozen=True)
@@ -32,15 +33,26 @@ class ModuleUsageFacts:
     aliases: Tuple[Tuple[str, str], ...] = ()           # (local_alias, imported_target)
     symbol_calls: Tuple[SymbolCallFact, ...] = ()
     symbol_calls_materialized: bool = False
+    reference_evidence: Tuple[ReferenceEvidenceFact, ...] = ()
+    reference_evidence_materialized: bool = False
 
     def __getattribute__(self, name: str):
-        if name == "symbol_calls_materialized":
+        if name in (
+            "symbol_calls_materialized",
+            "reference_evidence_materialized",
+        ):
             return bool(
-                object.__getattribute__(self, "__dict__").get(name, False)
+                object.__getattribute__(self, "__dict__").get(
+                    name,
+                    False,
+                )
             )
         return object.__getattribute__(self, name)
 
     def __getattr__(self, name: str):
         # Pickle restores old dataclass instances without fields added later.
-        if name == "symbol_calls":
+        if name in ("symbol_calls", "reference_evidence"):
             return ()
+        if name == "reference_evidence_materialized":
             return False
         raise AttributeError(name)
 
@@ -67,6 +79,21 @@ class ModuleUsageFacts:
             "symbol_calls_materialized": bool(
                 vars(self).get("symbol_calls_materialized", False)
             ),
+            "reference_evidence": [
+                {
+                    "target": item[0],
+                    "channel": item[1],
+                    "caller": item[2],
+                    "line": item[3],
+                }
+                for item in getattr(self, "reference_evidence", ())
+            ],
+            "reference_evidence_materialized": bool(
+                vars(self).get(
+                    "reference_evidence_materialized",
+                    False,
+                )
+            ),
         }
 
     @classmethod
@@ -105,6 +132,24 @@ class ModuleUsageFacts:
             )
         )
 
+        raw_ref_ev = data.get("reference_evidence", [])
+        reference_evidence = tuple(
+            sorted(
+                {
+                    (
+                        str(item["target"]),
+                        str(item["channel"]),
+                        str(item.get("caller", "")),
+                        int(item.get("line", 0)),
+                    )
+                    for item in raw_ref_ev
+                    if isinstance(item, dict)
+                    and "target" in item
+                    and "channel" in item
+                }
+            )
+        )
+
         return cls(
             imports=imports,
             direct_calls=direct_calls,
@@ -117,6 +162,13 @@ class ModuleUsageFacts:
             symbol_calls_materialized=bool(
                 data.get("symbol_calls_materialized", False)
             ),
+            reference_evidence=reference_evidence,
+            reference_evidence_materialized=bool(
+                data.get(
+                    "reference_evidence_materialized",
+                    False,
+                )
+            ),
         )
 
 
@@ -144,6 +196,8 @@ class UsageDelta:
     removed_aliases: Tuple[Tuple[str, str], ...] = ()
     added_symbol_calls: Tuple[SymbolCallFact, ...] = ()
     removed_symbol_calls: Tuple[SymbolCallFact, ...] = ()
+    added_reference_evidence: Tuple[ReferenceEvidenceFact, ...] = ()
+    removed_reference_evidence: Tuple[ReferenceEvidenceFact, ...] = ()
 
     @property
     def is_empty(self) -> bool:
@@ -167,6 +221,8 @@ class UsageDelta:
                 self.removed_aliases,
                 self.added_symbol_calls,
                 self.removed_symbol_calls,
+                self.added_reference_evidence,
+                self.removed_reference_evidence,
             ]
         )
 
@@ -203,6 +259,10 @@ def diff_usage_facts(
         getattr(old_f, "symbol_calls", ()),
         getattr(new_f, "symbol_calls", ()),
     )
+    add_refev, rem_refev = _diff_tuples(
+        getattr(old_f, "reference_evidence", ()),
+        getattr(new_f, "reference_evidence", ()),
     )
 
     return UsageDelta(
         module_path=module_path,
@@ -223,5 +283,7 @@ def diff_usage_facts(
         removed_aliases=rem_alias,
         added_symbol_calls=add_symbol_calls,
         removed_symbol_calls=rem_symbol_calls,
+        added_reference_evidence=add_refev,
+        removed_reference_evidence=rem_refev,
     )
 
diff --git a/contextor/core/reference/visitor.py b/contextor/core/reference/visitor.py
index ea5bce3..475f4fe 100644
--- a/contextor/core/reference/visitor.py
+++ b/contextor/core/reference/visitor.py
@@ -65,6 +65,7 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
         self.event_bound = set()
         self.inherited = []
         self.qualified_refs = set()
+        self.reference_evidence = set()
 
         self._call_funcs = set()
         self.aliases = {}
@@ -183,8 +184,17 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
                 return
 
             name = _attribute_name(node.args[1])
-            resolved = self._resolve_name(name)
+            resolved = self._resolve_name(name)
+
+            if resolved or name:
+                self.reference_evidence.add(
+                    (
+                        resolved or name,
+                        "event_bindings",
+                        self._current_context() or "",
+                        getattr(node, "lineno", 0),
+                    )
+                )
 
             classification, match = _classify_match(
                 name,
@@ -206,8 +216,17 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
                 return
 
             name = _attribute_name(node.args[0])
-            resolved = self._resolve_name(name)
+            resolved = self._resolve_name(name)
+
+            if resolved or name:
+                self.reference_evidence.add(
+                    (
+                        resolved or name,
+                        "event_bindings",
+                        self._current_context() or "",
+                        getattr(node, "lineno", 0),
+                    )
+                )
 
             classification, match = _classify_match(
                 name,
@@ -248,8 +267,17 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
                 continue
 
             name = _attribute_name(keyword.value)
-            resolved = self._resolve_name(name)
+            resolved = self._resolve_name(name)
+
+            if resolved or name:
+                self.reference_evidence.add(
+                    (
+                        resolved or name,
+                        "callback_calls",
+                        self._current_context() or "",
+                        getattr(node, "lineno", 0),
+                    )
+                )
 
             classification, match = _classify_match(
                 name,
@@ -284,6 +312,14 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
             )
 
             self.aliases[local_name] = imported_name
+            self.reference_evidence.add(
+                (
+                    imported_name,
+                    "api_imports",
+                    "",
+                    getattr(node, "lineno", 0),
+                )
+            )
 
         self.generic_visit(node)
 
@@ -291,6 +327,14 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
             local_name = item.asname or item.name.split(".")[-1]
 
             self.aliases[local_name] = item.name
+            self.reference_evidence.add(
+                (
+                    item.name,
+                    "api_imports",
+                    "",
+                    getattr(node, "lineno", 0),
+                )
+            )
 
         self.generic_visit(node)
 
@@ -318,6 +362,15 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
             name = _attribute_name(node)
             if name and "." in name:
                 resolved = self._resolve_name(name)
+                if resolved or name:
+                    self.reference_evidence.add(
+                        (
+                            resolved or name,
+                            "qualified_refs",
+                            self._current_context() or "",
+                            getattr(node, "lineno", 0),
+                        )
+                    )
                 classification, match = _classify_match(
                     name,
                     resolved,
@@ -365,9 +418,17 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
             and isinstance(node.args[1].value, str)
         ):
             dynamic_name = node.args[1].value
-            resolved_dyn = self._resolve_name(dynamic_name)
+            resolved_dyn = self._resolve_name(dynamic_name)
 
+            self.reference_evidence.add(
+                (
+                    resolved_dyn or dynamic_name,
+                    "called_ambiguous",
+                    self._current_context() or "",
+                    getattr(node, "lineno", 0),
+                )
+            )
+
             _, dyn_match = _classify_match(
                 dynamic_name,
                 resolved_dyn,
@@ -400,6 +461,16 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
 
                 resolved_arg = self._resolve_name(arg_name)
 
+                if resolved_arg or arg_name:
+                    self.reference_evidence.add(
+                        (
+                            resolved_arg or arg_name,
+                            "callback_calls",
+                            self._current_context() or "",
+                            getattr(node, "lineno", 0),
+                        )
+                    )
+
                 classification, arg_match = _classify_match(
                     arg_name,
                     resolved_arg,
@@ -421,6 +492,19 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
 
         resolved = self._resolve_name(called_name)
 
+        if resolved or called_name:
+            candidate = self._instance_method_candidate(resolved)
+            target_to_record = candidate or resolved or called_name
+            if target_to_record != "getattr":
+                self.reference_evidence.add(
+                    (
+                        target_to_record,
+                        "direct_calls",
+                        self._current_context() or "",
+                        getattr(node, "lineno", 0),
+                    )
+                )
+
         if resolved in self.target_symbols:
             self.called.add(
                 (
@@ -530,9 +614,18 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
 
         for base in node.bases:
             base_name = _attribute_name(base)
-            resolved = self._resolve_name(base_name)
+            resolved = self._resolve_name(base_name)
 
+            if resolved or base_name:
+                self.reference_evidence.add(
+                    (
+                        resolved or base_name,
+                        "inheritance",
+                        node.name,
+                        getattr(node, "lineno", 0),
+                    )
+                )
+
             classification, match = _classify_match(
                 base_name,
                 resolved,
@@ -582,6 +675,26 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
 
         self.generic_visit(node)
 
+    def _instance_method_candidate(self, resolved):
+        """
+        Extract raw instance method candidate: obj.method() -> Class.method
+        without classifying against target_symbols.
+        """
+        if not resolved:
+            return None
+
+        parts = resolved.split(".")
+        if len(parts) != 2:
+            return None
+
+        instance_name, method = parts
+        constructor = self.instances.get(instance_name)
+        if not constructor:
+            return None
+
+        return f"{constructor}.{method}"
+
     def _resolve_instance_method(self, resolved):
         """
         Resolve calls such as:
@@ -590,26 +703,11 @@ class SymbolReferenceVisitor(ast.NodeVisitor):
 
         when `obj` was previously assigned from a known
         constructor.
         """
-        if not resolved:
-            return None
-
-        parts = resolved.split(".")
-
-        if len(parts) != 2:
-            return None
-
-        instance_name, method = parts
-
-        constructor = self.instances.get(instance_name)
-
-        if not constructor:
-            return None
-
-        candidate = f"{constructor}.{method}"
-
+        candidate = self._instance_method_candidate(resolved)
         if candidate in self.target_symbols:
             return candidate
 
         return None
 
diff --git a/contextor/core/reference/engine.py b/contextor/core/reference/engine.py
index a1593c6..c094ebf 100644
--- a/contextor/core/reference/engine.py
+++ b/contextor/core/reference/engine.py
@@ -880,6 +880,21 @@ def extract_module_usage_facts(
     )
 
 
+    reference_evidence = tuple(
+        sorted(
+            {
+                (
+                    str(t),
+                    str(ch),
+                    str(caller),
+                    int(line),
+                )
+                for t, ch, caller, line in visitor.reference_evidence
+                if t and ch
+            }
+        )
+    )
+
     return ModuleUsageFacts(
         imports=tuple(sorted(import_names)),
         direct_calls=direct_calls,
@@ -890,8 +905,217 @@ def extract_module_usage_facts(
         aliases=aliases,
         symbol_calls=symbol_calls,
         symbol_calls_materialized=True,
+        reference_evidence=reference_evidence,
+        reference_evidence_materialized=True,
     )
 
 
+# ==========================================================
+# CANONICAL REFERENCE PROJECTION
+# ==========================================================
+
+
+class CanonicalReferenceEvidenceUnavailable(RuntimeError):
+    """Raised when required canonical reference facts are unavailable, stale, or incomplete."""
+    pass
+
+
+def _usage_fact_contains_target(
+    fact_target: str,
+    definer_module: str,
+    symbol: str,
+    aliases: tuple[tuple[str, str], ...] = (),
+) -> bool:
+    """Check whether an outbound usage fact target matches the requested definer::symbol."""
+    canonical_identity = f"{definer_module}.{symbol}"
+
+    if fact_target == canonical_identity or fact_target == symbol:
+        return True
+
+    for local_alias, target in aliases:
+        if fact_target == local_alias and target == canonical_identity:
+            return True
+        if fact_target.startswith(f"{local_alias}.") and canonical_identity.startswith(f"{target}."):
+            suffix = fact_target[len(local_alias) + 1:]
+            if f"{target}.{suffix}" == canonical_identity:
+                return True
+
+    if fact_target.endswith(f".{symbol}"):
+        if fact_target == canonical_identity or fact_target.endswith(f".{canonical_identity}"):
+            return True
+        prefix = fact_target[:-len(symbol) - 1]
+        for local_alias, target in aliases:
+            if prefix == local_alias and (target == definer_module or target.endswith(definer_module)):
+                return True
+
+    return False
+
+
+def build_symbol_references_from_canonical(
+    *,
+    definer_module: str,
+    symbols: list[str],
+    artifact_consumption: dict[str, Any],
+    module_usages: dict[str, Any],
+    current_modules: set[str] | None = None,
+) -> dict[str, Any]:
+    """
+    Pure in-memory projection of symbol references from canonical artifact_consumption and module_usages facts.
+    Produces the exact same dict shape and content as build_symbol_references without any file I/O or AST parsing.
+
+    Confirmed references (imports, direct_calls, callbacks, events, qualified_refs, inheritance, runtime)
+    are strictly artifact_consumption-gated inbound edges.
+    Ambiguous candidates (called_by_ambiguous) are scanned from canonical current module_usages evidence
+    and are intentionally unconfirmed.
+    """
+    candidate_modules = (
+        current_modules
+        if current_modules is not None
+        else set(module_usages)
+    )
+
+    for module_id in candidate_modules:
+        facts = module_usages.get(module_id)
+        if facts is None:
+            raise CanonicalReferenceEvidenceUnavailable(
+                f"Missing module_usages for current module {module_id}"
+            )
+        if not getattr(
+            facts,
+            "reference_evidence_materialized",
+            False,
+        ):
+            raise CanonicalReferenceEvidenceUnavailable(
+                f"Reference evidence not materialized for current module {module_id}"
+            )
+
+    result: dict[str, Any] = {}
+
+    for symbol in symbols:
+        result[symbol] = _empty_reference()
+
+        target_key = f"{definer_module}::{symbol}"
+        consumption = artifact_consumption.get(target_key)
+
+        confirmed_consumers = consumption.get("consumers", ()) if consumption else ()
+        channels_by_consumer = consumption.get("channels", {}) if consumption else {}
+
+        for consumer in confirmed_consumers:
+            if current_modules is not None and consumer not in current_modules:
+                raise CanonicalReferenceEvidenceUnavailable(
+                    f"Consumer {consumer} is not current"
+                )
+
+            facts = module_usages.get(consumer)
+            if facts is None:
+                raise CanonicalReferenceEvidenceUnavailable(
+                    f"Missing module_usages for confirmed consumer {consumer}"
+                )
+
+            if not getattr(
+                facts,
+                "reference_evidence_materialized",
+                False,
+            ):
+                raise CanonicalReferenceEvidenceUnavailable(
+                    f"Reference evidence not materialized for confirmed consumer {consumer}"
+                )
+
+            channels = channels_by_consumer.get(consumer, ())
+            aliases = getattr(facts, "aliases", ())
+            reference_evidence = getattr(facts, "reference_evidence", ())
+
+            for channel in channels:
+                if channel in ("api_imports", "imports"):
+                    result[symbol]["imported_from"].append(consumer)
+
+                elif channel == "direct_calls":
+                    result[symbol]["called_by"].append(consumer)
+                    for item in reference_evidence:
+                        if item[1] == "direct_calls" and _usage_fact_contains_target(
+                            item[0], definer_module, symbol, aliases
+                        ):
+                            result[symbol]["called_by_detail"].append(
+                                {
+                                    "module": consumer,
+                                    "line": item[3] if item[3] else None,
+                                    "context": item[2] if item[2] else None,
+                                }
+                            )
+
+                elif channel == "callback_calls":
+                    result[symbol]["callback_called"].append(consumer)
+                    for item in reference_evidence:
+                        if item[1] == "callback_calls" and _usage_fact_contains_target(
+                            item[0], definer_module, symbol, aliases
+                        ):
+                            result[symbol]["callback_called_detail"].append(
+                                {
+                                    "module": consumer,
+                                    "line": item[3] if item[3] else None,
+                                    "context": item[2] if item[2] else None,
+                                }
+                            )
+
+                elif channel == "event_bindings":
+                    result[symbol]["event_bound_by"].append(consumer)
+                    for item in reference_evidence:
+                        if item[1] == "event_bindings" and _usage_fact_contains_target(
+                            item[0], definer_module, symbol, aliases
+                        ):
+                            result[symbol]["event_bound_by_detail"].append(
+                                {
+                                    "module": consumer,
+                                    "line": item[3] if item[3] else None,
+                                    "context": item[2] if item[2] else None,
+                                }
+                            )
+
+                elif channel == "qualified_refs":
+                    result[symbol]["qualified_refs"].append(consumer)
+                    for item in reference_evidence:
+                        if item[1] == "qualified_refs" and _usage_fact_contains_target(
+                            item[0], definer_module, symbol, aliases
+                        ):
+                            result[symbol]["qualified_refs_detail"].append(
+                                {
+                                    "module": consumer,
+                                    "line": item[3] if item[3] else None,
+                                    "context": item[2] if item[2] else None,
+                                }
+                            )
+
+                elif channel == "inheritance":
+                    result[symbol]["inherited_by"].append(consumer)
+                    for item in reference_evidence:
+                        if item[1] == "inheritance" and _usage_fact_contains_target(
+                            item[0], definer_module, symbol, aliases
+                        ):
+                            result[symbol]["inherited_by_detail"].append(
+                                {
+                                    "module": consumer,
+                                    "child": item[2],
+                                    "line": item[3] if item[3] else None,
+                                }
+                            )
+
+                elif channel == "runtime_calls":
+                    result[symbol]["runtime_calls"].append(consumer)
+
+        # Ambiguous calls can come from any module
+        for mod in candidate_modules:
+            mod_facts = module_usages[mod]
+            mod_aliases = getattr(mod_facts, "aliases", ())
+            for item in getattr(mod_facts, "reference_evidence", ()):
+                if item[1] == "called_ambiguous" and _usage_fact_contains_target(
+                    item[0], definer_module, symbol, mod_aliases
+                ):
+                    result[symbol]["called_by_ambiguous"].append(mod)
+                    result[symbol]["called_by_ambiguous_detail"].append(
+                        {
+                            "module": mod,
+                            "reason": "short_name_match_no_confirmed_import",
+                            "line": item[3] if item[3] else None,
+                            "context": item[2] if item[2] else None,
+                        }
+                    )
+
     return _normalize_references(result)
 
 
 # ==========================================================
 # PUBLIC EXPORTS
 # ==========================================================
 
 __all__ = [
     "MAX_USAGE_DETAILS",
     "CanonicalReferenceEvidenceUnavailable",
     "build_symbol_references",
     "build_symbol_references_from_canonical",
     "extract_module_usage_facts",
     "find_import_users",
     "reset_caches",
 ]
diff --git a/contextor/core/single_file/builders/layer0_builders.py b/contextor/core/single_file/builders/layer0_builders.py
index dc81ab4..aa2fed8 100644
--- a/contextor/core/single_file/builders/layer0_builders.py
+++ b/contextor/core/single_file/builders/layer0_builders.py
@@ -1,5 +1,10 @@
 from typing import Any
 from .registry import ContextBuilder, ContextPayload, BuildState
+from contextor.core.reference.engine import (
+    CanonicalReferenceEvidenceUnavailable,
+    build_symbol_references,
+    build_symbol_references_from_canonical,
+)
 
 class ModuleIntentBuilder:
     name = "ModuleIntentBuilder"
@@ -207,13 +212,43 @@ class SymbolContextBuilder:
         # --------------------------------------------------
         # REFERENCES & CANONICAL PROJECTION
         # --------------------------------------------------
 
         canonical_reference_eligible = bool(
             canonical_current
             and getattr(payload.engine_state, "artifact_consumption_state", "deferred") == "fresh"
             and isinstance(getattr(payload.engine_state, "module_usages", None), dict)
         )
 
         references = None
         if canonical_reference_eligible:
             canonical_modules = getattr(payload.engine_state, "modules", None)
             module_universe = canonical_modules if isinstance(canonical_modules, dict) else payload.modules
 
             current_reference_modules = {
                 mod_id
                 for mod_id in module_universe
                 if _canonical_state_module_is_current(payload.engine_state, mod_id)
             }
             try:
                 references = build_symbol_references_from_canonical(
                     definer_module=payload.module_id,
                     symbols=all_symbols,
                     artifact_consumption=payload.engine_state.artifact_consumption or {},
                     module_usages=payload.engine_state.module_usages,
                     current_modules=current_reference_modules,
                 )
             except CanonicalReferenceEvidenceUnavailable:
                 references = None
 
         if references is None:
             references = build_symbol_references(
                 payload.modules,
                 all_symbols,
                 payload.root_path,
                 definer_module=payload.module_id,
             )
 
         consumers = extract_api_consumers(
             all_symbols,
```

### 4.2 Test Files

```diff
diff --git a/tests/test_reporting_single_file.py b/tests/test_reporting_single_file.py
index d655422..64f3655 100644
--- a/tests/test_reporting_single_file.py
+++ b/tests/test_reporting_single_file.py
@@ -304,7 +304,7 @@ def test_promoted_fields_bypass_legacy_extractors(tmp_path):
         extract_symbols.assert_not_called()
         find_usage.assert_not_called()
         build_index.assert_not_called()
-        spy_refs.assert_called_once()
+        spy_refs.assert_not_called()
 
     assert "compute" in result["symbol_context"]["all_symbols"]
 
diff --git a/tests/test_symbol_call_facts.py b/tests/test_symbol_call_facts.py
index a539cf4..1905ea7 100644
--- a/tests/test_symbol_call_facts.py
+++ b/tests/test_symbol_call_facts.py
@@ -4,7 +4,11 @@ from pathlib import Path
 from unittest.mock import patch
 
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
-from contextor.core.analysis.incremental.materialization import ensure_module_usages
+from contextor.core.analysis.incremental.materialization import (
+    ensure_module_usages,
+    materialize_incremental_state,
+    module_usages_require_materialization,
+)
 from contextor.core.analysis.state_manager import (
     FileStateManager,
     RepositoryAnalysisState,
@@ -480,4 +484,263 @@ def test_graph_analytics_legacy_usage_backfills_required_edges(tmp_path):
     assert _edge(f"{module_name}::_compute_pagerank", f"{module_name}::_normalized_edges", 737) in calls
     assert _edge(f"{module_name}::compute_topology_analytics", f"{module_name}::_compute_pagerank", 1930) in calls
     assert state.module_usages["unrelated"] is unrelated
+
+
+def test_module_usages_require_materialization_for_reference_evidence():
+    # Case A: Both materialized -> False
+    state_a = RepositoryAnalysisState(
+        modules={"sample": Module("sample", "sample.py", "/path/sample.py", [])},
+        module_usages={
+            "sample": ModuleUsageFacts(
+                symbol_calls_materialized=True,
+                reference_evidence_materialized=True,
+            )
+        },
+    )
+    assert module_usages_require_materialization(state_a) is False
+
+    # Case B: symbol_calls True, reference_evidence False -> True
+    state_b = RepositoryAnalysisState(
+        modules={"sample": Module("sample", "sample.py", "/path/sample.py", [])},
+        module_usages={
+            "sample": ModuleUsageFacts(
+                symbol_calls_materialized=True,
+                reference_evidence_materialized=False,
+            )
+        },
+    )
+    assert module_usages_require_materialization(state_b) is True
+
+    # Case C: symbol_calls False, reference_evidence True -> True
+    state_c = RepositoryAnalysisState(
+        modules={"sample": Module("sample", "sample.py", "/path/sample.py", [])},
+        module_usages={
+            "sample": ModuleUsageFacts(
+                symbol_calls_materialized=False,
+                reference_evidence_materialized=True,
+            )
+        },
+    )
+    assert module_usages_require_materialization(state_c) is True
+
+    # Case D: Missing module_usages entry -> True
+    state_d = RepositoryAnalysisState(
+        modules={"sample": Module("sample", "sample.py", "/path/sample.py", [])},
+        module_usages={},
+    )
+    assert module_usages_require_materialization(state_d) is True
+
+
+def test_legacy_reference_evidence_upgrade(tmp_path):
+    consumer_file = tmp_path / "consumer.py"
+    consumer_code = """
+from provider import target
+
+def run():
+    target()
+"""
+    consumer_file.write_text(consumer_code, encoding="utf-8")
+
+    state = RepositoryAnalysisState(
+        modules={
+            "consumer": Module("consumer", "consumer.py", str(consumer_file), ["provider"]),
+        },
+        module_usages={
+            "consumer": ModuleUsageFacts(
+                symbol_calls_materialized=True,
+                reference_evidence=(),
+                reference_evidence_materialized=False,
+            )
+        },
+    )
+
+    ensure_module_usages(state)
+
+    facts = state.module_usages["consumer"]
+    assert facts.symbol_calls_materialized is True
+    assert facts.reference_evidence_materialized is True
+    assert len(facts.reference_evidence) > 0
+    assert any(ev[0].endswith("target") for ev in facts.reference_evidence)
+
+
+def test_legacy_reference_evidence_triggers_single_extraction(tmp_path):
+    consumer_file = tmp_path / "consumer.py"
+    consumer_file.write_text("def run(): pass\n", encoding="utf-8")
+
+    state = RepositoryAnalysisState(
+        modules={
+            "consumer": Module("consumer", "consumer.py", str(consumer_file), []),
+        },
+        module_usages={
+            "consumer": ModuleUsageFacts(
+                symbol_calls_materialized=True,
+                reference_evidence=(),
+                reference_evidence_materialized=False,
+            )
+        },
+    )
+
+    with patch(
+        "contextor.core.reference.engine.extract_module_usage_facts",
+        wraps=extract_module_usage_facts,
+    ) as extract_spy:
+        ensure_module_usages(state)
+
+    assert extract_spy.call_count == 1
+    assert state.module_usages["consumer"].reference_evidence_materialized is True
+
+
+def test_current_module_usages_untouched_during_legacy_upgrade(tmp_path):
+    legacy_file = tmp_path / "legacy.py"
+    legacy_file.write_text("def leg(): pass\n", encoding="utf-8")
+
+    current_file = tmp_path / "current.py"
+    current_file.write_text("def curr(): pass\n", encoding="utf-8")
+
+    current_facts = ModuleUsageFacts(
+        symbol_calls_materialized=True,
+        reference_evidence=(("current.curr", "direct_calls", "", 1),),
+        reference_evidence_materialized=True,
+    )
+
+    state = RepositoryAnalysisState(
+        modules={
+            "legacy": Module("legacy", "legacy.py", str(legacy_file), []),
+            "current": Module("current", "current.py", str(current_file), []),
+        },
+        module_usages={
+            "legacy": ModuleUsageFacts(
+                symbol_calls_materialized=True,
+                reference_evidence=(),
+                reference_evidence_materialized=False,
+            ),
+            "current": current_facts,
+        },
+    )
+
+    with patch(
+        "contextor.core.reference.engine.extract_module_usage_facts",
+        wraps=extract_module_usage_facts,
+    ) as extract_spy:
+        ensure_module_usages(state)
+
+    assert extract_spy.call_count == 1
+    assert extract_spy.call_args[0][0] == "legacy"
+    assert state.module_usages["current"] is current_facts
+    assert state.module_usages["legacy"].reference_evidence_materialized is True
+
+
+def test_old_pickled_or_dict_shape_detected_and_upgraded(tmp_path):
+    source = tmp_path / "sample.py"
+    source.write_text("from lib import func\ndef caller(): func()\n", encoding="utf-8")
+
+    # Simulate old object where reference_evidence and reference_evidence_materialized are absent in dict
+    old_facts = ModuleUsageFacts(
+        imports=("lib",),
+        direct_calls=("lib.func",),
+        symbol_calls_materialized=True,
+    )
+    object.__delattr__(old_facts, "reference_evidence_materialized")
+    if "reference_evidence" in vars(old_facts):
+        object.__delattr__(old_facts, "reference_evidence")
+
+    state = RepositoryAnalysisState(
+        modules={
+            "sample": Module("sample", "sample.py", str(source), ["lib"]),
+        },
+        module_usages={
+            "sample": old_facts,
+        },
+    )
+
+    assert module_usages_require_materialization(state) is True
+
+    ensure_module_usages(state)
+
+    upgraded = state.module_usages["sample"]
+    assert upgraded.symbol_calls_materialized is True
+    assert upgraded.reference_evidence_materialized is True
+    assert len(upgraded.reference_evidence) > 0
+
+
+def test_hydration_legacy_module_usages_authoritative_upgrade_and_roundtrip(tmp_path):
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.live_state.hydration import hydrate_repository_engine
+    from contextor.core.paths import repo_cache_dir
+    from contextor.core.analysis.state_manager import save_engine_state
+    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+    from contextor.core.single_file.single_file_analysis import collect_all_contexts
+
+    repo_root = tmp_path / "repo"
+    pkg = repo_root / "pkg"
+    pkg.mkdir(parents=True)
+    (pkg / "__init__.py").write_text("", encoding="utf-8")
+
+    provider_code = """
+def target():
+    return 42
+"""
+    (pkg / "provider.py").write_text(provider_code, encoding="utf-8")
+
+    consumer_code = """
+from pkg.provider import target
+
+def run():
+    return target()
+"""
+    (pkg / "consumer.py").write_text(consumer_code, encoding="utf-8")
+
+    # Step 1: Initial normal analysis to establish repository identity and valid graph
+    ContextorFacade.analyze_project(str(repo_root))
+    cache_dir = repo_cache_dir(repo_root)
+    registry = PersistentIdentityRegistry(str(repo_root))
+
+    # Hydrate to obtain current state object
+    initial_hydrated = hydrate_repository_engine(str(repo_root))
+    assert initial_hydrated is not None
+    state = initial_hydrated.engine.state
+
+    # Mutate consumer facts to simulate legacy state: symbol_calls_materialized=True, reference_evidence_materialized=False
+    legacy_facts = ModuleUsageFacts(
+        imports=("pkg.provider",),
+        symbol_calls_materialized=True,
+        reference_evidence=(),
+        reference_evidence_materialized=False,
+    )
+    state.module_usages["pkg.consumer"] = legacy_facts
+
+    # Save this legacy snapshot into the canonical live snapshot location
+    save_engine_state(
+        state,
+        str(cache_dir),
+        "legacy_h2b_state",
+        writer="desktop",
+        repo_id=registry.repo_id,
+        root_path=str(repo_root),
+    )
+
+    # Step 2: FIRST PRODUCTION HYDRATION
+    with patch(
+        "contextor.core.reference.engine.extract_module_usage_facts",
+        wraps=extract_module_usage_facts,
+    ) as extract_spy:
+        hydrated_1 = hydrate_repository_engine(str(repo_root))
+
+    assert hydrated_1 is not None
+    assert extract_spy.call_count == 1
+    assert extract_spy.call_args[0][0] == "pkg.consumer"
+
+    facts_1 = hydrated_1.engine.state.module_usages["pkg.consumer"]
+    assert facts_1.symbol_calls_materialized is True
+    assert facts_1.reference_evidence_materialized is True
+    assert len(facts_1.reference_evidence) > 0
+    assert any(ev[0].endswith("target") for ev in facts_1.reference_evidence)
+
+    # Step 3: Persist the upgraded state through normal product contract
+    save_engine_state(
+        hydrated_1.engine.state,
+        str(cache_dir),
+        "upgraded_h2b_state",
+        writer="desktop",
+        repo_id=registry.repo_id,
+        root_path=str(repo_root),
+    )
+
+    # Step 4: SECOND PRODUCTION HYDRATION
+    with patch(
+        "contextor.core.reference.engine.extract_module_usage_facts",
+        wraps=extract_module_usage_facts,
+    ) as extract_spy_2:
+        hydrated_2 = hydrate_repository_engine(str(repo_root))
+
+    assert hydrated_2 is not None
+    assert extract_spy_2.call_count == 0
+
+    facts_2 = hydrated_2.engine.state.module_usages["pkg.consumer"]
+    assert facts_2.reference_evidence_materialized is True
+    assert facts_2.reference_evidence == facts_1.reference_evidence
+    assert module_usages_require_materialization(hydrated_2.engine.state) is False
+
+    # Step 5: AFTER SECOND HYDRATION — SINGLE FILE CANONICAL REFERENCE PATH
+    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references") as legacy_ref_spy:
+        provider_file = str(pkg / "provider.py")
+        res = collect_all_contexts(
+            provider_file,
+            hydrated_2.engine.state.modules,
+            hydrated_2.engine.state.dependency_graph,
+            root_path=str(repo_root),
+            engine_state=hydrated_2.engine.state,
+        )
+        assert not legacy_ref_spy.called, "build_symbol_references must NOT be called after hydration upgrade"
+
+    sym_ctx = res.get("symbol_context", {})
+    assert "references" in sym_ctx
+    assert "target" in sym_ctx["references"]
+    assert "pkg.consumer" in sym_ctx["references"]["target"]["called_by"]

diff --git a/tests/test_canonical_reference_projection.py b/tests/test_canonical_reference_projection.py
new file mode 100644
index 0000000..f6b64d3
--- /dev/null
+++ b/tests/test_canonical_reference_projection.py
@@ -0,0 +1,586 @@
+import ast
+import builtins
+import copy
+from pathlib import Path
+import tempfile
+from unittest.mock import patch, MagicMock
+
+import pytest
+
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.reference.engine import (
+    build_symbol_references,
+    build_symbol_references_from_canonical,
+    CanonicalReferenceEvidenceUnavailable,
+)
+from contextor.core.single_file.single_file_analysis import collect_all_contexts
+from contextor.core.api.api_consumers import extract_api_consumers, summarize_api_consumers
+
+
+@pytest.fixture
+def multi_channel_repo():
+    with tempfile.TemporaryDirectory() as td:
+        root = Path(td)
+        pkg = root / "pkg"
+        pkg.mkdir()
+        (pkg / "__init__.py").write_text("", encoding="utf-8")
+
+        provider_code = """
+class BaseService:
+    def base_method(self):
+        pass
+
+class Worker:
+    def run(self):
+        pass
+
+def compute_sum(a, b):
+    return a + b
+
+def execute_callback(cb):
+    pass
+
+def on_custom_event(data):
+    pass
+
+GLOBAL_CONFIG = {"key": "val"}
+UNUSED_PROVIDER_SYM = 42
+"""
+        (pkg / "provider.py").write_text(provider_code, encoding="utf-8")
+
+        consumer_a_code = """
+from pkg.provider import BaseService, Worker, compute_sum, execute_callback, on_custom_event, GLOBAL_CONFIG
+import pkg.provider as p
+
+class ConcreteService(BaseService):
+    def handle(self):
+        self.base_method()
+
+def run_consumer_a():
+    res = compute_sum(1, 2)
+    def my_cb(): pass
+    execute_callback(callback=my_cb)
+    cfg = p.GLOBAL_CONFIG
+"""
+        (pkg / "consumer_a.py").write_text(consumer_a_code, encoding="utf-8")
+
+        consumer_b_code = """
+import pkg.provider as prov
+
+class EventBroker:
+    def bind(self, event_name, handler):
+        pass
+
+def setup_events():
+    b = EventBroker()
+    b.bind("action", prov.on_custom_event)
+    w = prov.Worker()
+    getattr(prov, "compute_sum")(10, 20)
+"""
+        (pkg / "consumer_b.py").write_text(consumer_b_code, encoding="utf-8")
+
+        from contextor.core.graph.graph import build_graph
+
+        ContextorFacade.analyze_project(td)
+        hydrated = hydrate_repository_engine(td)
+        state = hydrated.engine.state
+        graph = build_graph(state.modules)
+
+        yield td, state, graph
+
+
+def test_golden_parity_matrix(multi_channel_repo):
+    td, state, graph = multi_channel_repo
+    symbols = [
+        "BaseService",
+        "Worker",
+        "compute_sum",
+        "execute_callback",
+        "on_custom_event",
+        "GLOBAL_CONFIG",
+        "UNUSED_PROVIDER_SYM",
+    ]
+
+    legacy = build_symbol_references(
+        state.modules,
+        symbols,
+        td,
+        definer_module="pkg.provider",
+    )
+
+    current_modules = {
+        m
+        for m in state.modules
+        if getattr(state, "artifacts", {}).get(m, {}).get("is_valid", True)
+    }
+
+    canonical = build_symbol_references_from_canonical(
+        definer_module="pkg.provider",
+        symbols=symbols,
+        artifact_consumption=state.artifact_consumption,
+        module_usages=state.module_usages,
+        current_modules=current_modules,
+    )
+
+    # Explicit assertion that called_by_ambiguous is populated from consumer_b
+    assert "pkg.consumer_b" in legacy["compute_sum"]["called_by_ambiguous"]
+    assert len(legacy["compute_sum"]["called_by_ambiguous_detail"]) > 0
+    assert canonical["compute_sum"]["called_by_ambiguous"] == legacy["compute_sum"]["called_by_ambiguous"]
+    assert canonical["compute_sum"]["called_by_ambiguous_detail"] == legacy["compute_sum"]["called_by_ambiguous_detail"]
+
+    assert canonical == legacy, f"Mismatch:\nCanonical: {canonical}\nLegacy: {legacy}"
+
+    # Downstream consumers parity
+    legacy_consumers = extract_api_consumers(symbols, legacy)
+    canonical_consumers = extract_api_consumers(symbols, canonical)
+    assert canonical_consumers == legacy_consumers
+
+    assert summarize_api_consumers(canonical_consumers) == summarize_api_consumers(legacy_consumers)
+
+
+def test_zero_io_and_zero_ast_parses_during_canonical_projection(multi_channel_repo):
+    td, state, graph = multi_channel_repo
+    symbols = [
+        "BaseService",
+        "Worker",
+        "compute_sum",
+        "execute_callback",
+        "on_custom_event",
+        "GLOBAL_CONFIG",
+        "UNUSED_PROVIDER_SYM",
+    ]
+
+    current_consumers = set(state.module_usages.keys())
+
+    original_open = builtins.open
+    original_read_text = Path.read_text
+    original_parse = ast.parse
+
+    io_tracker = {"opens": 0, "read_text": 0, "parses": 0}
+
+    def guarded_open(*args, **kwargs):
+        io_tracker["opens"] += 1
+        return original_open(*args, **kwargs)
+
+    def guarded_read_text(*args, **kwargs):
+        io_tracker["read_text"] += 1
+        return original_read_text(*args, **kwargs)
+
+    def guarded_parse(*args, **kwargs):
+        io_tracker["parses"] += 1
+        return original_parse(*args, **kwargs)
+
+    with patch("builtins.open", side_effect=guarded_open), \
+         patch("pathlib.Path.read_text", side_effect=guarded_read_text), \
+         patch("ast.parse", side_effect=guarded_parse):
+
+        canonical = build_symbol_references_from_canonical(
+            definer_module="pkg.provider",
+            symbols=symbols,
+            artifact_consumption=state.artifact_consumption,
+            module_usages=state.module_usages,
+            current_modules=current_consumers,
+        )
+
+    assert io_tracker["opens"] == 0
+    assert io_tracker["read_text"] == 0
+    assert io_tracker["parses"] == 0
+    assert "compute_sum" in canonical
+
+
+def test_single_file_builder_uses_canonical_references(multi_channel_repo):
+    td, state, graph = multi_channel_repo
+    provider_file = str(Path(td) / "pkg" / "provider.py")
+
+    with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references") as legacy_spy:
+        res = collect_all_contexts(
+            provider_file,
+            state.modules,
+            graph,
+            root_path=td,
+            engine_state=state,
+        )
+        assert not legacy_spy.called, "build_symbol_references should NOT have been called when canonical state is fresh"
+
+    sym_ctx = res.get("symbol_context", {})
+    assert "references" in sym_ctx
+    assert "compute_sum" in sym_ctx["references"]
+    assert "pkg.consumer_a" in sym_ctx["references"]["compute_sum"]["called_by"]
+
+
+def test_fallback_when_artifact_consumption_deferred(multi_channel_repo):
+    td, state, graph = multi_channel_repo
+    provider_file = str(Path(td) / "pkg" / "provider.py")
+
     # Clone state with deferred consumption
     deferred_state = copy.copy(state)
     object.__setattr__(deferred_state, "artifact_consumption_state", "deferred")

     with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
         res = collect_all_contexts(
             provider_file,
             state.modules,
             graph,
             root_path=td,
             engine_state=deferred_state,
         )
         assert legacy_spy.called, "build_symbol_references MUST be called when artifact_consumption_state != 'fresh'"

     sym_ctx = res.get("symbol_context", {})
     assert "references" in sym_ctx
     assert "compute_sum" in sym_ctx["references"]


def test_fallback_when_consumer_is_not_current(multi_channel_repo):
     td, state, graph = multi_channel_repo
     symbols = ["compute_sum"]

     # Provide current_modules that excludes confirmed consumer pkg.consumer_a
     current_consumers = {"pkg.consumer_b"}

     with pytest.raises(CanonicalReferenceEvidenceUnavailable):
         build_symbol_references_from_canonical(
             definer_module="pkg.provider",
             symbols=symbols,
             artifact_consumption=state.artifact_consumption,
             module_usages=state.module_usages,
             current_modules=current_consumers,
         )


def test_fallback_when_consumer_facts_missing(multi_channel_repo):
     td, state, graph = multi_channel_repo
     symbols = ["compute_sum"]

     incomplete_usages = {
         k: v for k, v in state.module_usages.items() if k != "pkg.consumer_a"
     }

     with pytest.raises(CanonicalReferenceEvidenceUnavailable):
         build_symbol_references_from_canonical(
             definer_module="pkg.provider",
             symbols=symbols,
             artifact_consumption=state.artifact_consumption,
             module_usages=incomplete_usages,
             current_modules=set(state.module_usages.keys()),
         )


def test_visitor_instance_method_candidate_and_resolver_semantics():
     from contextor.core.reference.visitor import SymbolReferenceVisitor

     visitor = SymbolReferenceVisitor(
         target_symbols={"KnownClass.valid_method"},
         current_module="pkg.consumer",
     )
     visitor.instances["srv"] = "KnownClass"

     # Case A: Candidate matches an untargeted method
     candidate = visitor._instance_method_candidate("srv.untargeted_method")
     assert candidate == "KnownClass.untargeted_method"
     # Legacy resolver must return None because it is NOT in target_symbols
     assert visitor._resolve_instance_method("srv.untargeted_method") is None

     # Case B: Candidate matches a targeted method
     candidate_targeted = visitor._instance_method_candidate("srv.valid_method")
     assert candidate_targeted == "KnownClass.valid_method"
     # Legacy resolver returns the candidate because it IS in target_symbols
     assert visitor._resolve_instance_method("srv.valid_method") == "KnownClass.valid_method"


def test_old_snapshot_dict_unmaterialized_fails_closed(multi_channel_repo):
     from contextor.core.domain.usage_facts import ModuleUsageFacts

     td, state, graph = multi_channel_repo
     symbols = ["compute_sum"]

     legacy_dict = {
         "imports": ["pkg.provider"],
         "direct_calls": ["pkg.provider.compute_sum"],
         "runtime_calls": [],
         "callback_calls": [],
         "event_bindings": [],
         "inheritance_refs": [],
         "qualified_refs": [],
         "aliases": [],
         "symbol_calls": [],
         "symbol_calls_materialized": True,
         # Intentionally omitting reference_evidence and reference_evidence_materialized
     }

     old_facts = ModuleUsageFacts.from_dict(legacy_dict)
     assert old_facts.reference_evidence == ()
     assert old_facts.reference_evidence_materialized is False

     mock_usages = dict(state.module_usages)
     mock_usages["pkg.consumer_a"] = old_facts

     with pytest.raises(CanonicalReferenceEvidenceUnavailable) as exc_info:
         build_symbol_references_from_canonical(
             definer_module="pkg.provider",
             symbols=symbols,
             artifact_consumption=state.artifact_consumption,
             module_usages=mock_usages,
             current_modules=set(state.module_usages.keys()),
         )
     assert "Reference evidence not materialized" in str(exc_info.value)


def test_empty_current_evidence_is_distinguished_from_unmaterialized(multi_channel_repo):
     from contextor.core.domain.usage_facts import ModuleUsageFacts

     td, state, graph = multi_channel_repo
     symbols = ["compute_sum"]

     empty_materialized_facts = ModuleUsageFacts(
         imports=("pkg.provider",),
         direct_calls=(),
         runtime_calls=(),
         callback_calls=(),
         event_bindings=(),
         inheritance_refs=(),
         qualified_refs=(),
         aliases=(),
         symbol_calls=(),
         symbol_calls_materialized=True,
         reference_evidence=(),
         reference_evidence_materialized=True,
     )

     mock_usages = dict(state.module_usages)
     mock_usages["pkg.consumer_a"] = empty_materialized_facts

     # When materialized is True, it does NOT raise CanonicalReferenceEvidenceUnavailable
     res = build_symbol_references_from_canonical(
         definer_module="pkg.provider",
         symbols=symbols,
         artifact_consumption=state.artifact_consumption,
         module_usages=mock_usages,
         current_modules=set(state.module_usages.keys()),
     )
     assert "compute_sum" in res


def test_single_file_builder_fallback_on_unmaterialized_consumer_evidence(multi_channel_repo):
     from contextor.core.domain.usage_facts import ModuleUsageFacts

     td, state, graph = multi_channel_repo
     provider_file = str(Path(td) / "pkg" / "provider.py")

     unmaterialized_facts = ModuleUsageFacts(
         imports=("pkg.provider",),
         direct_calls=("pkg.provider.compute_sum",),
         runtime_calls=(),
         callback_calls=(),
         event_bindings=(),
         inheritance_refs=(),
         qualified_refs=(),
         aliases=(),
         symbol_calls=(),
         symbol_calls_materialized=True,
         reference_evidence=(),
         reference_evidence_materialized=False,
     )

     unmaterialized_state = copy.copy(state)
     mock_usages = dict(state.module_usages)
     mock_usages["pkg.consumer_a"] = unmaterialized_facts
     object.__setattr__(unmaterialized_state, "module_usages", mock_usages)

     with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
         res = collect_all_contexts(
             provider_file,
             state.modules,
             graph,
             root_path=td,
             engine_state=unmaterialized_state,
         )
         assert legacy_spy.called, "build_symbol_references MUST be called when consumer evidence is not materialized"

     sym_ctx = res.get("symbol_context", {})
     assert "references" in sym_ctx
     assert "compute_sum" in sym_ctx["references"]


def test_module_usage_facts_serialization_roundtrip_and_backward_compat():
     from contextor.core.domain.usage_facts import ModuleUsageFacts

     # 1. Roundtrip populated facts
     facts = ModuleUsageFacts(
         imports=("pkg.provider",),
         direct_calls=("pkg.provider.compute_sum",),
         reference_evidence=(
             ("pkg.provider.compute_sum", "direct_calls", "caller_func", 42),
         ),
         reference_evidence_materialized=True,
     )
     data = facts.to_dict()
     assert data["reference_evidence_materialized"] is True
     assert len(data["reference_evidence"]) == 1
     assert data["reference_evidence"][0]["line"] == 42

     restored = ModuleUsageFacts.from_dict(data)
     assert restored.reference_evidence == facts.reference_evidence
     assert restored.reference_evidence_materialized is True

     # 2. Roundtrip empty facts with materialized True
     empty_facts = ModuleUsageFacts(
         reference_evidence=(),
         reference_evidence_materialized=True,
     )
     empty_data = empty_facts.to_dict()
     assert empty_data["reference_evidence_materialized"] is True
     restored_empty = ModuleUsageFacts.from_dict(empty_data)
     assert restored_empty.reference_evidence == ()
     assert restored_empty.reference_evidence_materialized is True

     # 3. Old dict without reference_evidence_materialized
     old_data = {"imports": ["foo"]}
     old_restored = ModuleUsageFacts.from_dict(old_data)
     assert old_restored.reference_evidence == ()
     assert old_restored.reference_evidence_materialized is False

     # 4. Attribute fallback for objects restored without field in __dict__
     bare_obj = object.__new__(ModuleUsageFacts)
     assert bare_obj.reference_evidence == ()
     assert bare_obj.reference_evidence_materialized is False


def test_incremental_update_file_materializes_reference_evidence(multi_channel_repo):
     td, state, graph = multi_channel_repo

     hydrated = hydrate_repository_engine(td)
     engine = hydrated.engine

     # Check that initial analysis marked module_usages as materialized
     assert engine.state.module_usages["pkg.consumer_a"].reference_evidence_materialized is True

     # Update consumer_a.py on disk
     consumer_a_path = str(Path(td) / "pkg" / "consumer_a.py")
     updated_code = """
from pkg.provider import compute_sum

def run_updated():
    compute_sum(100, 200)
"""
     Path(consumer_a_path).write_text(updated_code, encoding="utf-8")
     engine.update_file(consumer_a_path)

     updated_facts = engine.state.module_usages["pkg.consumer_a"]
     assert updated_facts.reference_evidence_materialized is True
     assert any(ev[0].endswith("compute_sum") for ev in updated_facts.reference_evidence)


def test_unmaterialized_unconfirmed_current_module_forces_fallback(multi_channel_repo):
     from contextor.core.domain.usage_facts import ModuleUsageFacts

     td, state, graph = multi_channel_repo
     provider_file = str(Path(td) / "pkg" / "provider.py")

     # pkg.__init__ is current in repository, but not a confirmed consumer of provider
     unmaterialized_unrelated = ModuleUsageFacts(
         imports=(),
         direct_calls=(),
         runtime_calls=(),
         callback_calls=(),
         event_bindings=(),
         inheritance_refs=(),
         qualified_refs=(),
         aliases=(),
         symbol_calls=(),
         symbol_calls_materialized=True,
         reference_evidence=(),
         reference_evidence_materialized=False,
     )

     mutated_state = copy.copy(state)
     mock_usages = dict(state.module_usages)
     mock_usages["pkg.__init__"] = unmaterialized_unrelated
     object.__setattr__(mutated_state, "module_usages", mock_usages)

     with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
         res = collect_all_contexts(
             provider_file,
             state.modules,
             graph,
             root_path=td,
             engine_state=mutated_state,
         )
         assert legacy_spy.called, "build_symbol_references MUST be called when any current module evidence is unmaterialized"


def test_missing_usage_for_unconfirmed_current_module_forces_fallback(multi_channel_repo):
     td, state, graph = multi_channel_repo
     provider_file = str(Path(td) / "pkg" / "provider.py")

     # Remove pkg.__init__ (a current module not consuming provider) from module_usages
     mutated_state = copy.copy(state)
     mock_usages = {k: v for k, v in state.module_usages.items() if k != "pkg.__init__"}
     object.__setattr__(mutated_state, "module_usages", mock_usages)

     with patch("contextor.core.single_file.builders.layer0_builders.build_symbol_references", wraps=build_symbol_references) as legacy_spy:
         res = collect_all_contexts(
             provider_file,
             state.modules,
             graph,
             root_path=td,
             engine_state=mutated_state,
         )
         assert legacy_spy.called, "build_symbol_references MUST be called when a current module is missing module_usages"


def test_direct_projector_ambiguous_completeness(multi_channel_repo):
     from contextor.core.domain.usage_facts import ModuleUsageFacts

     td, state, graph = multi_channel_repo
     symbols = ["compute_sum"]

     current_modules = {"pkg.provider", "pkg.consumer_a", "pkg.unrelated"}

     # 1. Missing module_usages for unrelated current module
     incomplete_usages = dict(state.module_usages)
     incomplete_usages.pop("pkg.unrelated", None)

     with pytest.raises(CanonicalReferenceEvidenceUnavailable) as exc_info:
         build_symbol_references_from_canonical(
             definer_module="pkg.provider",
             symbols=symbols,
             artifact_consumption=state.artifact_consumption,
             module_usages=incomplete_usages,
             current_modules=current_modules,
         )
     assert "Missing module_usages for current module pkg.unrelated" in str(exc_info.value)

     # 2. Unmaterialized facts for unrelated current module
     unmaterialized_usages = dict(state.module_usages)
     unmaterialized_usages["pkg.unrelated"] = ModuleUsageFacts(
         reference_evidence=(),
         reference_evidence_materialized=False,
     )

     with pytest.raises(CanonicalReferenceEvidenceUnavailable) as exc_info:
         build_symbol_references_from_canonical(
             definer_module="pkg.provider",
             symbols=symbols,
             artifact_consumption=state.artifact_consumption,
             module_usages=unmaterialized_usages,
             current_modules=current_modules,
         )
     assert "Reference evidence not materialized for current module pkg.unrelated" in str(exc_info.value)

     # 3. Materialized empty facts for unrelated current module
     materialized_usages = dict(state.module_usages)
     materialized_usages["pkg.unrelated"] = ModuleUsageFacts(
         reference_evidence=(),
         reference_evidence_materialized=True,
     )

     res = build_symbol_references_from_canonical(
         definer_module="pkg.provider",
         symbols=symbols,
         artifact_consumption=state.artifact_consumption,
         module_usages=materialized_usages,
         current_modules=current_modules,
     )
     assert "compute_sum" in res
```
