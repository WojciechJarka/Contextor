# CONTEXTOR_C16_P15_EXTERNAL_IMPORT_EFFECTS_F1E

## PREFLIGHT

- Read `C:\Users\DafoO\.codex\AGENTS.md` and the F1E attachment. Initial HEAD: `0f00db3e02dcbb61c18d761fdfaf04675793791f`; initial worktree clean. F1D sources/tests were already part of this baseline; no unreported changes were overwritten.
- Contextor MCP discovery was first. Its documented `get_file_edit_context` resolved all six requested owners at LIVE revision 1175 with verified workspace sync, no syntax errors, and fresh module/graph/topology/cycle families; cycle semantics was stale. Contextor lineage resolved `filter_installed_desktop_cycle_errors` and `query_live_diagnostics_summary_narrow`; implementation fetch for `ContextorGUI.analyze` confirmed the existing success and recovery branches.
- `get_file_edit_context` rejected an unsupported `diagnostics_summary` projection field; retried once using its documented allowed fields. No source patch was based on that rejected request.
- Source authority at completion: HEAD unchanged; modified targets are reported by Contextor at LIVE revision 1194 with `workspace_sync=verified`, syntax checked with no errors. No current canonical LIVE mutation or restart was performed.

## EXACT_PRESENTATION_PATH

- Existing path: `ContextorGUI.analyze` runs `run_full_analysis_exclusive` in `run_with_progress`'s worker, applies `filter_installed_desktop_cycle_errors`, and then on GUI success displays “Repository is healthy!” whenever the remaining error list is empty. The hard-cycle filter only removes exact authenticated `model_pass_paths` from a fresh installed-cycle projection.
- New path: the analysis worker queries `diagnostics_summary`, then reads the installed hard-cycle projection. It accepts the potential diagnostic only if publication status is `success`; the published revision matches the expected revision; warning projection authority, state ID, repository identity/root, service instance, process start identity, and graph hash validate through `_accepted_paths`; and the summary query revision equals the authenticated projection revision. The potential diagnostic must independently be `fresh`, have the expected restricted-graph scope, exact nonnegative count/component shape, and `runtime_execution_proven=False`.
- The worker samples at most three components and eight module identities/eight soft-only edges per component. GUI callback displays the total and bounded sample as “POTENTIAL cycle involving uncertain dependencies”; the text explicitly says it does not prove CPython will execute the cycle. It is not added to hard structural paths or warning partitions.
- The healthy message now requires an authenticated fresh diagnostic with count zero. Missing, stale, malformed, failed-publication, wrong-revision, or wrong-repository evidence yields “absence ... was not established,” never a verified zero.
- Initial event-sequence capture, new diagnostics queries, and existing recovery verification IPC now run in the worker. GUI callbacks only choose and display messages. The recovery state transitions and accepted-certificate checks are preserved.

## LIVE_AUTHORITY_BINDING

- `canonical_query("diagnostics_summary")` returns a revision envelope and the canonical summary. A separate installed warning projection supplies state ID, repo/root, service/process identity, graph hash, and the existing hard-cycle partition. Both reads use one connected LIVE client; their revisions must match, and the projection must also match `analysis_result`'s successful published generation.
- F1D's summary source requires `cycles_state == "fresh"`, available hard/soft graph mappings, and no active resync. The production `RepositoryAnalysisState` commonly omits a `resync_required` attribute; existing state consumers treat absence as false. The narrow correction in `diagnostics_projection.py` follows that established default while rejecting any present non-boolean value, explicit resync, stale cycle generation, or missing graph. This made the real canonical summary fresh without weakening its graph/freshness gates.
- A query response from a different revision or identity is rejected. If the process has not loaded the diagnostic code, the missing field is unavailable and cannot authorize absence.

## REAL_END_TO_END_DIAGNOSTIC

- New independent synthetic LIVE test runs actual Desktop full analysis and publication for a repository containing the F1C witness plus independent hard cycles. Canonical graph evidence is: `pkg.a -> pkg.b` absent from hard edges and present in soft edges; `pkg.b -> pkg.a` present in hard edges.
- The isolated LIVE owner emits exactly one fresh potential SCC with members `("pkg.a", "pkg.b")` and soft-only edge `pkg.a -> pkg.b`. The summary revision equals the successful Desktop publication revision and the authenticated installed-cycle projection revision.
- Existing hard cycles have authenticated MODEL_PASS paths and zero active hard-cycle warnings. The potential `pkg.a/pkg.b` component appears in neither structural nor model-pass paths. The Desktop message reports the POTENTIAL component and no `ArchitectureCycle` warning is fabricated.
- A separate no-potential-cycle control obtains a fresh zero and keeps the existing healthy-success message.
- A subprocess test launches the real end-to-end case under a fresh isolated CPython 3.15.2 interpreter. Its LIVE owner is synthetic and isolated; this verifies code loaded in that process, not adoption by the currently running canonical owner.

## DESKTOP_POSITIVE_AND_NEGATIVE_CASES

- Positive: fresh isolated LIVE publication and matching graph report a positive component count and bounded sample in the Desktop warning.
- Negative: a stale diagnostic, wrong response revision, wrong repository path/identity, or non-success publication produces unavailable with `count=None`. The failed-publication case asserts no LIVE query occurs.
- The presentation formatter bounds each component sample even when an SCC has thousands of members/edges. It keeps total component count and reports sample truncation.
- Recovery verification regressions continue to cover accepted certificates, superseding incidents, cancellation, and failed recovery. Queries and certificate completion now execute in the worker while existing GUI status/message handling remains in the callback.

## PRESERVED_HARD_CYCLE_CONTRACTS

- No edits to hard/soft graph construction, canonical `detect_cycles`, structural cycle inventory, MODEL_PASS classes, receipt/manifest schema, warning projection schema, or `get_live_events` transition semantics.
- The existing hard-cycle filter remains the only path that suppresses hard warnings, and it still suppresses only authenticated MODEL_PASS paths. Potential-cycle data remains separate and is not filtered by that function.

## TARGETED_TEST_RESULTS

- 113 focused tests passed across F1D SCC/diagnostic tests, F1 external-import authority, narrow LIVE/MCP summary, Desktop hard-warning presentation, GUI startup/recovery, and the new Desktop potential-cycle tests before the final worker-thread recovery relocation.
- After that relocation, 61 focused Desktop warning, GUI recovery/startup, and Desktop potential-cycle tests passed, including the fresh CPython 3.15.2 subprocess end-to-end test.
- No full pytest. Only two dependency deprecation warnings were emitted. `git diff --check` found no source/test whitespace errors; Git reported expected Windows line-ending conversion notices.

## RUNTIME_ADOPTION_STATUS

- ISOLATED_RUNTIME_VERIFIED: the new source executes under CPython 3.15.2 in a fresh subprocess with a fresh isolated LIVE owner; positive and zero controls pass.
- CURRENT_CANONICAL_OWNER_ADOPTION: UNKNOWN / NOT VERIFIED. Contextor's running owner at revision 1194 reports the prior diagnostics summary shape without `soft_dependent_potential_cycles`. No restart or mutation was performed, as instructed. The current owner therefore cannot yet certify this new diagnostic to a live Desktop session.

## MCP_POST_CHANGE_AUDIT

- At revision 1194, Contextor MCP reports verified source sync and `checked_and_none` syntax diagnostics for `gui.py`, `cycle_warning_presentation.py`, `diagnostics_projection.py`, and unchanged `graph.py`.
- Graph, topology, and structural cycles are fresh; `cycle_semantics` remains stale and is reported as stale. No stale semantic evidence was described as fresh.
- Current MCP diagnostic envelope still reports the existing hard-only cycle count 16 and old summary shape. The changed graph builder and hard/soft classification were untouched. The synthetic canonical graph test confirms expected edges; installed hard-cycle report and structural paths remain unchanged by the new potential diagnostic.

## REMAINING_PROOF_GAPS

- The actual running canonical owner has not adopted the new code, so a current live Desktop/MCP session has not yet demonstrated the new summary field. A controlled later reload/runtime adoption check is needed before claiming end-to-end coverage for that owner. This task deliberately did not restart or mutate it.
- The isolated Desktop test verifies the `messagebox` call arguments and authenticated data path; it does not inspect a rendered native message box. Desktop rendering of the bounded text is not visually certified here.

## HARDCODING_AUDIT

- No repository/module allowlists or new special cases were added. Production logic validates general diagnostic shape and authenticated generation metadata. `pkg.a/pkg.b` are confined to independent synthetic tests.

## FILES_CHANGED

- `contextor/core/diagnostics_projection.py`
- `contextor/ui/cycle_warning_presentation.py`
- `contextor/ui/gui.py`
- `tests/test_soft_dependent_potential_cycles.py`
- `tests/test_cycle_semantics_desktop_potential_cycles.py` (new)

`walkthrough.md` is the required report and excluded from this inventory under AGENTS.md.

## FULL_DIFFS

Complete actual diffs for every source and test file follow. The new test is represented as a `/dev/null` addition.

```diff
diff --git a/contextor/core/diagnostics_projection.py b/contextor/core/diagnostics_projection.py
index 5aa92cc..4c2e34c 100644
--- a/contextor/core/diagnostics_projection.py
+++ b/contextor/core/diagnostics_projection.py
@@ -29,9 +29,10 @@ def _soft_dependent_cycle_diagnostic(state: Any) -> dict[str, Any]:
     }
     if state is None:
         return unavailable
-    if getattr(state, "resync_required", None) is True:
+    resync_required = getattr(state, "resync_required", False)
+    if resync_required is True:
         return {**unavailable, "availability": "stale"}
-    if getattr(state, "resync_required", None) is not False:
+    if resync_required is not False:
         return unavailable
     cycle_state = getattr(state, "cycles_state", None)
     if cycle_state != "fresh":
diff --git a/contextor/ui/cycle_warning_presentation.py b/contextor/ui/cycle_warning_presentation.py
index a1a810e..ac62a75 100644
--- a/contextor/ui/cycle_warning_presentation.py
+++ b/contextor/ui/cycle_warning_presentation.py
@@ -44,6 +44,17 @@ _FIELDS = frozenset({
     "authority",
 })
 
+_POTENTIAL_DIAGNOSTIC_FIELDS = frozenset({
+    "count",
+    "components",
+    "availability",
+    "evidence_scope",
+    "runtime_execution_proven",
+})
+_POTENTIAL_EVIDENCE_SCOPE = (
+    "RESTRICTED_HARD_UNION_SOFT_IMPORT_GRAPH_POTENTIAL_ONLY"
+)
+
 
 def _accepted_paths(
     result: Any,
@@ -222,3 +233,148 @@ def filter_installed_desktop_cycle_errors(
     except Exception:
         # A presentation query must not hide diagnostics or fail analysis.
         return errors
+
+
+def read_authenticated_soft_dependent_cycle_diagnostic(
+    analysis_result: Any,
+    repo_path: str,
+    *,
+    sample_limit: int = 3,
+) -> dict[str, Any]:
+    """Read a fresh potential-cycle result bound to the published LIVE graph.
+
+    Call from the analysis worker. Any missing or mismatched authority returns
+    unavailable, never a verified zero count.
+    """
+    unavailable = {
+        "availability": "unavailable",
+        "count": None,
+        "components": (),
+    }
+    if type(sample_limit) is not int or sample_limit < 0:
+        return unavailable
+    if getattr(analysis_result, "live_publish_status", None) != "success":
+        return unavailable
+
+    try:
+        from contextor.core.live_state import connect
+
+        client = connect(Path(repo_path))
+        if client is None:
+            return unavailable
+        response = client.canonical_query(
+            "diagnostics_summary", payload={},
+        )
+        if type(response) is not dict or response.get("status") != "ok":
+            return unavailable
+        revision = response.get("revision")
+        if type(revision) is not int or revision < 1:
+            return unavailable
+        summary = response.get("result")
+        if type(summary) is not dict:
+            return unavailable
+        diagnostic = summary.get("soft_dependent_potential_cycles")
+        availability = summary.get("availability")
+        if (
+            type(diagnostic) is not dict
+            or set(diagnostic) != _POTENTIAL_DIAGNOSTIC_FIELDS
+            or diagnostic.get("availability") != "fresh"
+            or type(diagnostic.get("count")) is not int
+            or diagnostic["count"] < 0
+            or diagnostic.get("evidence_scope") != _POTENTIAL_EVIDENCE_SCOPE
+            or diagnostic.get("runtime_execution_proven") is not False
+            or type(diagnostic.get("components")) is not tuple
+            or len(diagnostic["components"]) != diagnostic["count"]
+            or type(availability) is not dict
+            or availability.get("soft_dependent_potential_cycles") != "fresh"
+        ):
+            return unavailable
+
+        report = client.request(
+            "get_installed_cycle_warning_projection", timeout=2.0,
+        )
+        if _accepted_paths(analysis_result, repo_path, report) is None:
+            return unavailable
+        if report.get("revision") != revision:
+            return unavailable
+
+        components = diagnostic["components"]
+        validated = []
+        for component in components:
+            if type(component) is not dict or set(component) != {
+                "kind", "members", "soft_only_internal_edges",
+            }:
+                return unavailable
+            members = component.get("members")
+            edges = component.get("soft_only_internal_edges")
+            if (
+                component.get("kind") != "SOFT_DEPENDENT_POTENTIAL_CYCLE"
+                or type(members) is not tuple
+                or not members
+                or any(type(item) is not str or not item for item in members)
+                or tuple(sorted(set(members))) != members
+                or type(edges) is not tuple
+                or not edges
+                or any(
+                    type(edge) is not tuple
+                    or len(edge) != 2
+                    or any(type(item) is not str or not item for item in edge)
+                    or edge[0] not in members
+                    or edge[1] not in members
+                    for edge in edges
+                )
+                or tuple(sorted(set(edges))) != edges
+            ):
+                return unavailable
+            validated.append({
+                "members": members[:8],
+                "member_count": len(members),
+                "soft_only_internal_edges": edges[:8],
+                "soft_only_internal_edge_count": len(edges),
+            })
+
+        return {
+            "availability": "fresh",
+            "count": diagnostic["count"],
+            "components": tuple(validated[:sample_limit]),
+            "revision": revision,
+        }
+    except Exception:
+        return unavailable
+
+
+def format_soft_dependent_cycle_diagnostic(
+    diagnostic: Any,
+) -> str:
+    """Bound a potential-cycle diagnostic for a Desktop message box."""
+    if (
+        type(diagnostic) is not dict
+        or diagnostic.get("availability") != "fresh"
+        or type(diagnostic.get("count")) is not int
+    ):
+        return (
+            "Potential cycle diagnostic is unavailable or unverified; "
+            "absence of potential cycles was not established."
+        )
+    count = diagnostic["count"]
+    if count == 0:
+        return "No POTENTIAL cycles involving uncertain dependencies were detected in the verified LIVE graph."
+    lines = [
+        f"POTENTIAL cycle involving uncertain dependencies: {count} component(s).",
+    ]
+    for index, component in enumerate(diagnostic.get("components", ()), 1):
+        members = ", ".join(component["members"])
+        edges = ", ".join(
+            f"{source} -> {target}"
+            for source, target in component["soft_only_internal_edges"]
+        )
+        member_count = component["member_count"]
+        edge_count = component["soft_only_internal_edge_count"]
+        more_members = f", … ({member_count} modules)" if member_count > len(component["members"]) else ""
+        more_edges = f"; showing {len(component['soft_only_internal_edges'])} of {edge_count} edges" if edge_count > len(component["soft_only_internal_edges"]) else ""
+        lines.append(
+            f"Sample {index}: [{members}{more_members}]; uncertain edges: "
+            f"{edges}{more_edges}"
+        )
+    lines.append("This does not prove CPython will execute the cycle.")
+    return "\n".join(lines)
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index e6f95e0..da04922 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -1296,38 +1296,18 @@ class ContextorGUI:
             )
 
         pre_seq = 0
-        try:
-            from contextor.core.live_state import connect
-            live_client = connect(Path(path))
-            if live_client is not None:
-                resp = live_client.get_events(limit=1)
-                pre_seq = int(resp.get("latest_seq", 0))
-        except Exception:
-            pre_seq = 0
 
-        def task(log=None, progress_callback=None):
-            errors, analysis_result = run_full_analysis_exclusive(
-                path,
-                owner="desktop_analysis",
-                log=log,
-                progress_callback=progress_callback,
-                is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
-                cycle_source_preparation_preview=True,
-                cycle_partial_source_publication_opt_in=True,
-            )
-            from contextor.ui.cycle_warning_presentation import (
-                filter_installed_desktop_cycle_errors,
-            )
-            errors = filter_installed_desktop_cycle_errors(
-                errors,
-                analysis_result,
-                path,
-            )
-            return errors, analysis_result
+        potential_diagnostic = {
+            "availability": "unavailable",
+            "count": None,
+            "components": (),
+        }
+        recovery_outcome = {"status": "not_required"}
 
-        def on_success(outcome):
-            errors, analysis_result = outcome
-            incident_before_publish_result = self._live_recovery_incident(path)
+        def verify_recovery_on_worker(
+            analysis_result,
+            incident_before_publish_result,
+        ):
             analysis_recovery_generation = None
             if getattr(analysis_result, "live_publish_status", None) == "recovery_required":
                 analysis_recovery_generation = self._request_full_analysis_recovery(
@@ -1342,15 +1322,8 @@ class ContextorGUI:
                 )
             current_incident = self._live_recovery_incident(path)
             if current_incident is None:
-                self._start_live_watcher(path, initial_seq=pre_seq)
-                if not errors:
-                    messagebox.showinfo("OK", "No issues found. Repository is healthy!")
-                    return
-                msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
-                messagebox.showwarning("Issues Detected", msg)
-                return
+                return {"status": "not_required"}
 
-            self._start_live_watcher(path, initial_seq=pre_seq)
             generation = None
             if (
                 analysis_recovery_generation is not None
@@ -1375,26 +1348,15 @@ class ContextorGUI:
             ):
                 generation = starting_generation
             if generation is None:
-                self._set_live_status(
-                    "LIVE recovery verification failed; full repository analysis may be required."
-                )
-                if errors:
-                    msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
-                    messagebox.showwarning("Issues Detected", msg)
-                else:
-                    messagebox.showinfo(
-                        "Analysis complete",
-                        "No static issues found. LIVE recovery verification failed; "
-                        "full repository analysis may be required.",
-                    )
-                return
+                return {"status": "generation_unavailable"}
 
             self._set_live_recovery_verification_state(
                 path, generation, "verifying"
             )
-
             verification_client = None
             try:
+                from contextor.core.live_state import connect
+
                 verification_client = connect(Path(path))
                 if verification_client is None:
                     verification = {"status": "error", "error": "recovery_live_missing"}
@@ -1452,15 +1414,7 @@ class ContextorGUI:
                             cleared = True
 
             if cleared:
-                self._set_live_status(
-                    "LIVE recovery verified; incremental updates resumed."
-                )
-                if not errors:
-                    messagebox.showinfo("OK", "LIVE recovery verified; incremental updates resumed.")
-                else:
-                    msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
-                    messagebox.showwarning("Issues Detected", msg)
-                return
+                return {"status": "cleared"}
 
             if (
                 isinstance(certificate, dict)
@@ -1476,6 +1430,122 @@ class ContextorGUI:
             self._set_live_recovery_verification_state(
                 path, generation, "failed"
             )
+            return {"status": "failed"}
+
+        def task(log=None, progress_callback=None):
+            nonlocal pre_seq
+            try:
+                from contextor.core.live_state import connect
+
+                live_client = connect(Path(path))
+                if live_client is not None:
+                    response = live_client.get_events(limit=1)
+                    pre_seq = int(response.get("latest_seq", 0))
+            except Exception:
+                pre_seq = 0
+
+            errors, analysis_result = run_full_analysis_exclusive(
+                path,
+                owner="desktop_analysis",
+                log=log,
+                progress_callback=progress_callback,
+                is_cancelled=lambda: getattr(self.progress_bar, "is_cancelled", False),
+                cycle_source_preparation_preview=True,
+                cycle_partial_source_publication_opt_in=True,
+            )
+            incident_before_publish_result = self._live_recovery_incident(path)
+            from contextor.ui.cycle_warning_presentation import (
+                filter_installed_desktop_cycle_errors,
+            )
+            errors = filter_installed_desktop_cycle_errors(
+                errors,
+                analysis_result,
+                path,
+            )
+            from contextor.ui.cycle_warning_presentation import (
+                read_authenticated_soft_dependent_cycle_diagnostic,
+            )
+            potential_diagnostic.update(
+                read_authenticated_soft_dependent_cycle_diagnostic(
+                    analysis_result,
+                    path,
+                )
+            )
+            recovery_outcome.update(
+                verify_recovery_on_worker(
+                    analysis_result,
+                    incident_before_publish_result,
+                )
+            )
+            return errors, analysis_result
+
+        def on_success(outcome):
+            errors, analysis_result = outcome
+            from contextor.ui.cycle_warning_presentation import (
+                format_soft_dependent_cycle_diagnostic,
+            )
+            potential_message = format_soft_dependent_cycle_diagnostic(
+                potential_diagnostic
+            )
+            detail_lines = [
+                f"{error.kind}: {error.message}"
+                for error in errors
+            ]
+            if (
+                potential_diagnostic.get("availability") != "fresh"
+                or potential_diagnostic.get("count", 0) > 0
+            ):
+                detail_lines.append(potential_message)
+            elif not errors:
+                potential_message = ""
+            details = "\n".join(detail_lines)
+            current_incident = self._live_recovery_incident(path)
+            recovery_status = recovery_outcome.get("status")
+            if recovery_status == "not_required" and current_incident is None:
+                self._start_live_watcher(path, initial_seq=pre_seq)
+                if (
+                    not errors
+                    and potential_diagnostic.get("availability") == "fresh"
+                    and potential_diagnostic.get("count") == 0
+                ):
+                    messagebox.showinfo("OK", "No issues found. Repository is healthy!")
+                    return
+                messagebox.showwarning(
+                    "Issues Detected" if errors or potential_diagnostic.get("count", 0) else "Analysis complete",
+                    details or potential_message,
+                )
+                return
+
+            self._start_live_watcher(path, initial_seq=pre_seq)
+            if recovery_status == "generation_unavailable" or (
+                recovery_status == "not_required" and current_incident is not None
+            ):
+                self._set_live_status(
+                    "LIVE recovery verification failed; full repository analysis may be required."
+                )
+                if errors:
+                    messagebox.showwarning("Issues Detected", details)
+                else:
+                    messagebox.showinfo(
+                        "Analysis complete",
+                        "No static issues found. LIVE recovery verification failed; "
+                        "full repository analysis may be required.\n\n"
+                        + potential_message,
+                    )
+                return
+            if recovery_status == "cleared":
+                self._set_live_status(
+                    "LIVE recovery verified; incremental updates resumed."
+                )
+                if not errors:
+                    messagebox.showinfo(
+                        "OK",
+                        "LIVE recovery verified; incremental updates resumed.\n\n"
+                        + potential_message,
+                    )
+                else:
+                    messagebox.showwarning("Issues Detected", details)
+                return
 
             self._set_live_status(
                 "LIVE recovery verification failed; full repository analysis may be required."
@@ -1484,11 +1554,11 @@ class ContextorGUI:
                 messagebox.showinfo(
                     "Analysis complete",
                     "No static issues found. LIVE recovery verification failed; "
-                    "full repository analysis may be required.",
+                    "full repository analysis may be required.\n\n"
+                    + potential_message,
                 )
             else:
-                msg = "\n".join([f"{e.kind}: {e.message}" for e in errors])
-                messagebox.showwarning("Issues Detected", msg)
+                messagebox.showwarning("Issues Detected", details)
 
         def on_error(exc):
             if recovery_generation is not None:
diff --git a/tests/test_soft_dependent_potential_cycles.py b/tests/test_soft_dependent_potential_cycles.py
index 368f308..4123dd6 100644
--- a/tests/test_soft_dependent_potential_cycles.py
+++ b/tests/test_soft_dependent_potential_cycles.py
@@ -49,7 +49,7 @@ def test_acyclic_soft_edge_and_duplicate_hard_edge_do_not_create_potential():
 
 def test_freshness_gate_never_asserts_zero_for_missing_or_stale_graph():
     state = SimpleNamespace(
-        resync_required=False, cycles_state="fresh", cycles=[],
+        cycles_state="fresh", cycles=[],
         collisions_state="fresh", collisions=[],
         syntax_diagnostics_state="fresh", syntax_diagnostics_by_path={},
         dependency_graph=SimpleNamespace(
diff --git a/tests/test_cycle_semantics_desktop_potential_cycles.py b/tests/test_cycle_semantics_desktop_potential_cycles.py
new file mode 100644
index 0000000..37724f2
--- /dev/null
+++ b/tests/test_cycle_semantics_desktop_potential_cycles.py
@@ -0,0 +1,279 @@
+"""Desktop soft-cycle presentation is bound to a verified LIVE generation."""
+
+from __future__ import annotations
+
+from pathlib import Path
+import subprocess
+import sys
+from threading import Thread, get_ident
+from types import SimpleNamespace
+from unittest.mock import MagicMock
+
+import pytest
+
+from contextor.ui import gui
+from contextor.ui.gui import ContextorGUI
+from contextor.ui.cycle_warning_presentation import (
+    format_soft_dependent_cycle_diagnostic,
+    read_authenticated_soft_dependent_cycle_diagnostic,
+)
+from contextor.core.live_state.runtime import (
+    _repository_canonical_query_handler,
+)
+from tests.test_cycle_semantics_desktop_warning_presentation import (
+    _analysis_result,
+)
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture,
+    _owner,
+)
+from tests.test_original_worker_official_full_live_publication import (
+    _official_live,
+)
+from tests.test_original_worker_partial_scc_preparation import TWO_PASS
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _witness_repo(root):
+    (root / "pkg").mkdir(parents=True)
+    (root / "a.py").write_text("import b\nvalue = 1\n", encoding="utf-8")
+    (root / "b.py").write_text("import a\nvalue = 2\n", encoding="utf-8")
+    (root / "x.py").write_text("import y\nvalue = 3\n", encoding="utf-8")
+    (root / "y.py").write_text("import x\nvalue = 4\n", encoding="utf-8")
+    (root / "pkg" / "__init__.py").write_text("pass\n", encoding="utf-8")
+    (root / "pkg" / "a.py").write_text(
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n    import pkg.b\n"
+        "value = 1\n",
+        encoding="utf-8",
+    )
+    (root / "pkg" / "b.py").write_text(
+        "from pkg.a import value\n", encoding="utf-8",
+    )
+
+
+def _gui_controller(root, monkeypatch):
+    controller = SimpleNamespace(
+        repo_path_var=SimpleNamespace(get=lambda: str(root)),
+        root=object(),
+        progress_bar=SimpleNamespace(is_cancelled=False),
+        log_box=None,
+        cpu_indicator=None,
+        stop_btn=None,
+        _busy_buttons=lambda: (),
+        _live_recovery_incident=lambda _path: None,
+        _start_live_watcher=lambda *_args, **_kwargs: None,
+    )
+
+    def run_inline(root_widget, progress_bar, task, *, on_success, **_kwargs):
+        outcome = []
+        failure = []
+
+        def run_worker():
+            controller._analysis_worker_thread_id = get_ident()
+            try:
+                outcome.append(task())
+            except BaseException as exc:
+                failure.append(exc)
+
+        worker = Thread(target=run_worker)
+        worker.start()
+        worker.join(timeout=120)
+        assert not worker.is_alive()
+        if failure:
+            raise failure[0]
+        outcome = outcome[0]
+        on_success(outcome)
+        return outcome
+
+    monkeypatch.setattr(gui, "run_with_progress", run_inline)
+    return controller
+
+
+def _install_diagnostics_handler(server):
+    server._canonical_query_handler = _repository_canonical_query_handler
+
+
+def test_live_full_to_desktop_reports_potential_without_hard_cycle_warning(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = tmp_path / "repo"
+    root.mkdir()
+    _witness_repo(root)
+    warning = MagicMock()
+    info = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
+    monkeypatch.setattr(gui.messagebox, "showinfo", info)
+    controller = _gui_controller(root, monkeypatch)
+    main_thread_id = get_ident()
+
+    with _official_live(root, monkeypatch) as (client, server, identity, _calls):
+        _install_diagnostics_handler(server)
+        ContextorGUI.analyze(controller)
+        assert controller._analysis_worker_thread_id != main_thread_id
+        errors, result = controller._full_analysis_done
+
+        assert result.live_publish_status == "success"
+        assert result.live_publish_revision == result.live_publish_expected_revision
+        assert result.live_publish_service_instance_id == server.endpoint.service_instance_id
+        assert identity.repo_id
+        installed = client.snapshot()
+        graph = installed["state"].dependency_graph
+        assert "pkg.b" not in graph.hard_edges["pkg.a"]
+        assert "pkg.a" in graph.hard_edges["pkg.b"]
+        assert "pkg.b" in graph.soft_edges["pkg.a"]
+
+        response = client.canonical_query("diagnostics_summary", payload={})
+        assert response.get("status") == "ok", response
+        summary = response["result"]
+        diagnostic = summary["soft_dependent_potential_cycles"]
+        assert response["revision"] == result.live_publish_revision
+        assert diagnostic["availability"] == "fresh", {
+            "diagnostic": diagnostic,
+            "resync_required": getattr(installed["state"], "resync_required", None),
+            "cycles_state": installed["state"].cycles_state,
+            "hard": installed["state"].dependency_graph.hard_edges,
+            "soft": installed["state"].dependency_graph.soft_edges,
+        }
+        assert diagnostic["count"] == 1
+        assert diagnostic["components"][0]["members"] == ("pkg.a", "pkg.b")
+        assert diagnostic["components"][0]["soft_only_internal_edges"] == (
+            ("pkg.a", "pkg.b"),
+        )
+
+        report = client.get_installed_cycle_warning_projection()
+        assert report["revision"] == response["revision"]
+        assert report["model_pass_count"] > 0
+        assert report["active_warning_count"] == 0
+        assert ("pkg.a", "pkg.b", "pkg.a") not in report["structural_paths"]
+        assert ("pkg.a", "pkg.b", "pkg.a") not in report["model_pass_paths"]
+        assert not [error for error in errors if error.kind == "ArchitectureCycle"]
+        warning.assert_called_once()
+        message = warning.call_args.args[1]
+        assert "POTENTIAL cycle involving uncertain dependencies" in message
+        assert "pkg.a" in message and "pkg.b" in message
+        assert "does not prove CPython will execute" in message
+        info.assert_not_called()
+
+
+def test_verified_control_reports_zero_and_keeps_healthy_success(tmp_path, isolated_dirs, monkeypatch):
+    root = tmp_path / "control"
+    root.mkdir()
+    for name, source in TWO_PASS.items():
+        (root / f"{name}.py").write_text(source, encoding="utf-8")
+    warning = MagicMock()
+    info = MagicMock()
+    monkeypatch.setattr(gui.messagebox, "showwarning", warning)
+    monkeypatch.setattr(gui.messagebox, "showinfo", info)
+    controller = _gui_controller(root, monkeypatch)
+
+    with _official_live(root, monkeypatch) as (client, _server, _identity, _calls):
+        _install_diagnostics_handler(_server)
+        ContextorGUI.analyze(controller)
+        response = client.canonical_query("diagnostics_summary", payload={})
+        assert response.get("status") == "ok", response
+        summary = response["result"]
+        diagnostic = summary["soft_dependent_potential_cycles"]
+        assert diagnostic["availability"] == "fresh"
+        assert diagnostic["count"] == 0
+        assert "Repository is healthy!" in info.call_args.args[1]
+        warning.assert_not_called()
+
+
+def test_stale_or_mismatched_live_authority_is_not_verified_zero(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    with _owner(state, metadata) as (server, client):
+        _install_diagnostics_handler(server)
+        result = _analysis_result(metadata, server)
+        monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)
+
+        state.cycles_state = "stale"
+        stale = read_authenticated_soft_dependent_cycle_diagnostic(result, str(root))
+        assert stale["availability"] == "unavailable"
+        assert stale["count"] is None
+        state.cycles_state = "fresh"
+
+        original_query = client.canonical_query
+        monkeypatch.setattr(
+            client,
+            "canonical_query",
+            lambda *args, **kwargs: dict(original_query(*args, **kwargs), revision=metadata.revision + 1),
+        )
+        mismatch = read_authenticated_soft_dependent_cycle_diagnostic(result, str(root))
+        assert mismatch["availability"] == "unavailable"
+        assert mismatch["count"] is None
+
+
+def test_failed_publication_cannot_authorize_zero(tmp_path, monkeypatch):
+    def forbidden(_root):
+        pytest.fail("failed publication must be rejected before LIVE query")
+
+    monkeypatch.setattr("contextor.core.live_state.connect", forbidden)
+    diagnostic = read_authenticated_soft_dependent_cycle_diagnostic(
+        SimpleNamespace(live_publish_status="failed"), str(tmp_path),
+    )
+    assert diagnostic["availability"] == "unavailable"
+    assert diagnostic["count"] is None
+    text = format_soft_dependent_cycle_diagnostic(diagnostic)
+    assert "absence of potential cycles was not established" in text
+
+
+def test_desktop_presentation_bounds_component_samples():
+    diagnostic = {
+        "availability": "fresh",
+        "count": 1,
+        "components": ({
+            "members": tuple(f"module.{index}" for index in range(8)),
+            "member_count": 5000,
+            "soft_only_internal_edges": tuple(
+                (f"module.{index}", f"module.{index + 1}")
+                for index in range(8)
+            ),
+            "soft_only_internal_edge_count": 12000,
+        },),
+    }
+    message = format_soft_dependent_cycle_diagnostic(diagnostic)
+    assert "5000 modules" in message
+    assert "showing 8 of 12000 edges" in message
+    assert len(message) < 1500
+
+
+def test_wrong_repository_identity_is_not_authorized(tmp_path, isolated_dirs, monkeypatch):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+    wrong_root = tmp_path / "other"
+    wrong_root.mkdir()
+    with _owner(state, metadata) as (server, client):
+        _install_diagnostics_handler(server)
+        monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: client)
+        diagnostic = read_authenticated_soft_dependent_cycle_diagnostic(
+            _analysis_result(metadata, server), str(wrong_root),
+        )
+    assert diagnostic["availability"] == "unavailable"
+    assert diagnostic["count"] is None
+
+
+@pytest.mark.skipif(sys.version_info[:3] != (3, 15, 2), reason="fresh CPython 3.15.2 runtime oracle")
+def test_end_to_end_behavior_in_fresh_cpython_process():
+    repository = Path(__file__).resolve().parents[1]
+    target = (
+        "tests/test_cycle_semantics_desktop_potential_cycles.py::"
+        "test_live_full_to_desktop_reports_potential_without_hard_cycle_warning"
+    )
+    script = (
+        "import sys; sys.path.insert(0, sys.argv[1]); "
+        "import pytest; raise SystemExit(pytest.main(['-q', sys.argv[2]]))"
+    )
+    completed = subprocess.run(
+        [sys.executable, "-I", "-c", script, str(repository), target],
+        cwd=repository,
+        capture_output=True,
+        text=True,
+        check=False,
+    )
+    assert completed.returncode == 0, completed.stdout + completed.stderr
```

## FINAL_VERDICT

SCOPED IMPLEMENTATION AND ISOLATED END-TO-END PASS. CURRENT CANONICAL OWNER ADOPTION AND NATIVE DESKTOP RENDERING REMAIN UNVERIFIED; no global FINAL PASS is claimed. STOP for auditor review.
