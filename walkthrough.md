# F1F — Desktop presentation contract

## PREFLIGHT

- Applicable `AGENTS.md` read. Contextor MCP discovery preceded file inspection/editing.
- Initial HEAD: `08cd146b87ceff815a68e206d6ece84d8fe1c67e`. Initial worktree was clean. Exact pre-edit target diff: `NONE`.
- Pre-edit Contextor state: revision 1194; both target files available and `workspace_sync=verified`; target syntax diagnostics checked with zero errors. Graph, topology, and structural-cycle families were fresh; `cycle_semantics` was stale.
- The actual changed source/test scope is limited to the two requested files. No graph, indexer, SCC, receipt, model, IPC, or recovery-certificate implementation was edited.

## EXACT_PRESENTATION_CORRECTIONS

- Replaced the global healthy-repository message with the requested statement scoped to verified static validation and soft-dependent potential cycles, including the explicit Python runtime-safety caveat.
- The cleared-recovery information dialog now requires no validation errors and a fresh integer potential count of zero. Positive potential count, errors, or a non-fresh diagnostic use the warning path; unavailable diagnostics use `Analysis incomplete` when no positive signal or validation error exists. The warning retains `details or potential_message`.
- Both recovery-failure presentation branches no longer say `No static issues found.` A positive potential count selects warning even with no ordinary errors. The warning includes `details` (which contains the potential message alongside validation errors) or the potential message when details are empty.
- `potential_positive` and verified-zero checks require an integer count, avoiding treating missing/unavailable counts as zero or comparing `None` numerically.
- No recovery certificate, generation, locking, cancellation, IPC, or graph logic changed.

## ZERO_HARD_CYCLE_END_TO_END

- Added one isolated LIVE/Desktop test using only the specified `pkg` source files. The repository source contains the F1C typing-guard dependency and its reverse hard import; no other repository source files are created by the fixture.
- DIRECT_EVIDENCE: LIVE publication succeeded; the installed graph has `pkg.a -> pkg.b` as soft only and `pkg.b -> pkg.a` as hard; authenticated potential diagnostic count is 1; diagnostic and published revisions match; installed `structural_paths == ()`; `model_pass_paths == ()` and `model_pass_count == 0`; no `ArchitectureCycle` error is returned; Desktop invokes `showwarning` with `POTENTIAL cycle involving uncertain dependencies`; no information/healthy-repository message is shown.
- The test uses the existing `_official_live`, `_gui_controller`, isolated-directory, and diagnostics-handler helpers.

## RECOVERY_PRESENTATION_VERIFICATION

- Added focused `recovery_status == "cleared"` cases using existing analysis-controller, identity-registry, and progress-call patterns:
  - fresh count 1: warning with potential-cycle detail;
  - fresh count 0 and no errors: information dialog with bounded static-analysis language;
  - unavailable count: warning that says absence of potential cycles was not established and does not claim a zero result.
- Recovery certificate verification and completion are mocked as a valid generation-1 certificate for these presentation-only cases; recovery lifecycle code is unchanged.
- The two recovery-failure branches were source-reviewed for positive potential counts and preservation of `potential_message` alongside ordinary errors. Existing direct recovery regressions were run; a dedicated positive-potential failure-dialog test was not added.

## TARGETED_TEST_RESULTS

- Changed file: `CONTEXTOR_DISABLE_PROCESS_POOL=1 .venv\\Scripts\\python.exe -m pytest -q tests/test_cycle_semantics_desktop_potential_cycles.py` — **11 passed, 2 dependency deprecation warnings**. This includes existing F1E isolated end-to-end controls and the new zero-hard-cycle case.
- Direct recovery regressions: four selected tests in `tests/test_gui_live_startup.py` — **4 passed, 2 dependency deprecation warnings**.
- An initial run of the changed test file exposed a fixture-placement mistake that omitted `pkg/b.py` from the potential-only fixture. The helper was corrected; final targeted run passed. No product regression remained.
- `git diff --check` for the two target files passed. Literal checks found neither the old global healthy message nor `No static issues found.` in `gui.py`.
- No full pytest run was performed.

## SOURCE_AUTHORITY

- Post-change Contextor `get_file_edit_context` for both targets: canonical revision 1197, provenance LIVE, `workspace_sync=verified`, syntax diagnostics `checked_and_none`, zero errors, no Contextor warnings.
- Post-change Contextor structural diagnostics: 16 DFS back-edge paths, fresh. The LIVE cycle-warning projection at revision 1197 reports structural count 16, model-pass count 0, and active-warning count 16. This equals the pre-edit structural count of 16.
- LIVE events after baseline revision 1194 show Desktop-watcher updates for `gui.py` at 1195 and the test file at 1196/1197, with continuous event history and no resync requirement. These are source-sync events, not a restart or full analysis.
- The `get_project_architecture` overlay reports `cycle_semantics=stale` and runtime execution `UNKNOWN_NOT_EVALUATED`; the stale semantic family is not claimed as fresh evidence.
- Hard/soft graph construction code was not edited. The isolated differential test directly checks the hard/soft edge classification for its synthetic repository. No full project graph reconstruction was requested or run.

## CURRENT_OWNER_ADOPTION_STATUS

- Desktop watcher observed the changed target files and Contextor confirmed their current disk/source sync at revision 1197.
- No MCP server code changed and no restart was performed. Adoption of any previously unadopted cycle-diagnostics server code is not certified by this task. Current `cycle_semantics` remains stale.

## REMAINING_PROOF_GAPS

- The verified zero dialog makes a statement about the authenticated, fresh, restricted static diagnostics only. It explicitly does not establish Python runtime safety.
- No dedicated test exercises positive potential count in each recovery-failure dialog branch; those branches were reviewed in source, and the selected recovery regressions passed.
- No current-owner restart/adoption or fresh cycle-semantics evidence is claimed.

## FILES_CHANGED

- `contextor/ui/gui.py`
- `tests/test_cycle_semantics_desktop_potential_cycles.py`
- `walkthrough.md` is the required report and is excluded from this list under the applicable workflow instructions.

## FULL_DIFFS

The following are the complete actual working-tree diffs for the two changed source/test files in this task:

```diff
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index da04922..56bf1e3 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1487,13 +1487,22 @@ class ContextorGUI:
             potential_message = format_soft_dependent_cycle_diagnostic(
                 potential_diagnostic
             )
+            potential_count = potential_diagnostic.get("count")
+            potential_positive = (
+                type(potential_count) is int and potential_count > 0
+            )
+            potential_verified_zero = (
+                potential_diagnostic.get("availability") == "fresh"
+                and type(potential_count) is int
+                and potential_count == 0
+            )
             detail_lines = [
                 f"{error.kind}: {error.message}"
                 for error in errors
             ]
             if (
                 potential_diagnostic.get("availability") != "fresh"
-                or potential_diagnostic.get("count", 0) > 0
+                or potential_positive
             ):
                 detail_lines.append(potential_message)
             elif not errors:
@@ -1505,13 +1514,17 @@ class ContextorGUI:
                 self._start_live_watcher(path, initial_seq=pre_seq)
                 if (
                     not errors
-                    and potential_diagnostic.get("availability") == "fresh"
-                    and potential_diagnostic.get("count") == 0
+                    and potential_verified_zero
                 ):
-                    messagebox.showinfo("OK", "No issues found. Repository is healthy!")
+                    messagebox.showinfo(
+                        "OK",
+                        "No validation errors or soft-dependent potential cycles "
+                        "were detected in the verified static analysis. "
+                        "This does not prove Python runtime safety.",
+                    )
                     return
                 messagebox.showwarning(
-                    "Issues Detected" if errors or potential_diagnostic.get("count", 0) else "Analysis complete",
+                    "Issues Detected" if errors or potential_positive else "Analysis incomplete",
                     details or potential_message,
                 )
                 return
@@ -1523,12 +1536,12 @@ class ContextorGUI:
                 self._set_live_status(
                     "LIVE recovery verification failed; full repository analysis may be required."
                 )
-                if errors:
+                if errors or potential_positive:
                     messagebox.showwarning("Issues Detected", details)
                 else:
                     messagebox.showinfo(
                         "Analysis complete",
-                        "No static issues found. LIVE recovery verification failed; "
+                        "LIVE recovery verification failed; "
                         "full repository analysis may be required.\n\n"
                         + potential_message,
                     )
@@ -1537,28 +1550,39 @@ class ContextorGUI:
                 self._set_live_status(
                     "LIVE recovery verified; incremental updates resumed."
                 )
-                if not errors:
+                if not errors and potential_verified_zero:
                     messagebox.showinfo(
                         "OK",
                         "LIVE recovery verified; incremental updates resumed.\n\n"
-                        + potential_message,
+                        "No validation errors or soft-dependent potential cycles "
+                        "were detected in the verified static analysis. "
+                        "This does not prove Python runtime safety.",
                     )
                 else:
-                    messagebox.showwarning("Issues Detected", details)
+                    messagebox.showwarning(
+                        "Issues Detected" if errors or potential_positive else "Analysis incomplete",
+                        "LIVE recovery verified; incremental updates resumed.\n\n"
+                        + (details or potential_message),
+                    )
                 return
 
             self._set_live_status(
                 "LIVE recovery verification failed; full repository analysis may be required."
             )
-            if not errors:
+            if errors or potential_positive:
+                messagebox.showwarning(
+                    "Issues Detected",
+                    "LIVE recovery verification failed; full repository analysis "
+                    "may be required.\n\n"
+                    + (details or potential_message),
+                )
+            else:
                 messagebox.showinfo(
                     "Analysis complete",
-                    "No static issues found. LIVE recovery verification failed; "
+                    "LIVE recovery verification failed; "
                     "full repository analysis may be required.\n\n"
                     + potential_message,
                 )
-            else:
-                messagebox.showwarning("Issues Detected", details)
 
         def on_error(exc):
             if recovery_generation is not None:
diff --git a/tests/test_cycle_semantics_desktop_potential_cycles.py b/tests/test_cycle_semantics_desktop_potential_cycles.py
index 37724f2..8d41907 100644
--- a/tests/test_cycle_semantics_desktop_potential_cycles.py
+++ b/tests/test_cycle_semantics_desktop_potential_cycles.py
@@ -20,6 +20,9 @@ from contextor.ui.cycle_warning_presentation import (
 from contextor.core.live_state.runtime import (
     _repository_canonical_query_handler,
 )
+from contextor.core.reporting_engine.persistent_registry import (
+    PersistentIdentityRegistry,
+)
 from tests.test_cycle_semantics_desktop_warning_presentation import (
     _analysis_result,
 )
@@ -31,6 +34,7 @@ from tests.test_original_worker_official_full_live_publication import (
     _official_live,
 )
 from tests.test_original_worker_partial_scc_preparation import TWO_PASS
+from tests.test_gui_live_startup import _make_analysis_controller
 
 
 @pytest.fixture(autouse=True)
@@ -56,6 +60,21 @@ def _witness_repo(root):
     )
 
 
+def _potential_only_repo(root):
+    package = root / "pkg"
+    package.mkdir(parents=True)
+    (package / "__init__.py").write_text("pass\n", encoding="utf-8")
+    (package / "a.py").write_text(
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n"
+        "value = 1\n",
+        encoding="utf-8",
+    )
+    (package / "b.py").write_text(
+        "from pkg.a import value\n", encoding="utf-8",
+    )
+
+
 def _gui_controller(root, monkeypatch):
     controller = SimpleNamespace(
         repo_path_var=SimpleNamespace(get=lambda: str(root)),
@@ -180,10 +199,177 @@ def test_verified_control_reports_zero_and_keeps_healthy_success(tmp_path, isola
         diagnostic = summary["soft_dependent_potential_cycles"]
         assert diagnostic["availability"] == "fresh"
         assert diagnostic["count"] == 0
-        assert "Repository is healthy!" in info.call_args.args[1]
+        assert info.call_args.args[1] == (
+            "No validation errors or soft-dependent potential cycles were "
+            "detected in the verified static analysis. This does not prove "
+            "Python runtime safety."
+        )
         warning.assert_not_called()
 
 
+def test_f1c_potential_only_live_desktop_has_no_hard_cycle_or_model_pass(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = tmp_path / "potential-only"
+    root.mkdir()
+    _potential_only_repo(root)
+    warning = MagicMock()
+    info = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
+    monkeypatch.setattr(gui.messagebox, "showinfo", info)
+    controller = _gui_controller(root, monkeypatch)
+
+    with _official_live(root, monkeypatch) as (client, server, identity, _calls):
+        _install_diagnostics_handler(server)
+        ContextorGUI.analyze(controller)
+        errors, result = controller._full_analysis_done
+        assert result.live_publish_status == "success"
+        assert identity.repo_id
+
+        installed = client.snapshot()
+        graph = installed["state"].dependency_graph
+        assert "pkg.b" not in graph.hard_edges.get("pkg.a", set())
+        assert "pkg.a" in graph.hard_edges["pkg.b"]
+        assert "pkg.b" in graph.soft_edges["pkg.a"]
+
+        response = client.canonical_query("diagnostics_summary", payload={})
+        assert response["status"] == "ok"
+        diagnostic = response["result"]["soft_dependent_potential_cycles"]
+        assert response["revision"] == result.live_publish_revision
+        assert diagnostic["availability"] == "fresh"
+        assert diagnostic["count"] == 1
+
+        report = client.get_installed_cycle_warning_projection()
+        assert report["revision"] == response["revision"]
+        assert report["structural_paths"] == ()
+        assert report["model_pass_paths"] == ()
+        assert report["model_pass_count"] == 0
+        assert not [error for error in errors if error.kind == "ArchitectureCycle"]
+        warning.assert_called_once()
+        assert "POTENTIAL cycle involving uncertain dependencies" in (
+            warning.call_args.args[1]
+        )
+        assert "Repository is healthy!" not in warning.call_args.args[1]
+        info.assert_not_called()
+
+
+@pytest.mark.parametrize(
+    "diagnostic,expected_dialog,expected_fragment",
+    [
+        pytest.param(
+            {
+                "availability": "fresh",
+                "count": 1,
+                "components": ({
+                    "members": ("pkg.a", "pkg.b"),
+                    "member_count": 2,
+                    "soft_only_internal_edges": (("pkg.a", "pkg.b"),),
+                    "soft_only_internal_edge_count": 1,
+                },),
+            },
+            "warning",
+            "POTENTIAL cycle involving uncertain dependencies",
+            id="positive",
+        ),
+        pytest.param(
+            {
+                "availability": "fresh",
+                "count": 0,
+                "components": (),
+            },
+            "info",
+            "No validation errors or soft-dependent potential cycles",
+            id="verified-zero",
+        ),
+        pytest.param(
+            {
+                "availability": "unavailable",
+                "count": None,
+                "components": (),
+            },
+            "warning",
+            "absence of potential cycles was not established",
+            id="unavailable",
+        ),
+    ],
+)
+def test_cleared_recovery_presents_potential_diagnostic_honestly(
+    tmp_path, monkeypatch, diagnostic, expected_dialog, expected_fragment,
+):
+    root = tmp_path / "recovery"
+    root.mkdir()
+    identity = PersistentIdentityRegistry(str(root))
+    controller = _make_analysis_controller(root)
+    ContextorGUI._request_full_analysis_recovery(
+        controller, str(root), "previous recovery incident", queue_prompt=False,
+    )
+    certificate = {
+        "certificate_id": "f1f-certificate",
+        "incident_generation": 1,
+        "repo_id": identity.repo_id,
+        "root_path": str(root.resolve()),
+        "state_id": "f1f-state",
+        "revision": 7,
+    }
+
+    class RecoveryClient:
+        def get_events(self, **_kwargs):
+            return {"latest_seq": 0}
+
+        def verify_recovery(self, generation):
+            assert generation == 1
+            return {"status": "ok", "certificate": certificate}
+
+        def complete_recovery_verification(self, certificate_id, generation):
+            return {
+                "status": "ok",
+                "released": True,
+                "certificate_id": certificate_id,
+                "incident_generation": generation,
+            }
+
+        def cancel_recovery_verification(self, *_args, **_kwargs):
+            pytest.fail("valid recovery certificate must not be cancelled")
+
+    client = RecoveryClient()
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)
+    monkeypatch.setattr(
+        gui,
+        "run_full_analysis_exclusive",
+        lambda *_args, **_kwargs: (
+            [], SimpleNamespace(live_publish_status="success"),
+        ),
+    )
+    monkeypatch.setattr(
+        "contextor.ui.cycle_warning_presentation.read_authenticated_soft_dependent_cycle_diagnostic",
+        lambda *_args, **_kwargs: diagnostic,
+    )
+    monkeypatch.setattr(
+        gui,
+        "run_with_progress",
+        lambda _root, _progress, task, *, on_success, **_kwargs: on_success(task()),
+    )
+    warning = MagicMock()
+    info = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
+    monkeypatch.setattr(gui.messagebox, "showinfo", info)
+
+    ContextorGUI.analyze(
+        controller,
+        recovery_repository=str(root),
+        recovery_generation=1,
+    )
+
+    selected = warning if expected_dialog == "warning" else info
+    selected.assert_called_once()
+    other = info if expected_dialog == "warning" else warning
+    other.assert_not_called()
+    message = selected.call_args.args[1]
+    assert expected_fragment in message
+    if diagnostic["availability"] != "fresh":
+        assert "No validation errors or soft-dependent potential cycles" not in message
+
+
 def test_stale_or_mismatched_live_authority_is_not_verified_zero(
     tmp_path, isolated_dirs, monkeypatch,
 ):
```

## FINAL_VERDICT

**FINAL PASS for the requested F1F presentation contract**, limited to the stated Desktop UI and isolated/recovery test evidence. Focused tests passed, post-change target-source synchronization and syntax diagnostics are fresh/verified, and the structural cycle count remains 16. The report does not claim runtime safety, current cycle-semantics freshness, or adoption of un-restarted MCP server code.
