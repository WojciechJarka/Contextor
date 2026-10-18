# TASK
CONTEXTOR_B0G4C38A1_IMMUTABLE_REPORT_CONTRACT_HARDENING — exact auditor-approved focused implementation. No LIVE state/schema integration.

## HEAD_BEFORE / HEAD_AFTER / GIT_STATUS
HEAD_BEFORE=26f62d757511ff0f8f707c2b7ed461948eebf295
HEAD_AFTER=26f62d757511ff0f8f707c2b7ed461948eebf295
GIT_STATUS before and after: `M walkthrough.md`, `?? contextor/core/cycle_semantics/contracts.py`, `?? tests/test_cycle_semantics_contracts.py`. Both source/test files remain untracked from C38A, so the FULL_DIFFS below compare the exact C38A pre-edit file contents reconstructed from that report's complete new-file diffs to current files. This is the current task's complete change, not an aggregate Git diff against HEAD. No Git mutation.

## PRECHECK
DIRECT_EVIDENCE: Contextor MCP used first; current documentation read. `get_symbol_implementation` returned complete `CycleSemanticsSnapshot` at `C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\contracts.py:116-317`, `CyclicImportSiteReport` at `...\edge_sites.py:52-56`, `ConditionalDiscoveryReport` at `...\conditional_discovery.py:35-50`, all workspace_sync=verified at LIVE 483. `get_source_range` returned all 217 pre-edit test lines. `get_module_context` showed contracts direct consumer only `tests.test_cycle_semantics_contracts`, outbound to conditional_discovery and edge_sites, no unrelated production consumer; both target modules verified. Literal Git/source checks then confirmed exact patch anchors. No material source drift. Before edit: LIVE 483, epoch bbd40ce1942841df94718acedc12561f, resync_required=false, syntax 0, collisions 0, structural cycle paths 16, all relevant families fresh. Authority identity read directly with `LiveStateClient(is_owner=False)` and endpoint match; no ownership claim.

## FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\contracts.py
- C:\Temp\Contextor_Repo\tests\test_cycle_semantics_contracts.py
- `walkthrough.md` overwritten solely as report, excluded from source/test changes.

## RUNTIME_TYPE_VALIDATION / RECURSIVE_IMMUTABILITY_VALIDATION / SCC_REPORT_CONSISTENCY
CONTRACT_PROVED: `CycleSemanticsSnapshot.__post_init__` now imports the two report classes only at validation time, requires their exact runtime types, then calls `_require_deep_immutable` on each. The pure helper accepts exact scalar primitive types, tuple/frozenset and frozen dataclass fields recursively, rejects list/dict/unsupported nested evidence, and rejects an object cycle with an active identity guard. Existing graph/source/version/coverage checks remain. Topology cyclic members must equal the snapshot cohort, and import-site component count/order/members must match topology components. The five new tests assert wrong report class, duck type, nested mutable candidates/components and component/topology divergence. Valid complete/partial fixtures remain accepted.

## CONTRACT_VERSION / SOURCE_BINDING_CLAIMS / RUNTIME_EXECUTION_CLAIMS
CONTRACT_VERSION=1.0.0 unchanged. SOURCE_BINDING_CLAIMS remains `NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY`; RUNTIME_EXECUTION_CLAIMS remains `UNKNOWN_NOT_EVALUATED`. No new AST/source read, IPC, LIVE import, analyzed-module import, persistence or freshness ownership was added. TYPE_CHECKING imports remain unchanged; new runtime imports are inside `__post_init__` only.

## NEW_TESTS / FOCUSED_REGRESSION_RESULTS / PICKLE_ROUNDTRIP / COLD_START_IMPORT
NEW_TESTS: `test_rejects_mutable_conditional_discovery`, `test_rejects_duck_typed_import_sites`, `test_rejects_nested_mutable_conditional_evidence`, `test_rejects_nested_mutable_import_evidence`, `test_rejects_component_topology_divergence` in `C:\Temp\Contextor_Repo\tests\test_cycle_semantics_contracts.py`. Existing 12 test functions retained; total 17 functions and 30 parametrized cases in that module.
FOCUSED_REGRESSION_RESULTS=PASS: `.venv\Scripts\python.exe -B -m pytest -q` on contracts, source_cohort, edge_sites, conditional_discovery, conditional_grouping, public_projection: 88 passed in 3.75s; no skips/xfails. No full suite.
PICKLE_ROUNDTRIP=PASS via retained `test_pickle_roundtrip_preserves_snapshot`. COLD_START_IMPORT=PASS via retained fresh-interpreter `test_cold_contract_import_does_not_import_ui_or_repo_generator`; no GUI/Repo Generator modules imported. These assertions ran in the focused test command.

## LIVE_BEFORE_AFTER / WORKSPACE_SYNC / COLLISIONS_BEFORE_AFTER / STRUCTURAL_CYCLES_BEFORE_AFTER
LIVE_BEFORE_AFTER: revision 483→485, same activity epoch `bbd40ce1942841df94718acedc12561f`, continuous event history, resync_required=false. Watcher events: 484 UPDATED contracts.py (affected contracts and test module), 485 UPDATED test module. Both target modules at revision 485 are workspace_sync=verified and canonical_state=fresh; graph/topology/cycles/collisions fresh. Name collisions 0→0; syntax errors 0→0; structural cycle paths 16→16. Current Contextor module context confirms unchanged ownership direction, contracts inbound only from test and outbound only to edge_sites/conditional_discovery.
Authority before/after identical: repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`, runtime_domain_id `rd1_4bb21e833272147f29727f8174356bdb3dbcba1b2d4965637b97183f8654`, service_instance_id `6f13273feccb46cb9c23fbbfee03afe1`, lease_generation 31, service_pid 11632, process_start_identity 134367226998365614, endpoint_fingerprint `1367eadf1a11448d1a74eec69518da568d80ee42be8f16ce15e54998e989fcbd`. No secrets printed. No `update_file`, FULL analysis or restart.

MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED=NO

## FINAL_VERDICT
B0G4C38A1_PASS. Exact approved patch and five regressions, 88 focused PASS, preserved pickle/cold import, stable authority and diagnostics, both files synchronized. STOP; await `proceduj`.

## FULL_DIFFS
Exact complete current-task diffs follow. Previous C38A new-file contents were reconstructed in memory from the prior walkthrough's complete diffs; no temporary file was created.

### contextor/core/cycle_semantics/contracts.py
```diff
--- a/contextor/core/cycle_semantics/contracts.py
+++ b/contextor/core/cycle_semantics/contracts.py
@@ -15,7 +15,7 @@
 import hashlib
 import json
 from collections.abc import Mapping
-from dataclasses import dataclass
+from dataclasses import dataclass, fields, is_dataclass
 from typing import TYPE_CHECKING
 
 if TYPE_CHECKING:
@@ -56,6 +56,79 @@
             for character in value
         )
     )
+
+
+def _require_deep_immutable(
+    value: object,
+    *,
+    path: str,
+    active: set[int] | None = None,
+) -> None:
+    """Reject mutable or unsupported nested evidence.
+
+    Approved evidence consists of scalar primitives,
+    immutable collections and frozen dataclass values.
+
+    The recursion guard rejects malformed cyclic object
+    structures rather than traversing indefinitely.
+    """
+
+    if type(value) in (
+        str,
+        bytes,
+        int,
+        float,
+        bool,
+        type(None),
+    ):
+        return
+
+    if active is None:
+        active = set()
+
+    identity = id(value)
+
+    if identity in active:
+        raise TypeError(
+            f"{path} contains a recursive object"
+        )
+
+    active.add(identity)
+
+    try:
+        if type(value) in (tuple, frozenset):
+            for member in value:
+                _require_deep_immutable(
+                    member,
+                    path=path,
+                    active=active,
+                )
+            return
+
+        if (
+            is_dataclass(value)
+            and not isinstance(value, type)
+            and getattr(
+                type(value),
+                "__dataclass_params__",
+                None,
+            ) is not None
+            and type(value).__dataclass_params__.frozen
+        ):
+            for item in fields(value):
+                _require_deep_immutable(
+                    getattr(value, item.name),
+                    path=f"{path}.{item.name}",
+                    active=active,
+                )
+            return
+
+        raise TypeError(
+            f"{path} contains mutable or unsupported evidence"
+        )
+
+    finally:
+        active.remove(identity)
 
 
 def fingerprint_hard_edges(
@@ -279,26 +352,63 @@
                 "Unsupported runtime execution claim"
             )
 
-        try:
-            components = (
-                self.import_sites.topology
-                .cyclic_components
-            )
-
-            topology_members = tuple(sorted(
-                module
-                for component in components
-                for module in component.members
-            ))
-
-        except (AttributeError, TypeError):
-            raise ValueError(
-                "Invalid import-site topology"
-            ) from None
+        from .conditional_discovery import (
+            ConditionalDiscoveryReport,
+        )
+        from .edge_sites import CyclicImportSiteReport
+
+        if type(self.import_sites) is not (
+            CyclicImportSiteReport
+        ):
+            raise TypeError(
+                "import_sites must be CyclicImportSiteReport"
+            )
+
+        if type(self.conditional_discovery) is not (
+            ConditionalDiscoveryReport
+        ):
+            raise TypeError(
+                "conditional_discovery must be ConditionalDiscoveryReport"
+            )
+
+        _require_deep_immutable(
+            self.import_sites,
+            path="import_sites",
+        )
+        _require_deep_immutable(
+            self.conditional_discovery,
+            path="conditional_discovery",
+        )
+
+        components = (
+            self.import_sites.topology.cyclic_components
+        )
+
+        topology_members = tuple(sorted(
+            module
+            for component in components
+            for module in component.members
+        ))
 
         if topology_members != self.cyclic_modules:
             raise ValueError(
                 "Import-site topology and cyclic cohort differ"
+            )
+
+        site_components = self.import_sites.components
+
+        if (
+            len(site_components) != len(components)
+            or any(
+                site.members != component.members
+                for site, component in zip(
+                    site_components,
+                    components,
+                )
+            )
+        ):
+            raise ValueError(
+                "Import-site components and topology differ"
             )
 
     @property
```

### tests/test_cycle_semantics_contracts.py
```diff
--- a/tests/test_cycle_semantics_contracts.py
+++ b/tests/test_cycle_semantics_contracts.py
@@ -6,7 +6,8 @@
 import pickle
 import subprocess
 import sys
-from dataclasses import FrozenInstanceError
+from dataclasses import FrozenInstanceError, replace
+from types import SimpleNamespace
 
 import pytest
 
@@ -215,3 +216,80 @@
         check=False,
     )
     assert result.returncode == 0, result.stderr
+
+
+def test_rejects_mutable_conditional_discovery() -> None:
+    with pytest.raises(
+        TypeError,
+        match="conditional_discovery must be",
+    ):
+        _snapshot(
+            conditional_discovery={
+                "candidates": [],
+            },
+        )
+
+
+def test_rejects_duck_typed_import_sites() -> None:
+    import_sites, _ = _reports()
+
+    with pytest.raises(
+        TypeError,
+        match="import_sites must be",
+    ):
+        _snapshot(
+            import_sites=SimpleNamespace(
+                topology=import_sites.topology,
+            ),
+        )
+
+
+def test_rejects_nested_mutable_conditional_evidence() -> None:
+    _, discovery = _reports()
+
+    bad_discovery = replace(
+        discovery,
+        candidates=[],
+    )
+
+    with pytest.raises(
+        TypeError,
+        match="mutable or unsupported evidence",
+    ):
+        _snapshot(
+            conditional_discovery=bad_discovery,
+        )
+
+
+def test_rejects_nested_mutable_import_evidence() -> None:
+    import_sites, _ = _reports()
+
+    bad_sites = replace(
+        import_sites,
+        components=list(import_sites.components),
+    )
+
+    with pytest.raises(
+        TypeError,
+        match="mutable or unsupported evidence",
+    ):
+        _snapshot(
+            import_sites=bad_sites,
+        )
+
+
+def test_rejects_component_topology_divergence() -> None:
+    import_sites, _ = _reports()
+
+    bad_sites = replace(
+        import_sites,
+        components=(),
+    )
+
+    with pytest.raises(
+        ValueError,
+        match="Import-site components and topology differ",
+    ):
+        _snapshot(
+            import_sites=bad_sites,
+        )
```
