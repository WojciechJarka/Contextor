STAGE_1_FINAL=PASS
PRODUCTION_CHANGE_REQUIRED=NO

REAL_INDEXER_VALID_PATH=PASS
REAL_INDEXER_SYNTAX_ERROR=PASS
REAL_SKIPPED_REASON_CONTRACT=CONFIRMED
REAL_FACADE_STATE_MATERIALIZATION=PASS
SOURCE_REPARSES_DURING_HYDRATION=0

REAL_INDEXER_EVIDENCE=
Disposable repo inputs:
  valid.py: value = 1
  broken.py: def broken(
Real contextor.core.symbol_engine.indexer::index_repository result:
  valid.py present in index.modules: PASS
  broken.py present in index.skipped: PASS
  SKIPPED_PATH=broken.py
  SKIPPED_REASON=is not valid Python (line 1, column 11: '(' was never closed)
  SKIPPED_LINE=1
  SKIPPED_COLUMN=11
The producer exposes no structural SyntaxError discriminator on SkippedFile beyond reason plus coordinates. The real producer's stable current reason contains "is not valid Python"; no production correction was required.

REAL_BUILDER_EVIDENCE=
build_syntax_diagnostics_from_index(real_index):
  valid.py -> {status: checked_and_none, errors: []}
  broken.py -> {status: checked_with_errors, errors: [{message: SKIPPED_REASON, line_number: 1, column_number: 11}]}
  syntax_diagnostics_state=fresh

CANONICAL_KEY_PROOF=
  keys=valid.py,broken.py
  repo_relative=PASS
  forward_slash_normalized=PASS
  absolute_paths=NONE
  invented_module_identity_for_broken.py=NONE

REAL_FACADE_EVIDENCE=
Real ContextorFacade.analyze_project on the same disposable shape produced a persisted RepositoryAnalysisState, hydrated through the existing state path:
  state.syntax_diagnostics_state=fresh
  state.syntax_diagnostics_by_path["valid.py"]={status: checked_and_none, errors: []}
  state.syntax_diagnostics_by_path["broken.py"].status=checked_with_errors
No build_syntax_diagnostics_from_index, RepositoryAnalysisState syntax field, RepositoryIndex, SkippedFile, or parser was mocked.

CANONICAL_KEY=source_path
FULL_ANALYSIS_MATERIALIZATION=ContextorFacade.analyze_project materializes RepositoryAnalysisState.syntax_diagnostics_by_path exclusively from completed index_repository results. Successful Module.path values become forward-slash repo-relative checked_and_none facts. Syntax SkippedFile values become checked_with_errors with message/line_number/column_number.
FAMILY_COMPLETENESS_RULE=fresh requires exactly one explicit fact for every indexed in-scope Python path. Non-syntax skipped/read/index outcome, non-canonical path, duplicate path, or missing outcome yields deferred; it never fabricates checked_and_none.
LEGACY_NORMALIZATION=Legacy snapshot hydration assigns syntax_diagnostics_by_path={} and syntax_diagnostics_state=not_materialized.
PERSISTENCE_ROUNDTRIP=PASS
MCP_RESTART_REQUIRED=NO
LIVE_RESTART_REQUIRED=NO
NEXT_STAGE=incremental/LIVE atomic lifecycle

SCOPE_CONFIRMED=
- No production changes were made during integration closure.
- module_parse_freshness, module_current_truth, SkippedFile/job reporting remain semantically unchanged.
- No update_file call and no real Desktop/LIVE certification.
- No incremental/LIVE implementation.

VALIDATION=
Focused pytest:
  .\.venv\Scripts\python.exe -m pytest -q tests/test_syntax_diagnostics_full_analysis.py tests/test_live_state_store.py
  28 passed in 5.89s
git diff --check: PASS (only existing CRLF warnings; no whitespace errors)
FULL_SUITE_RUN_BY_AGENT=NO

FILES_CHANGED=
- contextor/core/analysis/state_manager.py
- contextor/core/api/facade.py
- contextor/core/live_state/store.py
- tests/test_syntax_diagnostics_full_analysis.py

UNRELATED_PREEXISTING_CHANGE_PRESERVED=
- logs/contextor_runtime_20260906_162424_256_3672.jsonl

DIFFS=

diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index c8b75ff..a5c809e 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -89,6 +89,8 @@ class RepositoryAnalysisState:
     metrics: Dict[str, Any] = field(default_factory=dict)
     file_state: Dict[str, FileState] = field(default_factory=dict)
     module_parse_freshness: Dict[str, Dict[str, Any]] = field(default_factory=dict)
+    syntax_diagnostics_by_path: Dict[str, Dict[str, Any]] = field(default_factory=dict)
+    syntax_diagnostics_state: str = "not_materialized"
     module_usages: Dict[str, Any] = field(default_factory=dict)
     module_usages_manifest: Dict[str, Dict[str, str]] = field(default_factory=dict)
     topology_analytics: Dict[str, Any] = field(default_factory=dict)
@@ -116,6 +118,62 @@ class RepositoryAnalysisState:
     package_root: str = ""
 
 
+def _canonical_python_source_path(path: Any) -> str | None:
+    """Normalize an already repository-relative Python source path for state keys."""
+    normalized = str(path).replace("\\", "/")
+    if normalized.startswith("./"):
+        normalized = normalized[2:]
+    if (
+        not normalized.endswith(".py")
+        or normalized.startswith("/")
+        or (len(normalized) >= 3 and normalized[1:3] == ":/")
+    ):
+        return None
+    return normalized
+
+
+def build_syntax_diagnostics_from_index(index: Any) -> tuple[Dict[str, Dict[str, Any]], str]:
+    """Materialize full-analysis syntax facts from one completed RepositoryIndex.
+
+    A missing result for any indexed Python path is deliberately incomplete;
+    no source is read or parsed here.
+    """
+    expected_paths: set[str] = set()
+    facts: Dict[str, Dict[str, Any]] = {}
+    complete = True
+
+    for module in (getattr(index, "modules", {}) or {}).values():
+        path = _canonical_python_source_path(getattr(module, "path", None))
+        if path is None or path in expected_paths:
+            complete = False
+            continue
+        expected_paths.add(path)
+        facts[path] = {"status": "checked_and_none", "errors": []}
+
+    for skipped in getattr(index, "skipped", []) or []:
+        path = _canonical_python_source_path(getattr(skipped, "path", None))
+        if path is None or path in expected_paths:
+            complete = False
+            continue
+        expected_paths.add(path)
+        reason = str(getattr(skipped, "reason", ""))
+        if "is not valid Python" not in reason:
+            complete = False
+            continue
+        facts[path] = {
+            "status": "checked_with_errors",
+            "errors": [{
+                "message": reason,
+                "line_number": getattr(skipped, "line_number", None),
+                "column_number": getattr(skipped, "column_number", None),
+            }],
+        }
+
+    if not complete or set(facts) != expected_paths:
+        return facts, "deferred"
+    return facts, "fresh"
+
+
 def module_current_truth(state: RepositoryAnalysisState, module_name: str) -> Dict[str, Any]:
     """Return authoritative per-module parse freshness and provenance."""
     freshness = getattr(state, "module_parse_freshness", {}) or {}

diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index d9f9036..cf348ed 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -466,6 +466,7 @@ class ContextorFacade:
                 FileStateManager,
                 RepositoryAnalysisState,
                 artifact_consumption_is_fresh,
+                build_syntax_diagnostics_from_index,
                 build_canonical_artifact_consumption,
                 dependency_matrix_inputs_are_fresh,
                 save_engine_state,
@@ -518,6 +519,9 @@ class ContextorFacade:
                 canonical_consumption,
                 raw_artifacts,
             )
+            syntax_diagnostics_by_path, syntax_diagnostics_state = (
+                build_syntax_diagnostics_from_index(index)
+            )
 
             state = RepositoryAnalysisState(
                 modules=mods,
@@ -527,6 +531,8 @@ class ContextorFacade:
                 package_root=getattr(analysis_result, "package_root", ""),
                 artifact_consumption=canonical_consumption,
                 artifact_consumption_state="fresh" if consumption_valid else "stale",
+                syntax_diagnostics_by_path=syntax_diagnostics_by_path,
+                syntax_diagnostics_state=syntax_diagnostics_state,
                 module_usages=module_usages,
                 module_usages_manifest=module_usages_manifest,
                 metrics=metrics,

diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 84bd3f2..c96969b 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -340,6 +340,16 @@ def load_snapshot(
                         setattr(state_obj, "module_usages", {})
                     except AttributeError:
                         pass
+                if not hasattr(state_obj, "syntax_diagnostics_by_path"):
+                    try:
+                        setattr(state_obj, "syntax_diagnostics_by_path", {})
+                    except AttributeError:
+                        pass
+                if not hasattr(state_obj, "syntax_diagnostics_state"):
+                    try:
+                        setattr(state_obj, "syntax_diagnostics_state", "not_materialized")
+                    except AttributeError:
+                        pass
                 if not hasattr(state_obj, "module_usages_manifest"):
                     try:
                         setattr(state_obj, "module_usages_manifest", {})
@@ -418,6 +428,16 @@ def load_snapshot(
                     setattr(payload, "module_usages", {})
                 except AttributeError:
                     pass
+            if not hasattr(payload, "syntax_diagnostics_by_path"):
+                try:
+                    setattr(payload, "syntax_diagnostics_by_path", {})
+                except AttributeError:
+                    pass
+            if not hasattr(payload, "syntax_diagnostics_state"):
+                try:
+                    setattr(payload, "syntax_diagnostics_state", "not_materialized")
+                except AttributeError:
+                    pass
             if not hasattr(payload, "module_usages_manifest"):
                 try:
                     setattr(payload, "module_usages_manifest", {})

diff --git a/tests/test_syntax_diagnostics_full_analysis.py b/tests/test_syntax_diagnostics_full_analysis.py
new file mode 100644
index 0000000..d66e5d1
--- /dev/null
+++ b/tests/test_syntax_diagnostics_full_analysis.py
@@ -0,0 +1,159 @@
+from types import SimpleNamespace
+
+from contextor.core.analysis.state_manager import (
+    RepositoryAnalysisState,
+    build_syntax_diagnostics_from_index,
+)
+from contextor.core.api.facade import ContextorFacade
+from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.live_state import load_snapshot, save_snapshot
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+def _index(*, modules=(), skipped=()):
+    return SimpleNamespace(
+        modules={f"module_{index}": SimpleNamespace(path=path) for index, path in enumerate(modules)},
+        skipped=list(skipped),
+    )
+
+
+def test_full_analysis_materializes_checked_and_none_for_valid_python_path():
+    facts, state = build_syntax_diagnostics_from_index(_index(modules=("pkg\\valid.py",)))
+
+    assert state == "fresh"
+    assert facts == {"pkg/valid.py": {"status": "checked_and_none", "errors": []}}
+
+
+def test_full_analysis_materializes_syntax_error_without_module_identity():
+    skipped = SimpleNamespace(
+        path="broken.py",
+        reason="is not valid Python (line 3, column 7: invalid syntax)",
+        line_number=3,
+        column_number=7,
+    )
+
+    facts, state = build_syntax_diagnostics_from_index(_index(skipped=(skipped,)))
+
+    assert state == "fresh"
+    assert facts == {
+        "broken.py": {
+            "status": "checked_with_errors",
+            "errors": [{
+                "message": "is not valid Python (line 3, column 7: invalid syntax)",
+                "line_number": 3,
+                "column_number": 7,
+            }],
+        }
+    }
+
+
+def test_full_analysis_mix_is_complete_when_every_path_has_explicit_fact():
+    skipped = SimpleNamespace(
+        path="pkg/broken.py",
+        reason="is not valid Python (line 1: '(' was never closed)",
+        line_number=1,
+        column_number=None,
+    )
+
+    facts, state = build_syntax_diagnostics_from_index(
+        _index(modules=("pkg/valid.py",), skipped=(skipped,))
+    )
+
+    assert state == "fresh"
+    assert set(facts) == {"pkg/valid.py", "pkg/broken.py"}
+
+
+def test_non_syntax_skipped_outcome_cannot_fabricate_checked_and_none():
+    skipped = SimpleNamespace(
+        path="unreadable.py",
+        reason="could not be read (access denied)",
+        line_number=None,
+        column_number=None,
+    )
+
+    facts, state = build_syntax_diagnostics_from_index(_index(skipped=(skipped,)))
+
+    assert state == "deferred"
+    assert facts == {}
+
+
+def test_syntax_diagnostics_snapshot_roundtrip_needs_no_source_reconstruction(tmp_path, monkeypatch):
+    facts = {
+        "broken.py": {
+            "status": "checked_with_errors",
+            "errors": [{"message": "invalid syntax", "line_number": 2, "column_number": 4}],
+        }
+    }
+    state = RepositoryAnalysisState(
+        syntax_diagnostics_by_path=facts,
+        syntax_diagnostics_state="fresh",
+    )
+    save_snapshot(state, tmp_path, "syntax-state")
+
+    monkeypatch.setattr(
+        "contextor.core.source.ast.parse",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("hydration must not parse source")),
+    )
+    loaded, _ = load_snapshot(tmp_path, "syntax-state")
+
+    assert loaded.syntax_diagnostics_by_path == facts
+    assert loaded.syntax_diagnostics_state == "fresh"
+
+
+def test_legacy_snapshot_marks_syntax_family_not_materialized(tmp_path):
+    legacy = SimpleNamespace(modules={}, dependency_graph=None)
+    save_snapshot(legacy, tmp_path, "legacy-syntax")
+
+    loaded, _ = load_snapshot(tmp_path, "legacy-syntax")
+
+    assert loaded.syntax_diagnostics_by_path == {}
+    assert loaded.syntax_diagnostics_state == "not_materialized"
+
+
+def test_real_index_repository_materializes_source_scoped_syntax_facts(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    (tmp_path / "valid.py").write_text("value = 1\n", encoding="utf-8")
+    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")
+
+    index = index_repository(str(tmp_path))
+
+    assert {module.path for module in index.modules.values()} == {"valid.py"}
+    assert len(index.skipped) == 1
+    skipped = index.skipped[0]
+    assert skipped.path == "broken.py"
+    assert "is not valid Python" in skipped.reason
+    assert (skipped.line_number, skipped.column_number) == (1, 11)
+
+    facts, state = build_syntax_diagnostics_from_index(index)
+
+    assert state == "fresh"
+    assert facts["valid.py"] == {"status": "checked_and_none", "errors": []}
+    assert facts["broken.py"]["status"] == "checked_with_errors"
+    assert facts["broken.py"]["errors"][0] == {
+        "message": skipped.reason,
+        "line_number": 1,
+        "column_number": 11,
+    }
+    assert all("\\" not in path and not path.startswith(("/", "C:/")) for path in facts)
+    assert "broken" not in index.modules
+    assert "module_name" not in facts["broken.py"]
+
+
+def test_real_facade_materializes_real_index_syntax_facts(tmp_path, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    (tmp_path / "valid.py").write_text("value = 1\n", encoding="utf-8")
+    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")
+
+    errors, _ = ContextorFacade.analyze_project(str(tmp_path))
+
+    assert errors == []
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    state = hydrated.engine.state
+    assert state.syntax_diagnostics_state == "fresh"
+    assert state.syntax_diagnostics_by_path["valid.py"] == {
+        "status": "checked_and_none",
+        "errors": [],
+    }
+    assert state.syntax_diagnostics_by_path["broken.py"]["status"] == "checked_with_errors"
