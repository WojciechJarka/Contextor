# P2-D1 — ujawnienie założenia standardowych builtins

STATUS: SOURCE_AND_TARGETED_TEST_PASS; RUNTIME_ADOPTION_NOT_CERTIFIED. HEAD before edit: `bd764de651d0cb0f125477ea42f838f8ad5c4b58`. No FULL, restart, commit or push. Unrelated pre-existing `audyt.txt` was not changed.

## FILES_CHANGED

- `contextor/core/cycle_semantics/model_environment.py`
- `contextor/core/cycle_semantics/package_model.py`
- `contextor/core/cycle_semantics/live_warning_diagnostics_summary.py`
- `contextor/mcp/tools/get_live_events.py`
- `contextor/mcp/docs/get_live_events.json`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_live_warning_diagnostics_summary.py`
- `tests/test_cycle_semantics_mcp_live_warning_view.py`

`walkthrough.md` is the report only.

## CONTRACT_BEFORE_AFTER

DIRECT_EVIDENCE before: P2-R3's isolated CPython 3.15.2 witness showed ordinary MODEL_PASS for a supported cyclic package with `class E(ValueError): pass`, while pre-import replacement/deletion of `builtins.ValueError` made CPython fail. The model checks a module namespace slot, not the runtime builtin object. The ordinary assessment, fresh diagnostic summary and MCP warning view did not expose this initial-environment precondition.

After: one independent constant defines the exact precondition. `PackageImportAssessment` exposes it through a read-only property outside dataclass fields, so `asdict`, source-evidence fingerprints, and receipt structure have no new field. Fresh diagnostic and MCP warning views expose the same constant; unavailable paths retain their original shape. No evaluator steps, guards, outcomes, evidence_scope, authenticated owner warning-report schema or IPC code changed. The MCP documentation now states the static authority boundary. This metadata change is semantically justified by the independent CPython differential, not by a passing test alone.

## TARGETED_TESTS

- Focused package-model new test plus R9/R11 guards: 4 passed, 201 deselected. After strengthening the new test to exercise an actual assumed frozen dataclass with `@property`, that single test passed again (1 passed, 204 deselected).
- Direct diagnostic-summary and MCP warning-view test files: 33 passed. Their assertions cover fresh metadata, stale/unavailable omission, and unchanged structural/active counts.
- Direct receipt and warning-projection subset: 5 passed, 55 deselected. Together with the unchanged dataclass field set and unchanged source/receipt paths, this supports no classification, eligibility, receipt or fingerprint-contract change; it is not a new global certification.
- Scoped source/test/docs `git diff --check`: passed before this report. The report embeds literal full diff context lines, including space-prefixed blank context lines; checking the report itself flags those literal lines as trailing whitespace. No full pytest suite was run.

## MCP_POST_CHANGE_AUDIT

Before edit: LIVE revision 1203, 16 fresh hard structural DFS cycle paths, one soft-dependent potential SCC, zero syntax errors; `cycle_semantics` stale. The Desktop watcher accepted changed Python sources at revisions 1204–1210 and the final strengthened test at 1214. Intermediate unchanged watcher events 1211–1213 were observed. No `update_file` was called. At revision 1214, Contextor reports fresh graph, topology and cycles, 16 hard DFS cycle paths and one soft-dependent potential SCC, zero syntax errors, no advisory warning. The new `model_environment` module has zero outbound dependencies and only expected inbound consumers, so it introduces no import cycle. This is graph evidence, not runtime adoption. `cycle_semantics` remains stale.

## RUNTIME_ADOPTION_BOUNDARY

`package_model.py`, `live_warning_diagnostics_summary.py`, and `mcp/tools/get_live_events.py` changed on disk and were seen by the watcher. The running MCP server process has not been restarted/reloaded, so its current `get_live_events` code/schema adoption is UNKNOWN. New local tests imported the edited files and passed; watcher revision and fresh graph do not certify process reload. A later stage requiring live MCP behavior must first verify runtime freshness/schema/version after an authorized manual reload. No reload or production FULL was performed.

## FULL_DIFFS

The following are full actual diffs for every source/test/docs file in FILES_CHANGED. The report file itself is excluded.

```diff
diff --git a/contextor/core/cycle_semantics/model_environment.py b/contextor/core/cycle_semantics/model_environment.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/model_environment.py
@@ -0,0 +1,5 @@
+"""Environmental precondition for restricted static cycle models."""
+
+STANDARD_BUILTINS_PRECONDITION = (
+    "CONVENTIONAL_BUILTINS_ASSUMED_NOT_RUNTIME_ATTESTED"
+)
diff --git a/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py b/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
index 1caf029..bc36f4e 100644
--- a/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
+++ b/contextor/core/cycle_semantics/live_warning_diagnostics_summary.py
@@ -19,6 +19,7 @@ from .live_cycle_warning_query import (
     _AUTHORITY as _PROJECTION_AUTHORITY,
     _BINDING as _PROJECTION_BINDING,
 )
+from .model_environment import STANDARD_BUILTINS_PRECONDITION
 
 
 _IDENTITY_KEYS = (
@@ -176,6 +177,7 @@ def project_locked_warning_diagnostics_summary(
             "model_pass_count": warning_report["model_pass_count"],
             "warning_availability": "fresh",
             "warning_semantics": _WARNING_SEMANTICS,
+            "builtin_environment_precondition": STANDARD_BUILTINS_PRECONDITION,
         }
         result["attention_required"] = any(
             type(value) is int and value > 0
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 6881435..47ed25f 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -11,6 +11,9 @@ import sys
 from collections.abc import Mapping
 from dataclasses import dataclass, field, replace
 
+from contextor.core.cycle_semantics.model_environment import (
+    STANDARD_BUILTINS_PRECONDITION,
+)
 from contextor.core.cycle_semantics.package_layout import build_package_layout
 from contextor.core.cycle_semantics.namespace_path_model import (
     SearchPortion,
@@ -68,6 +71,10 @@ class PackageImportAssessment:
         tuple[AssumedFrozenDataclassDecoration, ...]
     ) = ()
 
+    @property
+    def builtin_environment_precondition(self) -> str:
+        return STANDARD_BUILTINS_PRECONDITION
+
 
 @dataclass(frozen=True)
 class _Step:
@@ -1336,7 +1343,10 @@ def evaluate_package_import_order(
     Indexed package __init__ IDs are translated to logical package names.
     The operation budget prevents unbounded model execution.
 
-    Results cannot certify general Python import safety.
+    MODEL_PASS assesses the restricted model assuming conventional builtin
+    bindings. The evaluator does not attest the actual contents of
+    __builtins__, builtins, or the import environment, and cannot certify
+    general Python import safety.
     """
     events: list[PackageModelEvent] = []
     assumed_external_imports: list[ReachedUnmodeledImport] = []
diff --git a/contextor/mcp/docs/get_live_events.json b/contextor/mcp/docs/get_live_events.json
index c095a8b..adb561b 100644
--- a/contextor/mcp/docs/get_live_events.json
+++ b/contextor/mcp/docs/get_live_events.json
@@ -14,7 +14,7 @@
     "Committed incremental ``update_file`` events may include optional post-commit ``diagnostic_changes`` evidence with exact bounded shape ``{total, truncated, items}``; ``items`` contains at most three deterministic details.",
     "Each diagnostic item exposes ``action`` (``ADDED`` or ``RESOLVED``), ``diagnostic_kind`` (``syntax``, ``collision``, or ``cycle``), and a stable JSON-safe ``diagnostic_key``. Syntax items include ``source_path`` and ``line_number``/``column_number`` when attributable; collision items expose canonical structured collision fields; cycle items expose ``cycle_nodes``.",
     "Diagnostic changes are emitted only when both before and after canonical diagnostic-family states are fresh. Their absence is not proof of zero diagnostics when a family is stale or deferred. Canonical state remains authoritative; the runtime JSONL trace carries the full committed diagnostic delta for operational evidence.",
-    "When the LIVE owner can verify the current installed cycle warning partition, successful responses expose ``cycle_warning_view`` with structural, MODEL_PASS and active-warning counts and paths. Structural cycle count remains unchanged. This is static-model acceptance evidence, not runtime execution safety.",
+    "When the LIVE owner can verify the current installed cycle warning partition, successful responses expose ``cycle_warning_view`` with structural, MODEL_PASS and active-warning counts and paths. Structural cycle count remains unchanged. MODEL_PASS assumes conventional builtin bindings; the model does not attest the actual builtins state. Suppressing a warning does not prove execution safety in a modified environment. This is static-model acceptance evidence, not runtime execution safety.",
     "Successful responses also expose ``cycle_warning_transitions`` for the latest installed commit only. Valid transitions distinguish ``STRUCTURAL_ADDED``, ``STRUCTURAL_REMOVED``, ``MODEL_ACCEPTED`` and ``WARNING_REACTIVATED``. Their absence or an unavailable result is not evidence of zero transitions. The checkpoint is not a reconstruction of the retained event history.",
     "``diagnostic_changes`` in the journal describe historical structural changes, not current active cycle warnings. The journal is preserved without deleting or rewriting its events. Current active warnings must be read from a fresh ``cycle_warning_view``.",
     "Warning projections require matching LIVE revision and activity epoch. If the owner, projection or checkpoint is unavailable or inconsistent, the warning view or transitions are marked ``unavailable`` without fabricated active-warning counts.",
diff --git a/contextor/mcp/tools/get_live_events.py b/contextor/mcp/tools/get_live_events.py
index 9906480..df6d7bd 100644
--- a/contextor/mcp/tools/get_live_events.py
+++ b/contextor/mcp/tools/get_live_events.py
@@ -1,6 +1,10 @@
 import json
 from pathlib import Path
 
+from contextor.core.cycle_semantics.model_environment import (
+    STANDARD_BUILTINS_PRECONDITION,
+)
+
 
 def _current_cycle_warning_view(client, events):
     """Read current warning state without reinterpreting historical events."""
@@ -68,6 +72,7 @@ def _current_cycle_warning_view(client, events):
     return {
         "status": "fresh",
         "scope": "CURRENT_INSTALLED_GENERATION_STATIC_MODEL_NOT_RUNTIME_SAFETY",
+        "builtin_environment_precondition": STANDARD_BUILTINS_PRECONDITION,
         "revision": report["revision"],
         "activity_epoch": report["activity_epoch"],
         "structural_count": report["structural_count"],
diff --git a/tests/test_cycle_semantics_live_warning_diagnostics_summary.py b/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
index 07ca16a..8d073e1 100644
--- a/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
+++ b/tests/test_cycle_semantics_live_warning_diagnostics_summary.py
@@ -16,6 +16,9 @@ from contextor.core.live_state.runtime import (
 from contextor.core.cycle_semantics.live_warning_diagnostics_summary import (
     project_locked_warning_diagnostics_summary,
 )
+from contextor.core.cycle_semantics.model_environment import (
+    STANDARD_BUILTINS_PRECONDITION,
+)
 from tests.test_cycle_semantics_live_installed_partial_claims import (
     _fixture,
     _owner,
@@ -68,6 +71,10 @@ def test_t01_t03_installed_partial_scc_controls_attention(
         assert summary["cycles"]["model_pass_count"] == accepted
         assert summary["cycles"]["active_warning_count"] == active
         assert summary["cycles"]["warning_availability"] == "fresh"
+        assert (
+            summary["cycles"]["builtin_environment_precondition"]
+            == STANDARD_BUILTINS_PRECONDITION
+        )
         assert summary["attention_required"] is (active > 0)
 
         assert original["cycles"]["count"] == 2
@@ -165,6 +172,7 @@ def test_t08_stale_structural_inventory_never_claims_zero(
 
         assert summary["cycles"]["count"] is None
         assert "active_warning_count" not in summary["cycles"]
+        assert "builtin_environment_precondition" not in summary["cycles"]
         assert summary["cycles"]["availability"] == "stale"
 
 
@@ -239,6 +247,7 @@ def test_t12_pure_projection_rejects_wrong_revision(
         assert result is raw
         assert raw == original
         assert "active_warning_count" not in result["cycles"]
+        assert "builtin_environment_precondition" not in result["cycles"]
 
 
 def test_t13_pure_projection_rejects_count_mismatch(
diff --git a/tests/test_cycle_semantics_mcp_live_warning_view.py b/tests/test_cycle_semantics_mcp_live_warning_view.py
index 58a310f..ba18c50 100644
--- a/tests/test_cycle_semantics_mcp_live_warning_view.py
+++ b/tests/test_cycle_semantics_mcp_live_warning_view.py
@@ -8,6 +8,9 @@ import json
 import pytest
 
 from contextor.mcp.tools.get_live_events import get_live_events
+from contextor.core.cycle_semantics.model_environment import (
+    STANDARD_BUILTINS_PRECONDITION,
+)
 from tests.test_cycle_semantics_live_installed_partial_claims import (
     _fixture, _owner,
 )
@@ -54,6 +57,10 @@ def test_t01_t03_real_installed_partial_warning_view(
 
         view = result["cycle_warning_view"]
         assert view["status"] == "fresh"
+        assert (
+            view["builtin_environment_precondition"]
+            == STANDARD_BUILTINS_PRECONDITION
+        )
         assert view["revision"] == metadata.revision
         assert view["activity_epoch"] == server._activity_epoch
         assert view["structural_count"] == 2
@@ -104,6 +111,7 @@ def test_t05_stale_cycles_never_become_false_zero_warnings(
         )["cycle_warning_view"]
 
         assert view["status"] == "unavailable"
+        assert "builtin_environment_precondition" not in view
         assert "active_warning_count" not in view
         assert "active_warning_paths" not in view
 
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index bf0bce6..5bbfe1a 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -9,6 +9,9 @@ import pytest
 from contextor.core.cycle_semantics.package_model import (
     evaluate_package_import_order,
 )
+from contextor.core.cycle_semantics.model_environment import (
+    STANDARD_BUILTINS_PRECONDITION,
+)
 
 
 def _model(source, entry):
@@ -21,6 +24,71 @@ def _model(source, entry):
     )
 
 
+def test_builtin_environment_precondition_is_metadata_not_dataclass_field():
+    sources = {
+        "pkg.__init__": ast.parse(
+            "class E(ValueError):\n"
+            "    pass\n"
+            "from .child import token\n"
+        ),
+        "pkg.child": ast.parse("from . import E\ntoken = 7\n"),
+    }
+    options = {
+        "annotation_semantics": "DEFERRED",
+        "_compile_on_first_import": True,
+    }
+    ordinary = evaluate_package_import_order(sources, "pkg", **options)
+    assert ordinary.outcome == "MODEL_PASS"
+    assert ordinary.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert (
+        ordinary.builtin_environment_precondition
+        == STANDARD_BUILTINS_PRECONDITION
+    )
+    assert "builtin_environment_precondition" not in asdict(ordinary)
+
+    shadowed = dict(sources)
+    shadowed["pkg.__init__"] = ast.parse(
+        "ValueError = 1\n"
+        "class E(ValueError):\n"
+        "    pass\n"
+        "from .child import token\n"
+    )
+    assert (
+        evaluate_package_import_order(shadowed, "pkg", **options).outcome
+        == "UNKNOWN"
+    )
+
+    conditional_sources = {
+        "pkg.__init__": ast.parse(
+            "from dataclasses import dataclass\n"
+            "@dataclass(frozen=True)\n"
+            "class D:\n"
+            "    @property\n"
+            "    def value(self):\n"
+            "        return 1\n"
+            "from .child import token\n"
+        ),
+        "pkg.child": ast.parse("from . import D\ntoken = 7\n"),
+    }
+    conditional = evaluate_package_import_order(
+        conditional_sources, "pkg", **options,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+    assert conditional.outcome == "MODEL_PASS"
+    assert conditional.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    assert (
+        conditional.builtin_environment_precondition
+        == STANDARD_BUILTINS_PRECONDITION
+    )
+    assert len(conditional.assumed_external_imports) == 1
+    assert len(conditional.assumed_dataclass_decorations) == 1
+    assert "builtin_environment_precondition" not in asdict(conditional)
+
+
 def test_frozen_dataclass_default_model_unknown():
     result = _model(
         {"pkg.__init__": (
```

## FINAL_VERDICT

SOURCE_AND_TARGETED_TEST_PASS_PENDING_RUNTIME_ADOPTION. The requested metadata contract is implemented and locally verified; no new hard/soft cycle appeared in fresh Contextor graph evidence. Do not claim current running MCP adoption or fresh installed cycle semantics.
