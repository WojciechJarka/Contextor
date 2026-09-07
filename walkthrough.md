# Canonical class-scope artifact fix — implementation report

ROOT_FIX=`contextor/core/symbol_engine/extractor.py`, `SymbolVisitor.visit_Assign` and `SymbolVisitor.visit_AnnAssign`.

PRODUCTION_FILES_CHANGED=`contextor/core/symbol_engine/extractor.py`

MODULE_SCOPE_RULE=`function_depth == 0 and not class_stack`; only this scope adds names to `facts.globals`.

FUNCTION_LOCAL_BEHAVIOR=UNCHANGED. Function-local assignments remain absent from `facts.globals`.

CLASS_SCOPE_BEHAVIOR=Class-body `Assign` and `AnnAssign` names remain in `facts.assignments` but are excluded from `facts.globals`; no `Class.field` artifacts are introduced.

DATACLASS_FIELD_BEHAVIOR=Dataclass fields are excluded from `facts.globals` by ordinary scope only; no `ClassVar` or dataclass-specific recognition was added.

NESTED_SCOPE_BEHAVIOR=Module classes, nested classes in module classes, and classes inside functions do not contribute class-body assignments to `facts.globals`.

EXTRACTOR_TESTS=`tests/test_symbol_extractor_semantics.py` — focused module/class/dataclass/function-local assignment coverage plus nested-scope regression. PASS.

ARTIFACT_MATERIALIZATION_TESTS=`tests/test_artifact_report.py::test_class_fields_are_not_materialized_as_artifacts` — real module global, class, and method remain materialized; dataclass fields do not. PASS.

FULL_INCREMENTAL_PARITY=`tests/test_incremental_equivalence.py::test_incremental_full_parity_excludes_class_fields_and_retires_stale_identity` — full `bootstrap_state` own-symbol set equals `prepare_source_update` own-symbol set; class fields absent. PASS.

REGISTRY_SYNC_TEST=The same incremental-equivalence regression syncs a pre-existing `a::field` identity against the corrected desired identity set and asserts it is no longer active. PASS.

TARGET_CURRENT_CANONICAL_COUNT=48 (pre-existing canonical state; not modified by this implementation).

TARGET_EXPECTED_POST_REANALYSIS_COUNT=39.

TARGET_FALSE_GLOBALS_REMOVED=9: `artifact_data_identity`, `artifact_keys`, `clusters`, `complete`, `max_cluster_size`, `min_cluster_size`, `min_jaccard`, `raw_artifact_keys`, `scope`.

TARGET_REAL_GLOBALS_PRESERVED=`_CALL_USAGE_CHANNELS`, `_IMPORT_USAGE_CHANNELS`, `_INHERITANCE_USAGE_CHANNELS`, `_LAYER_RULES`, `__all__`.

DIRECT_STATIC_PROOF=Production extractor/materialization logic over the current `contextor/core/reporting_engine/graph_analytics.py` returned 39 artifacts and exactly the five real module globals above. No MCP state was refreshed.

REPO_WIDE_CURRENT_FALSE_GLOBALS=342

REPO_WIDE_EXPECTED_GLOBAL_COUNT_AFTER_REANALYSIS=319

DOCS_REVIEWED=Public API/canonical-state contract and artifact materialization contract reviewed. They describe `class`, `function`, `method`, and `global`; they do not promise class-field artifacts.

DOCS_CHANGED=NO

MCP_RESTART_REQUIRED=YES

LIVE_RUNTIME_RELOAD_REQUIRED=YES

FULL_REANALYSIS_REQUIRED=YES

RUNTIME_CERTIFICATION_PENDING=YES

TESTS=`tests/test_symbol_extractor_semantics.py`, `tests/test_artifact_report.py`, `tests/test_incremental_equivalence.py`: 23 passed. `tests/test_canonical_state_contract.py`: 33 passed, 1 existing dependency deprecation warning.

DECISION=READY_FOR_RUNTIME_RELOAD

FULL_SUITE_RUN_BY_AGENT=NO

FILES_CHANGED=

- `contextor/core/symbol_engine/extractor.py`
- `tests/test_symbol_extractor_semantics.py`
- `tests/test_artifact_report.py`
- `tests/test_incremental_equivalence.py`

walkthrough.md is the reporting file and is not included in `FILES_CHANGED`.

## Complete raw unified diff

```diff
diff --git a/contextor/core/symbol_engine/extractor.py b/contextor/core/symbol_engine/extractor.py
index ef2fbbd..14455dd 100644
--- a/contextor/core/symbol_engine/extractor.py
+++ b/contextor/core/symbol_engine/extractor.py
@@ -108,14 +108,16 @@ class SymbolVisitor(ast.NodeVisitor):
         if self.function_depth == 0:
             for target in node.targets:
                 if isinstance(target, ast.Name):
-                    self.facts.globals.add(target.id)
                     self.facts.assignments.add(target.id)
+                    if not self.class_stack:
+                        self.facts.globals.add(target.id)
         self.generic_visit(node)
 
     def visit_AnnAssign(self, node):
         if self.function_depth == 0 and isinstance(node.target, ast.Name):
-            self.facts.globals.add(node.target.id)
             self.facts.assignments.add(node.target.id)
+            if not self.class_stack:
+                self.facts.globals.add(node.target.id)
         self.generic_visit(node)
 
     def visit_Call(self, node):
diff --git a/tests/test_artifact_report.py b/tests/test_artifact_report.py
index 961721f..b3d975e 100644
--- a/tests/test_artifact_report.py
+++ b/tests/test_artifact_report.py
@@ -78,6 +78,43 @@ def test_all_defined_symbols_receive_collision_free_qualified_identities(tmp_pat
     assert registry.get_artifact_id("pkg.first::unused") is not None
     assert registry.get_artifact_id("run") is None
 
+
+def test_class_fields_are_not_materialized_as_artifacts(tmp_path, isolated_dirs):
+    (tmp_path / "producer.py").write_text(
+        "from dataclasses import dataclass\n"
+        "\n"
+        "MODULE_GLOBAL = 1\n"
+        "\n"
+        "@dataclass\n"
+        "class Data:\n"
+        "    field: int\n"
+        "    default: int = 0\n"
+        "\n"
+        "    def method(self):\n"
+        "        return MODULE_GLOBAL\n",
+        encoding="utf-8",
+    )
+    (tmp_path / "consumer.py").write_text(
+        "from producer import Data, MODULE_GLOBAL\n"
+        "\n"
+        "def use():\n"
+        "    item = Data(1)\n"
+        "    return MODULE_GLOBAL + item.method()\n",
+        encoding="utf-8",
+    )
+
+    modules = build_index(str(tmp_path))
+    report = generate_artifact_usage_report(modules, str(tmp_path))
+    artifacts = report["artifacts"]
+
+    assert "producer::MODULE_GLOBAL" in artifacts
+    assert "producer::Data" in artifacts
+    assert "producer::Data.method" in artifacts
+    assert not {
+        "producer::field",
+        "producer::default",
+    } & artifacts.keys()
+
 from contextor.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report
 
 def test_usage_sidecar_and_filtering(sample_repo, isolated_dirs):
diff --git a/tests/test_incremental_equivalence.py b/tests/test_incremental_equivalence.py
index 57df4c6..cf90f27 100644
--- a/tests/test_incremental_equivalence.py
+++ b/tests/test_incremental_equivalence.py
@@ -143,6 +143,82 @@ def test_incremental_update_synchronizes_qualified_artifact_registry(tmp_path):
     assert registry.get_artifact_id("bar") is None
 
 
+def test_incremental_full_parity_excludes_class_fields_and_retires_stale_identity(
+    tmp_path,
+):
+    repo_dir = tmp_path / "repo"
+    repo_dir.mkdir()
+    target = repo_dir / "a.py"
+    target.write_text(
+        "MODULE_GLOBAL = 1\n"
+        "\n"
+        "class Data:\n"
+        "    field: int\n"
+        "    default: int = 0\n"
+        "\n"
+        "    def method(self):\n"
+        "        return MODULE_GLOBAL\n",
+        encoding="utf-8",
+    )
+
+    registry = PersistentIdentityRegistry(str(repo_dir))
+    state = bootstrap_state(repo_dir, registry)
+    with registry.transaction():
+        registry.sync_with_workspace(
+            {"a"},
+            {
+                "a::MODULE_GLOBAL",
+                "a::Data",
+                "a::Data.method",
+                "a::field",
+            },
+        )
+    target.write_text(
+        "MODULE_GLOBAL = 2\n"
+        "NEW_GLOBAL = 3\n"
+        "\n"
+        "class Data:\n"
+        "    field: int\n"
+        "    default: int = 1\n"
+        "\n"
+        "    def method(self):\n"
+        "        return MODULE_GLOBAL\n",
+        encoding="utf-8",
+    )
+
+    registry_baseline = PersistentIdentityRegistry(str(repo_dir))
+    full_state = bootstrap_state(repo_dir, registry_baseline)
+
+    from contextor.core.analysis.incremental.preparation import prepare_source_update
+
+    prepared = prepare_source_update(
+        target,
+        "a",
+        is_new=False,
+        old_module=state.modules["a"],
+        old_artifacts=state.artifacts["a"],
+        old_usage=getattr(state, "module_usages", {}).get("a"),
+    )
+    assert not prepared.has_error
+    assert set(prepared.new_artifacts["own_symbols"]) == set(
+        full_state.artifacts["a"]["own_symbols"]
+    )
+
+    expected_symbols = {"MODULE_GLOBAL", "NEW_GLOBAL", "Data", "Data.method"}
+    assert set(prepared.new_artifacts["own_symbols"]) == expected_symbols
+
+    from contextor.core.reporting_layer.artifact_usage_report import (
+        collect_qualified_artifact_identities,
+    )
+
+    with registry.transaction():
+        registry.sync_with_workspace(
+            set(full_state.modules),
+            collect_qualified_artifact_identities(full_state.artifacts),
+        )
+    assert registry.get_artifact_id("a::field") is None
+
 
 def test_incremental_update_allocates_qualified_identity_for_new_symbol(tmp_path):
     repo_dir = tmp_path / "repo"
     repo_dir.mkdir()
     target = repo_dir / "a.py"
     target.write_text("def existing():\n    return 1\n", encoding="utf-8")
diff --git a/tests/test_symbol_extractor_semantics.py b/tests/test_symbol_extractor_semantics.py
index 19652a6..ff47678 100644
--- a/tests/test_symbol_extractor_semantics.py
+++ b/tests/test_symbol_extractor_semantics.py
@@ -38,3 +38,99 @@ def test_decorated_signatures_exclude_decorators_and_nested_defs_are_not_artifac
         "Service.run": "async def run(cls, item: str) -> None",
     }
     assert all("@" not in signature for signature in facts.signatures.values())
+
+
+def test_assignments_are_globals_only_at_module_scope(tmp_path):
+    source = tmp_path / "scope_fixture.py"
+    source.write_text(
+        "from dataclasses import dataclass\n"
+        "\n"
+        "MODULE_ASSIGN = 1\n"
+        "MODULE_ANN: int\n"
+        "MODULE_ANN_DEFAULT: int = 3\n"
+        "\n"
+        "@dataclass\n"
+        "class Data:\n"
+        "    field: int\n"
+        "    default: int = 0\n"
+        "\n"
+        "    def method(self):\n"
+        "        return self.field\n"
+        "\n"
+        "class Outer:\n"
+        "    CLASS_ASSIGN = 1\n"
+        "    CLASS_ANN: int\n"
+        "    CLASS_ANN_DEFAULT: int = 3\n"
+        "\n"
+        "    class Inner:\n"
+        "        INNER_FIELD = 1\n"
+        "\n"
+        "    def method(self):\n"
+        "        return self.CLASS_ASSIGN\n"
+        "\n"
+        "def factory():\n"
+        "    local_assign = 1\n"
+        "    local_ann: int\n"
+        "\n"
+        "    class LocalClass:\n"
+        "        LOCAL_FIELD = 1\n"
+        "\n"
+        "    return local_assign\n",
+        encoding="utf-8",
+    )
+
+    facts = extract_symbol_facts(source)
+
+    assert facts.globals == {
+        "MODULE_ASSIGN",
+        "MODULE_ANN",
+        "MODULE_ANN_DEFAULT",
+    }
+    assert {
+        "Data",
+        "Outer",
+        "Inner",
+    } <= facts.classes
+    assert facts.functions == {"factory"}
+    assert facts.methods == {"Data.method", "Outer.method"}
+    assert {
+        "MODULE_ASSIGN",
+        "MODULE_ANN",
+        "MODULE_ANN_DEFAULT",
+        "CLASS_ASSIGN",
+        "CLASS_ANN",
+        "CLASS_ANN_DEFAULT",
+        "INNER_FIELD",
+    } <= facts.assignments
+    assert not {
+        "local_assign",
+        "local_ann",
+        "LOCAL_FIELD",
+    } & facts.globals
+
+
+def test_class_assignments_inside_nested_scopes_never_become_globals(tmp_path):
+    source = tmp_path / "nested_scope_fixture.py"
+    source.write_text(
+        "class ModuleClass:\n"
+        "    module_class_field = 1\n"
+        "\n"
+        "    class NestedClass:\n"
+        "        nested_class_field = 1\n"
+        "\n"
+        "def make_class():\n"
+        "    class FunctionClass:\n"
+        "        function_class_field = 1\n"
+        "\n"
+        "    return FunctionClass\n",
+        encoding="utf-8",
+    )
+
+    facts = extract_symbol_facts(source)
+
+    assert facts.globals == set()
+    assert not {
+        "module_class_field",
+        "nested_class_field",
+        "function_class_field",
+    } & facts.globals
