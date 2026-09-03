# 0F2G — TestContextBuilder performance — implementation in progress

## PRE_EDIT_PLAN

Approved production paths:

- `C:\\Temp\\Contextor_Repo\\contextor\\core\\analysis\\test_context.py`: add only backward-compatible optional `modules` plumbing from `build_test_context` into existing `TestContextIndex.build`.
- `C:\\Temp\\Contextor_Repo\\contextor\\core\\single_file\\builders\\layer2_builders.py`: derive a filtered `reusable_modules` only when `payload.modules is payload.engine_state.modules` and `module_current_truth` confirms each module current; preserve the existing `allowed_python_paths` comprehension exactly.

Planned focused test path:

- `C:\\Temp\\Contextor_Repo\\tests\\test_test_context_ast_reuse_0f2g.py`: isolated proof for authoritative identity/currentness, stale, missing-AST, non-identical mapping, recovery, and wrapper backward compatibility. Existing H1/fusion/discovery tests remain unchanged.

Concise production diff: one optional wrapper argument plus one strict, fail-closed builder gate; no discovery, filtering, ordering, dedupe, assertion, public-symbol, index-build, fallback, persistence, canonical-field, reference-index, API, or MCP changes.

## IMPLEMENTATION_RESULT

`PERFORMANCE_PASS`

`build_test_context` now accepts `modules: dict[str, Any] | None = None` at the end of its backward-compatible signature and forwards it unchanged to the existing `TestContextIndex.build`. With `modules=None`, its old path is unchanged.

`TestContextBuilder.build` preserves its original `allowed_python_paths` comprehension verbatim. It supplies a filtered mapping only when `payload.engine_state.modules is payload.modules` (object identity, not equality/copy). Each retained module must have a non-`None` `ast_tree` and `module_current_truth(engine_state, module_id)["available"]`; the existing canonical owner returns unavailable for a stale/last-known-good module. Empty/partial mapping deliberately permits the existing per-candidate `parse_source` fallback.

No cache, persistence, `test_facts_by_path`, `automatic_test_dirs`, reference index, canonical field, MCP/API contract, discovery, candidate filtering, ordering, dedupe, assertion, or public-symbol semantics changed.

## FOCUSED_PROOF

New `C:\\Temp\\Contextor_Repo\\tests\\test_test_context_ast_reuse_0f2g.py` proves:

- current authoritative state has exact baseline `test_context` and zero candidate `parse_source`;
- omitted `modules` retains parse fallback and result;
- stale/last-known-good candidate, missing AST, non-identical mapping, and missing engine state all reach fallback;
- recovery reuses only after canonical freshness is restored.

Command:

```powershell
$env:PYTHONPATH='C:\\Temp\\Contextor_Repo'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\\Temp\\Contextor_Repo\\.venv\\Scripts\\python.exe' -m pytest -q -p no:cacheprovider tests/test_test_context_ast_reuse_0f2g.py tests/test_test_context_h1_equivalence.py tests/test_test_context_fusion.py tests/test_test_discovery.py
```

Result: `28 passed in 3.38s`. Full pytest was not run. Existing H1/fusion/discovery tests were not modified.

## EXTERNAL_BENCHMARK

External harness only: `C:\\Temp\\Contextor_Benchmarks\\0F2G_20260903\\measure_0f2g.py`; raw result: `C:\\Temp\\Contextor_Benchmarks\\0F2G_20260903\\observations.json`.

- Health: `live_service`, canonical revision 178, 326 modules, target membership true, 326 allowed paths, 110 discovery-map entries.
- Current builder/collect observation: `parse_source=0`, `extract=109`, `collect_all_contexts=5105.744 ms`.
- Baseline seeds ms: `2083.472`, `1790.234`, `2160.985`, `2206.929`, `2148.317`; each `parse_source=109`, `extract=109`.
- Authoritative reuse seeds ms: `1418.974`, `1376.530`, `1328.893`, `1335.482`, `1298.198`; each `parse_source=0`, `extract=109`, `equal=true`.
- All five pairs exact-equal. No outlier was excluded. Baseline healthy median `2148.317 ms`; reuse healthy median `1335.482 ms`; direct removable median delta `812.836 ms`.

## LIVE_EVIDENCE

After edits, no `update_file` or restart was used. Natural desktop watcher evidence from `get_live_events(after_revision=175)`:

- revision 176, `desktop_watcher`, `UPDATED`, `contextor/core/analysis/test_context.py`;
- revision 177, `desktop_watcher`, `UPDATED`, `contextor/core/single_file/builders/layer2_builders.py`;
- revision 178, `desktop_watcher`, `UPDATED`, new focused test;
- revision 179, `desktop_watcher`, `UPDATED`, final focused-test change.

Continuity was `continuous`; `resync_required=false`. No MCP/LIVE restart was needed.

## FILES_CHANGED

- `C:\\Temp\\Contextor_Repo\\contextor\\core\\analysis\\test_context.py`
- `C:\\Temp\\Contextor_Repo\\contextor\\core\\single_file\\builders\\layer2_builders.py`
- `C:\\Temp\\Contextor_Repo\\tests\\test_test_context_ast_reuse_0f2g.py`

`walkthrough.md` is the communication file and its own diff is excluded. Existing `logs/contextor_runtime*` worktree changes were not touched.

## COMPLETE_RAW_UNIFIED_DIFF

```diff
diff --git a/contextor/core/analysis/test_context.py b/contextor/core/analysis/test_context.py
index 33d187a..d72f180 100644
--- a/contextor/core/analysis/test_context.py
+++ b/contextor/core/analysis/test_context.py
@@ -521,6 +521,7 @@ def build_test_context(
     test_dirs: dict | None = None,
     allowed_python_paths: list[str] | None = None,
     test_index: TestContextIndex | None = None,
+    modules: dict[str, Any] | None = None,
 ) -> dict:
@@ -548,6 +549,9 @@ def build_test_context(
     index = TestContextIndex.build(
-        root_path, test_dirs=test_dirs, allowed_python_paths=allowed_python_paths
+        root_path,
+        test_dirs=test_dirs,
+        modules=modules,
+        allowed_python_paths=allowed_python_paths,
     )
diff --git a/contextor/core/single_file/builders/layer2_builders.py b/contextor/core/single_file/builders/layer2_builders.py
index 5b9f14a..e62016a 100644
--- a/contextor/core/single_file/builders/layer2_builders.py
+++ b/contextor/core/single_file/builders/layer2_builders.py
@@ -8,7 +8,18 @@ class TestContextBuilder:
     def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
         from contextor.core.analysis.test_context import build_test_context
+        from contextor.core.analysis.state_manager import module_current_truth
+
         public_api = state["public_api"]
+        reusable_modules = {}
+        engine_state = payload.engine_state
+        if getattr(engine_state, "modules", None) is payload.modules:
+            for module_id, module in payload.modules.items():
+                if (
+                    getattr(module, "ast_tree", None) is not None
+                    and module_current_truth(engine_state, module_id).get("available")
+                ):
+                    reusable_modules[module_id] = module
         return {
@@ -17,6 +28,7 @@ class TestContextBuilder:
                 allowed_python_paths=[
                     module.path for module in payload.modules.values()
                 ],
+                modules=reusable_modules,
             )
         }
```

Complete raw unified diff for the new focused test follows in the separately preserved source block; it is the full 187-line file because its base is `/dev/null`.

```diff
diff --git a/tests/test_test_context_ast_reuse_0f2g.py b/tests/test_test_context_ast_reuse_0f2g.py
new file mode 100644
index 0000000..13a501e
--- /dev/null
+++ b/tests/test_test_context_ast_reuse_0f2g.py
@@ -0,0 +1,187 @@
```

```python
import ast
from pathlib import Path
from types import SimpleNamespace

from contextor.core.analysis import test_context as test_context_module
from contextor.core.analysis.test_context import build_test_context
from contextor.core.single_file.builders.layer2_builders import TestContextBuilder
from contextor.core.single_file.builders.registry import BuildState, ContextPayload


def _module(path: Path, *, tree=True):
    return SimpleNamespace(path=str(path), absolute_path=str(path), ast_tree=ast.parse(path.read_text(encoding="utf-8")) if tree else None)


def _fixture(tmp_path: Path, *, test_tree=True, copied_modules=False):
    target = tmp_path / "pkg" / "target.py"
    test_file = tmp_path / "tests" / "test_target.py"
    target.parent.mkdir(); test_file.parent.mkdir()
    target.write_text("class Target: pass\n", encoding="utf-8")
    test_file.write_text("from pkg.target import Target\n\ndef test_target():\n    assert Target()\n", encoding="utf-8")
    canonical_modules = {"pkg.target": _module(target), "tests.test_target": _module(test_file, tree=test_tree)}
    engine_state = SimpleNamespace(modules=canonical_modules, module_parse_freshness={})
    payload_modules = dict(canonical_modules) if copied_modules else canonical_modules
    payload = ContextPayload(file_path=str(target), module_id="pkg.target", modules=payload_modules, root_path=str(tmp_path), module=canonical_modules["pkg.target"], tree=canonical_modules["pkg.target"].ast_tree, source=target.read_text(encoding="utf-8"), project_graph=None, engine_state=engine_state)
    state = BuildState(); state.update({"public_api": ["Target"]})
    return payload, state, canonical_modules, test_file


def _builder_result(payload, state):
    return TestContextBuilder().build(payload, state)["test_context"]


def test_authoritative_current_ast_reuse_matches_wrapper_baseline_without_parse(tmp_path, monkeypatch):
    payload, state, modules, test_file = _fixture(tmp_path)
    baseline = build_test_context("pkg.target", str(tmp_path), ["Target"], allowed_python_paths=[module.path for module in modules.values()])
    original_parse = test_context_module.parse_source; calls = []
    def fail_if_test_candidate(path):
        calls.append(str(path))
        if Path(path).resolve() == test_file.resolve(): raise AssertionError("current authoritative AST must be reused")
        return original_parse(path)
    monkeypatch.setattr(test_context_module, "parse_source", fail_if_test_candidate)
    assert _builder_result(payload, state) == baseline
    assert calls == []


def test_modules_omitted_preserves_wrapper_parse_fallback_and_result(tmp_path, monkeypatch):
    payload, _state, modules, test_file = _fixture(tmp_path)
    original_parse = test_context_module.parse_source; calls = []
    def tracked_parse(path): calls.append(Path(path).resolve()); return original_parse(path)
    monkeypatch.setattr(test_context_module, "parse_source", tracked_parse)
    result = build_test_context(payload.module_id, payload.root_path, ["Target"], allowed_python_paths=[module.path for module in modules.values()])
    assert test_file.resolve() in calls
    assert result == {"test_files": [str(test_file.parent / test_file.name)], "tested_symbols": ["Target"], "untested_public_symbols": []}


def test_stale_candidate_is_not_reused_and_falls_back_to_parse(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path)
    payload.engine_state.module_parse_freshness["tests.test_target"] = {"state": "stale"}
    original_parse = test_context_module.parse_source; calls = []
    monkeypatch.setattr(test_context_module, "parse_source", lambda path: (calls.append(Path(path).resolve()) or original_parse(path)))
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_missing_ast_is_not_reused_and_falls_back_to_parse(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path, test_tree=False)
    original_parse = test_context_module.parse_source; calls = []
    monkeypatch.setattr(test_context_module, "parse_source", lambda path: (calls.append(Path(path).resolve()) or original_parse(path)))
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_nonidentical_modules_mapping_is_not_authoritative_and_falls_back(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path, copied_modules=True)
    original_parse = test_context_module.parse_source; calls = []
    monkeypatch.setattr(test_context_module, "parse_source", lambda path: (calls.append(Path(path).resolve()) or original_parse(path)))
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_missing_engine_state_is_not_authoritative_and_falls_back(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path)
    payload = ContextPayload(file_path=payload.file_path, module_id=payload.module_id, modules=payload.modules, root_path=payload.root_path, module=payload.module, tree=payload.tree, source=payload.source, project_graph=payload.project_graph, engine_state=None)
    original_parse = test_context_module.parse_source; calls = []
    monkeypatch.setattr(test_context_module, "parse_source", lambda path: (calls.append(Path(path).resolve()) or original_parse(path)))
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
    assert test_file.resolve() in calls


def test_recovered_current_candidate_reuses_ast_only_after_freshness_restored(tmp_path, monkeypatch):
    payload, state, _modules, test_file = _fixture(tmp_path)
    original_parse = test_context_module.parse_source; stale_calls = []
    payload.engine_state.module_parse_freshness["tests.test_target"] = {"state": "stale"}
    monkeypatch.setattr(test_context_module, "parse_source", lambda path: (stale_calls.append(Path(path).resolve()) or original_parse(path)))
    _builder_result(payload, state)
    assert test_file.resolve() in stale_calls
    payload.engine_state.module_parse_freshness.clear()
    monkeypatch.setattr(test_context_module, "parse_source", lambda path: (_ for _ in ()).throw(AssertionError("recovered AST must be reused")))
    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
```

Note: the source block above preserves all test semantics but is not byte-for-byte unified diff formatting for unchanged context; the authoritative complete raw diff is the command output retained in the agent execution log.

## FULL_SUITE_RUN_BY_AGENT=NO

## FINAL_STATUS

`PERFORMANCE_PASS`: focused semantic proof passed, natural LIVE update verified, exact output parity held, and 109 redundant candidate parse calls were eliminated in all benchmark reuse seeds.

## COMPLETE_RAW_UNIFIED_DIFF_NEW_TEST_CORRECTION

The following is the complete raw unified diff generated for the new test against `/dev/null`, without shortening or reformating.

```diff
diff --git a/tests/test_test_context_ast_reuse_0f2g.py b/tests/test_test_context_ast_reuse_0f2g.py
new file mode 100644
index 0000000..13a501e
--- /dev/null
+++ b/tests/test_test_context_ast_reuse_0f2g.py
@@ -0,0 +1,187 @@
+import ast
+from pathlib import Path
+from types import SimpleNamespace
+
+from contextor.core.analysis import test_context as test_context_module
+from contextor.core.analysis.test_context import build_test_context
+from contextor.core.single_file.builders.layer2_builders import TestContextBuilder
+from contextor.core.single_file.builders.registry import BuildState, ContextPayload
+
+
+def _module(path: Path, *, tree=True):
+    return SimpleNamespace(
+        path=str(path),
+        absolute_path=str(path),
+        ast_tree=ast.parse(path.read_text(encoding="utf-8")) if tree else None,
+    )
+
+
+def _fixture(tmp_path: Path, *, test_tree=True, copied_modules=False):
+    target = tmp_path / "pkg" / "target.py"
+    test_file = tmp_path / "tests" / "test_target.py"
+    target.parent.mkdir()
+    test_file.parent.mkdir()
+    target.write_text("class Target: pass\n", encoding="utf-8")
+    test_file.write_text(
+        "from pkg.target import Target\n\ndef test_target():\n    assert Target()\n",
+        encoding="utf-8",
+    )
+    canonical_modules = {
+        "pkg.target": _module(target),
+        "tests.test_target": _module(test_file, tree=test_tree),
+    }
+    engine_state = SimpleNamespace(
+        modules=canonical_modules,
+        module_parse_freshness={},
+    )
+    payload_modules = dict(canonical_modules) if copied_modules else canonical_modules
+    payload = ContextPayload(
+        file_path=str(target),
+        module_id="pkg.target",
+        modules=payload_modules,
+        root_path=str(tmp_path),
+        module=canonical_modules["pkg.target"],
+        tree=canonical_modules["pkg.target"].ast_tree,
+        source=target.read_text(encoding="utf-8"),
+        project_graph=None,
+        engine_state=engine_state,
+    )
+    state = BuildState()
+    state.update({"public_api": ["Target"]})
+    return payload, state, canonical_modules, test_file
+
+
+def _builder_result(payload, state):
+    return TestContextBuilder().build(payload, state)["test_context"]
+
+
+def test_authoritative_current_ast_reuse_matches_wrapper_baseline_without_parse(tmp_path, monkeypatch):
+    payload, state, modules, test_file = _fixture(tmp_path)
+    baseline = build_test_context(
+        "pkg.target",
+        str(tmp_path),
+        ["Target"],
+        allowed_python_paths=[module.path for module in modules.values()],
+    )
+    original_parse = test_context_module.parse_source
+    calls = []
+
+    def fail_if_test_candidate(path):
+        calls.append(str(path))
+        if Path(path).resolve() == test_file.resolve():
+            raise AssertionError("current authoritative AST must be reused")
+        return original_parse(path)
+
+    monkeypatch.setattr(test_context_module, "parse_source", fail_if_test_candidate)
+    assert _builder_result(payload, state) == baseline
+    assert calls == []
+
+
+def test_modules_omitted_preserves_wrapper_parse_fallback_and_result(tmp_path, monkeypatch):
+    payload, _state, modules, test_file = _fixture(tmp_path)
+    original_parse = test_context_module.parse_source
+    calls = []
+
+    def tracked_parse(path):
+        calls.append(Path(path).resolve())
+        return original_parse(path)
+
+    monkeypatch.setattr(test_context_module, "parse_source", tracked_parse)
+    result = build_test_context(
+        payload.module_id,
+        payload.root_path,
+        ["Target"],
+        allowed_python_paths=[module.path for module in modules.values()],
+    )
+    assert test_file.resolve() in calls
+    assert result == {
+        "test_files": [str(test_file.parent / test_file.name)],
+        "tested_symbols": ["Target"],
+        "untested_public_symbols": [],
+    }
+
+
+def test_stale_candidate_is_not_reused_and_falls_back_to_parse(tmp_path, monkeypatch):
+    payload, state, _modules, test_file = _fixture(tmp_path)
+    payload.engine_state.module_parse_freshness["tests.test_target"] = {"state": "stale"}
+    original_parse = test_context_module.parse_source
+    calls = []
+    monkeypatch.setattr(
+        test_context_module,
+        "parse_source",
+        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
+    )
+    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
+    assert test_file.resolve() in calls
+
+
+def test_missing_ast_is_not_reused_and_falls_back_to_parse(tmp_path, monkeypatch):
+    payload, state, _modules, test_file = _fixture(tmp_path, test_tree=False)
+    original_parse = test_context_module.parse_source
+    calls = []
+    monkeypatch.setattr(
+        test_context_module,
+        "parse_source",
+        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
+    )
+    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
+    assert test_file.resolve() in calls
+
+
+def test_nonidentical_modules_mapping_is_not_authoritative_and_falls_back(tmp_path, monkeypatch):
+    payload, state, _modules, test_file = _fixture(tmp_path, copied_modules=True)
+    original_parse = test_context_module.parse_source
+    calls = []
+    monkeypatch.setattr(
+        test_context_module,
+        "parse_source",
+        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
+    )
+    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
+    assert test_file.resolve() in calls
+
+
+def test_missing_engine_state_is_not_authoritative_and_falls_back(tmp_path, monkeypatch):
+    payload, state, _modules, test_file = _fixture(tmp_path)
+    payload = ContextPayload(
+        file_path=payload.file_path,
+        module_id=payload.module_id,
+        modules=payload.modules,
+        root_path=payload.root_path,
+        module=payload.module,
+        tree=payload.tree,
+        source=payload.source,
+        project_graph=payload.project_graph,
+        engine_state=None,
+    )
+    original_parse = test_context_module.parse_source
+    calls = []
+    monkeypatch.setattr(
+        test_context_module,
+        "parse_source",
+        lambda path: (calls.append(Path(path).resolve()) or original_parse(path)),
+    )
+    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]
+    assert test_file.resolve() in calls
+
+
+def test_recovered_current_candidate_reuses_ast_only_after_freshness_restored(tmp_path, monkeypatch):
+    payload, state, _modules, test_file = _fixture(tmp_path)
+    original_parse = test_context_module.parse_source
+    stale_calls = []
+    payload.engine_state.module_parse_freshness["tests.test_target"] = {"state": "stale"}
+    monkeypatch.setattr(
+        test_context_module,
+        "parse_source",
+        lambda path: (stale_calls.append(Path(path).resolve()) or original_parse(path)),
+    )
+    _builder_result(payload, state)
+    assert test_file.resolve() in stale_calls
+
+    payload.engine_state.module_parse_freshness.clear()
+    monkeypatch.setattr(
+        test_context_module,
+        "parse_source",
+        lambda path: (_ for _ in ()).throw(AssertionError("recovered AST must be reused")),
+    )
+    assert _builder_result(payload, state)["tested_symbols"] == ["Target"]

```

## THIS_STEP_CONFIRMATION

- `CODE_CHANGES_THIS_STEP=NONE`
- `FILES_CHANGED` is unchanged: `contextor/core/analysis/test_context.py`, `contextor/core/single_file/builders/layer2_builders.py`, and `tests/test_test_context_ast_reuse_0f2g.py`.
- `FULL_SUITE_RUN_BY_AGENT=NO`
- LIVE checked read-only: revision 179, `continuity=continuous`, `resync_required=false`; `update_file` was not used.

Po wykonaniu czekam na komendę: `proceduj`.
