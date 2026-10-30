# CONTEXTOR P1D3-WARN-5M — index-bound conditional namespace source evidence

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `5711f482c0310460952b47046ea9c40b310e9356`; initial worktree clean. Both authorized target files were absent. Contextor MCP first resolved existing namespace path model and original worker binding at canonical revision 905, workspace_sync verified, graph/cycles fresh, cycle_semantics stale, structural DFS count 16 and active warnings 16.

## FILE_CREATION

- DIRECT_EVIDENCE: Created exactly the two architect-supplied new Python files. No existing production or test file was edited.

## BINDING_DOMAIN_CONTRACT

- CODE_PATH_PROVED: The new binder accepts caller-supplied ordered roots, indexed source paths, index fingerprints and `SourceSnapshot` objects. It first calls `resolve_namespace_path`; a non-CONDITIONAL result is returned as INDETERMINATE with its reason. It checks source domain equality against supplied inventory `.py` entries, without filesystem reads or analyzed-source imports.
- CODE_PATH_PROVED: Constants cap 256 sources, 2 MiB per source, 32 MiB aggregate and 16,384 inventory files. No global cache or shared evaluation state was introduced.

## SOURCE_BYTE_AND_INDEX_PROOF

- CODE_PATH_PROVED: For supplied indexed sources, the binder checks exact module-derived relative paths, root membership, one-to-one source identities, snapshot shape and SHA-256 of raw bytes against both snapshot and index fingerprints. This binds caller-supplied bytes/index claims, not physical path provenance or LIVE authority.

## CONDITIONAL_RESOLUTION_BINDING

- CODE_PATH_PROVED: Selected regular initializer and module steps are matched to indexed source bindings and ordered into `selected_sources`; namespace steps have no source bytes. The digest canonically encodes caller-supplied inventory order, bindings and resolution steps. Authority explicitly says `CALLER_SUPPLIED_INDEXED_SOURCE_BYTES_NOT_RUNTIME_OR_LIVE_CERTIFIED`.

## NEGATIVE_FAIL_CLOSED_CASES

- DIRECT_EVIDENCE: M03–M13 passed in the focused run, including finder assumption, byte/hash/path/domain/duplicate/loader/budget negatives and deterministic digest. M14 failed on the exact reason, described below.
- CONTRACT_CONFLICT: M14 adds `pkg/ns.py` to a supplied inventory containing `pkg/ns/child.py`, then expects `INVENTORY_SOURCE_BINDING_MISMATCH`. The exact implementation calls path resolution first. That resolver selects `pkg/ns.py` and returns `INDETERMINATE / MODULE_IS_NOT_A_PACKAGE` before inventory binding validation. The actual status is INDETERMINATE as expected, but reason differs. The architect must decide the contract; no assertion or production gate was changed by the agent.

## TEST_RESULTS

- DIRECT_EVIDENCE: `python -m py_compile` on both new files passed.
- DIRECT_EVIDENCE: `python -m pytest -q -rs tests/test_cycle_semantics_namespace_source_binding.py tests/test_cycle_semantics_namespace_path_model.py tests/test_cycle_semantics_namespace_pep420_contract.py` → 33 passed, 1 failed in 3.41s. Failure: `test_m14_unindexed_shadowing_source_blocks_binding`, expected `INVENTORY_SOURCE_BINDING_MISMATCH`, actual `MODULE_IS_NOT_A_PACKAGE` at test line 288.
- DIRECT_EVIDENCE: `git diff --check` and `git diff --no-index --check -- /dev/null` for both new files found no whitespace errors. Git emitted only LF-to-CRLF advisories.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Both new files returned `not_found` from MCP active module registry at the post-change read; their canonical workspace_sync is UNKNOWN. MCP `get_live_events` returned revision 905, activity_epoch `d08a5a93184d473f8bc124596f4a44c9`, fresh warning view with 16 structural and 16 active warnings. Earlier module context showed graph/cycles fresh and cycle_semantics stale. No manual update_file, FULL or restart was performed.

## FILES_CHANGED

- `contextor/core/cycle_semantics/namespace_source_binding.py` (new, untracked)
- `tests/test_cycle_semantics_namespace_source_binding.py` (new, untracked)

`walkthrough.md` was overwritten as the report.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/namespace_source_binding.py b/contextor/core/cycle_semantics/namespace_source_binding.py
new file mode 100644
index 0000000..1dc0750
--- /dev/null
+++ b/contextor/core/cycle_semantics/namespace_source_binding.py
@@ -0,0 +1,302 @@
+"""Bind supplied namespace inventories to indexed source byte snapshots.
+
+This is conditional caller-supplied evidence only. It does not
+authenticate runtime import resolution, filesystem completeness,
+canonical LIVE generations, or cycle-warning suppression.
+"""
+
+from __future__ import annotations
+
+import hashlib
+import json
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import SourceSnapshot
+
+from .namespace_path_model import (
+    NamespacePathResult,
+    SearchPortion,
+    resolve_namespace_path,
+)
+
+
+_MAX_SOURCES = 256
+_MAX_SOURCE_BYTES = 2 * 1024 * 1024
+_MAX_TOTAL_BYTES = 32 * 1024 * 1024
+_MAX_INVENTORY_FILES = 16384
+
+_AUTHORITY = (
+    "CALLER_SUPPLIED_INDEXED_SOURCE_BYTES_"
+    "NOT_RUNTIME_OR_LIVE_CERTIFIED"
+)
+
+_VERSION = "namespace-conditional-source-binding/1"
+
+
+@dataclass(frozen=True)
+class IndexedSourcePath:
+    module_id: str
+    root_id: str
+    relative_path: str
+
+
+@dataclass(frozen=True)
+class BoundNamespaceResolution:
+    status: str
+    reason: str | None
+    requested_name: str
+    resolution: NamespacePathResult | None
+    selected_sources: tuple[tuple[str, str, str], ...]
+    evidence_sha256: str | None
+    authority: str = _AUTHORITY
+    version: str = _VERSION
+
+
+def bind_indexed_namespace_resolution(
+    roots: tuple[SearchPortion, ...],
+    bindings: tuple[IndexedSourcePath, ...],
+    indexed_fingerprints: Mapping[str, str],
+    source_snapshots: Mapping[str, SourceSnapshot],
+    requested_name: str,
+    *,
+    standard_finder_assumed: bool = False,
+) -> BoundNamespaceResolution:
+    """Verify supplied source identities and conditional path selection.
+
+    No file reads, imports of analyzed modules, LIVE IPC or publication.
+    An inventory hash describes supplied input; it is not a trusted
+    signature or proof of actual interpreter search paths.
+    """
+    resolution = resolve_namespace_path(
+        roots,
+        requested_name,
+        standard_finder_assumed=standard_finder_assumed,
+    )
+
+    def reject(reason: str) -> BoundNamespaceResolution:
+        return BoundNamespaceResolution(
+            "INDETERMINATE",
+            reason,
+            requested_name,
+            resolution,
+            (),
+            None,
+        )
+
+    if resolution.status != "CONDITIONAL":
+        return reject(
+            resolution.reason or "PATH_RESOLUTION_INDETERMINATE"
+        )
+
+    if (
+        type(bindings) is not tuple
+        or not bindings
+        or len(bindings) > _MAX_SOURCES
+        or not isinstance(indexed_fingerprints, Mapping)
+        or not isinstance(source_snapshots, Mapping)
+    ):
+        return reject("SOURCE_BINDING_INPUT_INVALID")
+
+    if (
+        sum(len(root.files) for root in roots)
+        > _MAX_INVENTORY_FILES
+    ):
+        return reject("INVENTORY_FILE_LIMIT")
+
+    root_by_id = {}
+
+    for root in roots:
+        if (
+            not root.root_id.isidentifier()
+            or root.root_id in root_by_id
+        ):
+            return reject("ROOT_ID_INVALID")
+
+        root_by_id[root.root_id] = root
+
+    module_to_binding = {}
+    path_to_binding = {}
+
+    for binding in bindings:
+        if type(binding) is not IndexedSourcePath:
+            return reject("SOURCE_BINDING_SHAPE_INVALID")
+
+        module_id = binding.module_id
+
+        if (
+            type(module_id) is not str
+            or not module_id
+            or any(
+                not segment.isidentifier()
+                for segment in module_id.split(".")
+            )
+            or type(binding.root_id) is not str
+            or binding.root_id not in root_by_id
+            or type(binding.relative_path) is not str
+        ):
+            return reject("SOURCE_BINDING_IDENTITY_INVALID")
+
+        expected_path = module_id.replace(".", "/") + ".py"
+
+        if binding.relative_path != expected_path:
+            return reject("SOURCE_MODULE_PATH_MISMATCH")
+
+        if binding.relative_path not in (
+            root_by_id[binding.root_id].files
+        ):
+            return reject("SOURCE_PATH_NOT_IN_INVENTORY")
+
+        source_key = (
+            binding.root_id + ":" + binding.relative_path
+        )
+
+        if (
+            module_id in module_to_binding
+            or source_key in path_to_binding
+        ):
+            return reject("DUPLICATE_SOURCE_BINDING")
+
+        module_to_binding[module_id] = binding
+        path_to_binding[source_key] = binding
+
+    required_ids = set(module_to_binding)
+
+    if (
+        set(indexed_fingerprints) != required_ids
+        or set(source_snapshots) != required_ids
+    ):
+        return reject("SOURCE_INDEX_DOMAIN_MISMATCH")
+
+    # Every supplied .py entry must be represented by a source
+    # identity. This proves only completeness relative to the
+    # supplied inventory, never completeness of actual sys.path.
+    inventory_python_files = {
+        root.root_id + ":" + filename
+        for root in roots
+        for filename in root.files
+        if filename.endswith(".py")
+    }
+
+    if inventory_python_files != set(path_to_binding):
+        return reject("INVENTORY_SOURCE_BINDING_MISMATCH")
+
+    signatures = {}
+    retained_bytes = 0
+
+    for module_id in sorted(required_ids):
+        snapshot = source_snapshots[module_id]
+        claimed_sha = indexed_fingerprints[module_id]
+
+        if (
+            type(snapshot) is not SourceSnapshot
+            or type(snapshot.raw) is not bytes
+            or type(snapshot.source_fingerprint) is not str
+            or type(claimed_sha) is not str
+            or len(claimed_sha) != 64
+            or any(
+                character not in "0123456789abcdef"
+                for character in claimed_sha
+            )
+        ):
+            return reject("SOURCE_SNAPSHOT_SHAPE_INVALID")
+
+        if len(snapshot.raw) > _MAX_SOURCE_BYTES:
+            return reject("SOURCE_BYTE_LIMIT")
+
+        retained_bytes += len(snapshot.raw)
+
+        if retained_bytes > _MAX_TOTAL_BYTES:
+            return reject("SOURCE_TOTAL_BYTE_LIMIT")
+
+        actual_sha = hashlib.sha256(snapshot.raw).hexdigest()
+
+        if (
+            actual_sha != claimed_sha
+            or snapshot.source_fingerprint != claimed_sha
+        ):
+            return reject("SOURCE_FINGERPRINT_MISMATCH")
+
+        signatures[module_id] = actual_sha
+
+    selected = []
+
+    for step in resolution.steps:
+        if step.kind == "NAMESPACE_PACKAGE":
+            continue
+
+        if (
+            step.kind not in {"REGULAR_PACKAGE", "MODULE_FILE"}
+            or type(step.source) is not str
+        ):
+            return reject("UNSUPPORTED_SELECTED_SOURCE_KIND")
+
+        binding = path_to_binding.get(step.source)
+
+        if binding is None:
+            return reject("SELECTED_SOURCE_NOT_INDEXED")
+
+        expected_module = (
+            step.name + ".__init__"
+            if step.kind == "REGULAR_PACKAGE"
+            else step.name
+        )
+
+        if binding.module_id != expected_module:
+            return reject("SELECTED_MODULE_IDENTITY_MISMATCH")
+
+        selected.append((
+            binding.module_id,
+            step.source,
+            signatures[binding.module_id],
+        ))
+
+    # Canonical serialization of caller-supplied information only.
+    # This digest does not authenticate where that information
+    # originated or whether files outside the inventory exist.
+    digest_input = (
+        _VERSION,
+        requested_name,
+        tuple(
+            (
+                root.root_id,
+                tuple(sorted(root.files)),
+            )
+            for root in roots
+        ),
+        tuple(
+            sorted(
+                (
+                    binding.module_id,
+                    binding.root_id,
+                    binding.relative_path,
+                    signatures[binding.module_id],
+                )
+                for binding in bindings
+            )
+        ),
+        tuple(
+            (
+                step.name,
+                step.kind,
+                step.source,
+                step.portions,
+            )
+            for step in resolution.steps
+        ),
+    )
+
+    encoded = json.dumps(
+        digest_input,
+        ensure_ascii=True,
+        separators=(",", ":"),
+    ).encode("utf-8")
+
+    return BoundNamespaceResolution(
+        "SOURCE_BOUND_CONDITIONAL",
+        None,
+        requested_name,
+        resolution,
+        tuple(selected),
+        hashlib.sha256(encoded).hexdigest(),
+    )
diff --git a/tests/test_cycle_semantics_namespace_source_binding.py b/tests/test_cycle_semantics_namespace_source_binding.py
new file mode 100644
index 0000000..99a6b1f
--- /dev/null
+++ b/tests/test_cycle_semantics_namespace_source_binding.py
@@ -0,0 +1,288 @@
+"""Source-byte and index-identity binding for conditional namespace paths."""
+
+from __future__ import annotations
+
+import hashlib
+from dataclasses import asdict
+
+from contextor.core.source import SourceSnapshot
+from contextor.core.cycle_semantics.namespace_path_model import (
+    SearchPortion,
+)
+from contextor.core.cycle_semantics.namespace_source_binding import (
+    IndexedSourcePath,
+    bind_indexed_namespace_resolution,
+)
+
+
+def _snapshot(text):
+    raw = text.encode("utf-8")
+    return SourceSnapshot(
+        raw,
+        hashlib.sha256(raw).hexdigest(),
+    )
+
+
+def _base():
+    roots = (
+        SearchPortion(
+            "root",
+            frozenset({
+                "pkg/__init__.py",
+                "pkg/ns/child.py",
+            }),
+        ),
+    )
+    bindings = (
+        IndexedSourcePath(
+            "pkg.__init__", "root", "pkg/__init__.py"
+        ),
+        IndexedSourcePath(
+            "pkg.ns.child", "root", "pkg/ns/child.py"
+        ),
+    )
+    snapshots = {
+        "pkg.__init__": _snapshot("value = 1\n"),
+        "pkg.ns.child": _snapshot("value = 7\n"),
+    }
+    fingerprints = {
+        name: snapshot.source_fingerprint
+        for name, snapshot in snapshots.items()
+    }
+    return roots, bindings, fingerprints, snapshots
+
+
+def _bind(
+    roots,
+    bindings,
+    fingerprints,
+    snapshots,
+    requested="pkg.ns.child",
+    *,
+    finder=True,
+):
+    return bind_indexed_namespace_resolution(
+        roots,
+        bindings,
+        fingerprints,
+        snapshots,
+        requested,
+        standard_finder_assumed=finder,
+    )
+
+
+def test_m01_namespace_source_bytes_are_bound():
+    args = _base()
+    result = _bind(*args)
+
+    assert result.status == "SOURCE_BOUND_CONDITIONAL"
+    assert result.reason is None
+    assert len(result.selected_sources) == 2
+    assert result.selected_sources[0][0] == "pkg.__init__"
+    assert result.selected_sources[1][0] == "pkg.ns.child"
+    assert result.resolution.steps[1].kind == "NAMESPACE_PACKAGE"
+    assert len(result.evidence_sha256) == 64
+
+
+def test_m02_two_portions_bind_distinct_children():
+    roots = (
+        SearchPortion("first", frozenset({"nsp/left.py"})),
+        SearchPortion("second", frozenset({"nsp/right.py"})),
+    )
+    bindings = (
+        IndexedSourcePath("nsp.left", "first", "nsp/left.py"),
+        IndexedSourcePath("nsp.right", "second", "nsp/right.py"),
+    )
+    snapshots = {
+        "nsp.left": _snapshot("value = 1"),
+        "nsp.right": _snapshot("value = 2"),
+    }
+    hashes = {
+        key: value.source_fingerprint
+        for key, value in snapshots.items()
+    }
+
+    result = _bind(
+        roots, bindings, hashes, snapshots, "nsp.right"
+    )
+
+    assert result.status == "SOURCE_BOUND_CONDITIONAL"
+    assert result.selected_sources == ((
+        "nsp.right",
+        "second:nsp/right.py",
+        hashes["nsp.right"],
+    ),)
+
+
+def test_m03_finder_assumption_is_not_automatic():
+    result = _bind(*_base(), finder=False)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "IMPORT_FINDER_ENVIRONMENT_NOT_PROVED"
+    assert result.evidence_sha256 is None
+
+
+def test_m04_modified_raw_bytes_are_rejected():
+    roots, rows, hashes, snapshots = _base()
+    snapshots["pkg.ns.child"] = _snapshot("value = 99")
+
+    result = _bind(roots, rows, hashes, snapshots)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
+
+
+def test_m05_forged_fingerprint_is_rejected():
+    roots, rows, hashes, snapshots = _base()
+    hashes["pkg.ns.child"] = "0" * 64
+
+    result = _bind(roots, rows, hashes, snapshots)
+
+    assert result.reason == "SOURCE_FINGERPRINT_MISMATCH"
+
+
+def test_m06_incorrect_module_path_is_rejected():
+    roots, rows, hashes, snapshots = _base()
+
+    bad_rows = (
+        rows[0],
+        IndexedSourcePath(
+            "pkg.ns.child",
+            "root",
+            "pkg/child.py",
+        ),
+    )
+
+    result = _bind(
+        roots, bad_rows, hashes, snapshots
+    )
+
+    assert result.reason == "SOURCE_MODULE_PATH_MISMATCH"
+
+
+def test_m07_unbound_python_inventory_entry_is_rejected():
+    roots, rows, hashes, snapshots = _base()
+    roots = (
+        SearchPortion(
+            "root",
+            roots[0].files | frozenset({"pkg/extra.py"}),
+        ),
+    )
+
+    result = _bind(roots, rows, hashes, snapshots)
+
+    assert result.reason == "INVENTORY_SOURCE_BINDING_MISMATCH"
+
+
+def test_m08_missing_capture_is_rejected():
+    roots, rows, hashes, snapshots = _base()
+    del snapshots["pkg.ns.child"]
+
+    result = _bind(roots, rows, hashes, snapshots)
+
+    assert result.reason == "SOURCE_INDEX_DOMAIN_MISMATCH"
+
+
+def test_m09_duplicate_module_identity_is_rejected():
+    roots, rows, hashes, snapshots = _base()
+
+    result = _bind(
+        roots,
+        rows + (rows[0],),
+        hashes,
+        snapshots,
+    )
+
+    assert result.reason == "DUPLICATE_SOURCE_BINDING"
+
+
+def test_m10_alternative_loader_remains_indeterminate():
+    roots, rows, hashes, snapshots = _base()
+    roots = (
+        SearchPortion(
+            "root",
+            roots[0].files | frozenset({
+                "pkg/ns/child.cp310-win_amd64.pyd",
+            }),
+        ),
+    )
+
+    result = _bind(roots, rows, hashes, snapshots)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "ALTERNATIVE_LOADER_CANDIDATE"
+
+
+def test_m11_inventory_order_changes_digest():
+    roots, rows, hashes, snapshots = _base()
+
+    extra_root = SearchPortion(
+        "other",
+        frozenset({"notes.txt"}),
+    )
+
+    first = _bind(
+        roots + (extra_root,),
+        rows,
+        hashes,
+        snapshots,
+    )
+    second = _bind(
+        (extra_root,) + roots,
+        rows,
+        hashes,
+        snapshots,
+    )
+
+    assert first.status == "SOURCE_BOUND_CONDITIONAL"
+    assert second.status == "SOURCE_BOUND_CONDITIONAL"
+    assert first.evidence_sha256 != second.evidence_sha256
+
+
+def test_m12_source_byte_budget_fails_closed():
+    roots, rows, hashes, snapshots = _base()
+
+    oversized = b"x" * (2 * 1024 * 1024 + 1)
+    digest = hashlib.sha256(oversized).hexdigest()
+
+    snapshots["pkg.ns.child"] = SourceSnapshot(
+        oversized,
+        digest,
+    )
+    hashes["pkg.ns.child"] = digest
+
+    result = _bind(roots, rows, hashes, snapshots)
+
+    assert result.reason == "SOURCE_BYTE_LIMIT"
+    assert result.evidence_sha256 is None
+
+
+def test_m13_deterministic_without_live_authority():
+    args = _base()
+
+    first = _bind(*args)
+    second = _bind(*args)
+
+    assert first == second
+    assert asdict(first) == asdict(second)
+    assert first.authority == (
+        "CALLER_SUPPLIED_INDEXED_SOURCE_BYTES_"
+        "NOT_RUNTIME_OR_LIVE_CERTIFIED"
+    )
+    assert first.status == "SOURCE_BOUND_CONDITIONAL"
+
+
+def test_m14_unindexed_shadowing_source_blocks_binding():
+    roots, rows, hashes, snapshots = _base()
+
+    roots = (
+        SearchPortion(
+            "root",
+            roots[0].files | frozenset({"pkg/ns.py"}),
+        ),
+    )
+
+    result = _bind(roots, rows, hashes, snapshots)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "INVENTORY_SOURCE_BINDING_MISMATCH"
```

## UNPROVED_RUNTIME_ASSUMPTIONS

- Actual `sys.path`, finder behavior, absence of external namespace portions, physical filesystem completeness, canonical LIVE source identity and runtime import safety remain unproved. No MODEL_PASS or warning suppression was introduced.

## FINAL_VERDICT

CONTRACT_CONFLICT. The exact two files are present and compile, but the required focused set has one M14 reason mismatch. STOP without independent repair or test expectation change; architect decision required.
