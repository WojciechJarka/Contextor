TASK: CONTEXTOR_B0G4C0_PACKAGE_IMPORT_LAYOUT

HEAD_BEFORE
d22f7b454b51c3269839aa544ce6cfc1d1d92219

HEAD_AFTER
d22f7b454b51c3269839aa544ce6cfc1d1d92219

GIT_STATUS_BEFORE
clean

GIT_STATUS_AFTER
?? contextor/core/cycle_semantics/package_layout.py
?? tests/test_cycle_semantics_package_layout.py
walkthrough.md is this task report and is excluded from FILES_CHANGED.

LIVE_REVISION_BEFORE
418
activity_epoch=1beab26da2ff4932852caa7db6ff4242
canonical_state=fresh
graph=fresh
cycles=fresh, reported cycle diagnostics=16
resync_required=false
name_collisions=0 (fresh)

LIVE_REVISION_AFTER
420
activity_epoch=1beab26da2ff4932852caa7db6ff4242 (unchanged)
canonical_state=fresh
graph=fresh
cycles=fresh, reported cycle diagnostics=16
resync_required=false
name_collisions=0 (fresh)

LIVE_WATCHER_EVIDENCE
- Revision 419: desktop_watcher UPDATED contextor/core/cycle_semantics/package_layout.py; affected module contextor.core.cycle_semantics.package_layout.
- Revision 420: desktop_watcher UPDATED tests/test_cycle_semantics_package_layout.py; affected module tests.test_cycle_semantics_package_layout.
- Event continuity=continuous; no direct update_file or publish request was made.

SOURCE_PRECHECK
- HEAD and status were checked before editing; HEAD stayed unchanged. Initial status was clean.
- B0G4B7 evidence module contextor.core.cycle_semantics.evidence existed and was LIVE at revision 418 with workspace_sync=verified.
- Contextor resolved ImportOccurrence to the frozen dataclass in contextor/core/cycle_semantics/provenance.py (lines 28-40). The artifact has three confirmed direct static consumers in the canonical evidence: cycle_semantics.__init__, cycle_semantics.binding_order, and tests.test_cycle_semantics_execution_context.
- Existing package naming uses flat modules under contextor.core.cycle_semantics. No __init__.py was changed.
- Existing relative source-module resolver _resolve_import_module is owned by contextor.core.analysis.lineage_extraction_contracts (lines 143-149); its one direct consumer is contextor.core.analysis.lineage_extraction_visitors. It was not modified.
- ProjectGraph is owned by contextor.core.domain.graph (lines 10-54); Contextor reports 30 direct module consumers. The new package-layout module does not import or modify ProjectGraph.
- After watcher synchronization, Contextor reported the new package-layout module with one hard outbound edge to provenance and its test with hard dependencies on package_layout and provenance.

FILES_CHANGED
- contextor/core/cycle_semantics/package_layout.py (new)
- tests/test_cycle_semantics_package_layout.py (new)

IMPLEMENTATION_CONTRACT
- Both files match the supplied contents exactly; comparison against the attached specification returned true for each.
- The production module adds frozen evidence records for package layout and import-site plans. It maps indexed __init__ module IDs to regular-package candidates, classifies module files, namespace candidates, ambiguous layouts, and unknown modules, and returns deterministic parent load chains.
- The planner uses ImportOccurrence facts and preserves the occurrence ordinal, line, relative level, requested names, aliases, local bindings, and possible child-module candidates.
- It reports from-import member/submodule ambiguity as unresolved. Namespace candidates are explicitly repository-layout candidates, not runtime namespace-package proof. External imports remain unresolved.
- No analyzed source file is accessed or imported by this module. It does not mutate ProjectGraph, hard_edges, soft_edges, cycles, canonical state, or publication state. Valid from __future__ imports remain represented as import evidence.

TEST_COMMAND
Baseline:
& ..venvScriptspython.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

Post-change:
& ..venvScriptspython.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

TEST_RESULTS
- Repository Python: 3.10.9.
- Baseline: 121 passed in 3.75s.
- Post-change: 133 passed in 3.96s (12 new tests plus 121 existing).
- No warnings were emitted. No warning filter or warning-suppression option was used.
- Only the specified eight baseline files and nine post-change files were run.

PACKAGE_LAYOUT_EVIDENCE
- Tests verify deterministic ordering, __init__ normalization, regular-package parent chains, module-file and namespace-candidate classification, and explicit file/package conflicts.
- Contextor after watcher processing confirms the new module is workspace_sync=verified at revision 420. Its canonical hard dependency is provenance; no ProjectGraph dependency is present.

RELATIVE_IMPORT_EVIDENCE
- Targeted tests pass for from . import child, from .. import child, preservation of the requested package name, and relative traversal beyond top level returning RELATIVE_BEYOND_TOP_LEVEL with no entries.
- The planner uses the lexical occurrence level and indexed importer identity; it does not execute Python import resolution.

FROM_IMPORT_AMBIGUITY_EVIDENCE
- Tests pass for from pkg import child as c: pkg.child is retained only as a possible child module, the local alias is c, and resolution remains MEMBER_OR_SUBMODULE_UNRESOLVED.
- Imports from a plain module and star imports remain unresolved. External imports are reported as layout-unresolved.
- The future-import regression confirms from __future__ import annotations remains represented and unresolved as a repository-local layout target.

COLLISION_COUNT_BEFORE_AFTER
- Before: 0, availability=fresh, revision=418.
- After: 0, availability=fresh, revision=420.
- Both values are from Contextor canonical collision diagnostics after the corresponding source state was synchronized.

STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
- Before: 16 reported cycle diagnostics, availability=fresh, revision=418.
- After: 16 reported cycle diagnostics, availability=fresh, revision=420.
- The new package module has one hard edge to provenance. LIVE reports no change in the canonical reported cycle count. This count is the Contextor cycle diagnostic count, not a claim that every possible runtime import cycle was enumerated.

NO_SAFETY_CERTIFICATION
- PASS: no runtime safety certification is made. Tests exercise synthetic AST/import-occurrence inputs and the static layout planner. No analyzed module imports were executed and no cold-import experiment was run.

NO_WARNING_SUPPRESSION
- PASS: no warning suppression was added to source or tests, and pytest was not invoked with warning suppression.

NO_DIRECT_LIVE_PUBLICATION
- PASS: no update_file, publish, forced resync, or restart was requested. The desktop_watcher synchronized both new files and advanced LIVE from revision 418 to 420.

UNRESOLVED_LIMITATIONS
- NAMESPACE_CANDIDATE describes only the indexed repository layout; external namespace portions, runtime import hooks, and environment-dependent import behavior are outside this evidence.
- A possible child module does not establish whether a from-import binds a package attribute or loads a submodule.
- Runtime import targets and runtime safety remain unverified.
- The graph and collision conclusions are bounded to the fresh canonical Contextor state at revision 420.

EVIDENCE_CLASSES
- DIRECT_EVIDENCE: test outputs, Git HEAD/status, Contextor revisions/events/freshness/collision and cycle diagnostics, and workspace_sync=verified.
- CODE_PATH_PROVED: supplied implementation was byte-for-byte content-matched after newline normalization; Contextor resolved the new module's canonical edge to provenance.
- CONTRACT_PROVED: the 12 targeted tests passed; the public ProjectGraph and ImportOccurrence ownership checks came from Contextor source contracts.
- INFERENCE: unchanged reported cycle count and the new module's single edge support no observed cycle increase in the canonical graph.
- UNKNOWN: runtime package resolution and runtime safety for arbitrary analyzed imports.

FINAL_VERDICT
B0G4C0_PASS

FULL_DIFFS
diff --git a/contextor/core/cycle_semantics/package_layout.py b/contextor/core/cycle_semantics/package_layout.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/package_layout.py
@@ -0,0 +1,396 @@
+"""Conservative, source-independent inventory of Python import package layout.
+
+Never executes imports, mutates the canonical graph or certifies runtime targets.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Iterable
+from dataclasses import dataclass
+
+from contextor.core.cycle_semantics.provenance import ImportOccurrence
+
+
+@dataclass(frozen=True)
+class PackageLayoutNode:
+    name: str
+    kind: str
+    indexed_module_ids: tuple[str, ...]
+
+
+@dataclass(frozen=True)
+class PackageLayout:
+    nodes: tuple[PackageLayoutNode, ...]
+    authority: str = "REPOSITORY_LAYOUT_CANDIDATES_ONLY"
+
+
+@dataclass(frozen=True)
+class ImportNamePlan:
+    requested_name: str
+    local_binding: str
+    load_chain: tuple[PackageLayoutNode, ...]
+    member_name: str | None
+    possible_child_module: str | None
+    resolution: str
+
+
+@dataclass(frozen=True)
+class ImportSitePlan:
+    module_id: str
+    occurrence_ordinal: int
+    line: int
+    status: str
+    entries: tuple[ImportNamePlan, ...]
+    authority: str = "STATIC_LAYOUT_NOT_RUNTIME_PROOF"
+
+
+def _dotted(name: str) -> bool:
+    return bool(name) and all(
+        part.isidentifier()
+        for part in name.split(".")
+    )
+
+
+def build_package_layout(
+    indexed_modules: Iterable[str],
+) -> PackageLayout:
+    """Classify indexed modules, regular packages and namespace candidates.
+
+    A namespace is only a candidate: external portions and runtime import hooks
+    are not modeled. File/package conflicts are explicitly marked ambiguous.
+    """
+    if isinstance(indexed_modules, (str, bytes)):
+        raise TypeError(
+            "indexed_modules must be an iterable of module IDs"
+        )
+
+    try:
+        supplied = list(indexed_modules)
+    except TypeError:
+        raise TypeError(
+            "indexed_modules must be iterable"
+        ) from None
+
+    if any(
+        not isinstance(item, str) or not _dotted(item)
+        for item in supplied
+    ):
+        raise ValueError("invalid indexed module ID")
+
+    if len(supplied) != len(set(supplied)):
+        raise ValueError("duplicate indexed module ID")
+
+    ids = set(supplied)
+    origins: dict[str, set[str]] = {}
+
+    for index_id in ids:
+        if index_id.endswith(".__init__"):
+            name = index_id.removesuffix(".__init__")
+            origins.setdefault(name, set()).add(index_id)
+        else:
+            origins.setdefault(index_id, set()).add(index_id)
+
+    children: set[str] = set()
+
+    for name in origins:
+        parts = name.split(".")
+        for length in range(1, len(parts)):
+            children.add(".".join(parts[:length]))
+
+    nodes = []
+
+    for name in sorted(set(origins) | children):
+        choices = tuple(sorted(origins.get(name, ())))
+        is_init = f"{name}.__init__" in choices
+        is_file = name in choices
+        has_children = name in children
+
+        if (
+            (is_init and is_file)
+            or (is_file and has_children and not is_init)
+        ):
+            kind = "AMBIGUOUS_LAYOUT"
+        elif is_init:
+            kind = "REGULAR_PACKAGE"
+        elif is_file:
+            kind = "MODULE_FILE"
+        else:
+            kind = "NAMESPACE_CANDIDATE"
+
+        nodes.append(
+            PackageLayoutNode(name, kind, choices)
+        )
+
+    return PackageLayout(tuple(nodes))
+
+
+def _module_context(
+    module_id: str,
+    names: set[str],
+) -> tuple[str, ...] | None:
+    if module_id not in names:
+        return None
+
+    return tuple(module_id.split(".")[:-1])
+
+
+def _chain(
+    name: str,
+    lookup: dict[str, PackageLayoutNode],
+) -> tuple[PackageLayoutNode, ...]:
+    parts = name.split(".")
+    result = []
+
+    for length in range(1, len(parts) + 1):
+        path = ".".join(parts[:length])
+        node = lookup.get(path)
+
+        result.append(
+            node
+            if node is not None
+            else PackageLayoutNode(
+                path, "UNKNOWN_MODULE", ()
+            )
+        )
+
+    return tuple(result)
+
+
+def plan_package_import(
+    module_id: str,
+    occurrence: ImportOccurrence,
+    layout: PackageLayout,
+) -> ImportSitePlan:
+    """Plan lexical package-loading candidates without executing imports.
+
+    A possible submodule never proves a from-import member's runtime target.
+    """
+    if not isinstance(layout, PackageLayout):
+        raise TypeError("layout must be PackageLayout")
+
+    if not isinstance(occurrence, ImportOccurrence):
+        raise TypeError(
+            "occurrence must be ImportOccurrence"
+        )
+
+    if not isinstance(module_id, str) or not _dotted(module_id):
+        raise ValueError("invalid importer ID")
+
+    lookup = {
+        node.name: node
+        for node in layout.nodes
+    }
+
+    indexed = {
+        origin
+        for node in layout.nodes
+        for origin in node.indexed_module_ids
+    }
+
+    context = _module_context(module_id, indexed)
+
+    if context is None:
+        return ImportSitePlan(
+            module_id,
+            occurrence.ordinal,
+            occurrence.line,
+            "IMPORTER_NOT_INDEXED",
+            (),
+        )
+
+    if occurrence.form not in {"IMPORT", "IMPORT_FROM"}:
+        return ImportSitePlan(
+            module_id,
+            occurrence.ordinal,
+            occurrence.line,
+            "UNSUPPORTED_FORM",
+            (),
+        )
+
+    if occurrence.form == "IMPORT_FROM":
+        if (
+            not isinstance(occurrence.level, int)
+            or occurrence.level < 0
+        ):
+            return ImportSitePlan(
+                module_id,
+                occurrence.ordinal,
+                occurrence.line,
+                "INVALID_LEVEL",
+                (),
+            )
+
+        if occurrence.level:
+            climb = occurrence.level - 1
+
+            if not context or climb >= len(context):
+                return ImportSitePlan(
+                    module_id,
+                    occurrence.ordinal,
+                    occurrence.line,
+                    "RELATIVE_BEYOND_TOP_LEVEL",
+                    (),
+                )
+
+            base = list(
+                context[:len(context) - climb]
+            )
+
+            if occurrence.module is not None:
+                if not _dotted(occurrence.module):
+                    return ImportSitePlan(
+                        module_id,
+                        occurrence.ordinal,
+                        occurrence.line,
+                        "INVALID_MODULE_NAME",
+                        (),
+                    )
+                base.extend(
+                    occurrence.module.split(".")
+                )
+
+            requested_base = ".".join(base)
+
+        else:
+            requested_base = occurrence.module or ""
+
+            if not _dotted(requested_base):
+                return ImportSitePlan(
+                    module_id,
+                    occurrence.ordinal,
+                    occurrence.line,
+                    "INVALID_MODULE_NAME",
+                    (),
+                )
+
+    else:
+        if occurrence.level != 0:
+            return ImportSitePlan(
+                module_id,
+                occurrence.ordinal,
+                occurrence.line,
+                "INVALID_LEVEL",
+                (),
+            )
+
+        requested_base = ""
+
+    output = []
+
+    for requested, alias in occurrence.aliases:
+        if (
+            not isinstance(requested, str)
+            or (
+                requested != "*"
+                and not _dotted(requested)
+            )
+        ):
+            return ImportSitePlan(
+                module_id,
+                occurrence.ordinal,
+                occurrence.line,
+                "INVALID_MEMBER_NAME",
+                (),
+            )
+
+        if alias is not None and (
+            not isinstance(alias, str)
+            or not alias.isidentifier()
+        ):
+            return ImportSitePlan(
+                module_id,
+                occurrence.ordinal,
+                occurrence.line,
+                "INVALID_BINDING",
+                (),
+            )
+
+        if occurrence.form == "IMPORT":
+            if requested == "*":
+                return ImportSitePlan(
+                    module_id,
+                    occurrence.ordinal,
+                    occurrence.line,
+                    "INVALID_MEMBER_NAME",
+                    (),
+                )
+
+            chain = _chain(requested, lookup)
+            local = alias or requested.split(".")[0]
+
+            outcome = (
+                "LAYOUT_CHAIN_CANDIDATE"
+                if all(
+                    node.kind not in {
+                        "UNKNOWN_MODULE",
+                        "AMBIGUOUS_LAYOUT",
+                    }
+                    for node in chain
+                )
+                else "LAYOUT_UNRESOLVED"
+            )
+
+            output.append(
+                ImportNamePlan(
+                    requested,
+                    local,
+                    chain,
+                    None,
+                    None,
+                    outcome,
+                )
+            )
+
+        else:
+            chain = _chain(requested_base, lookup)
+            local = alias or requested
+
+            possible_child = (
+                f"{requested_base}.{requested}"
+                if (
+                    requested != "*"
+                    and chain[-1].kind in {
+                        "REGULAR_PACKAGE",
+                        "NAMESPACE_CANDIDATE",
+                        "AMBIGUOUS_LAYOUT",
+                    }
+                    and f"{requested_base}.{requested}" in lookup
+                )
+                else None
+            )
+
+            outcome = (
+                "STAR_EXPORTS_UNRESOLVED"
+                if requested == "*"
+                else "MEMBER_OR_SUBMODULE_UNRESOLVED"
+                if possible_child is not None
+                else "MEMBER_BINDING_UNRESOLVED"
+            )
+
+            if any(
+                node.kind in {
+                    "UNKNOWN_MODULE",
+                    "AMBIGUOUS_LAYOUT",
+                }
+                for node in chain
+            ):
+                outcome = "LAYOUT_UNRESOLVED"
+
+            output.append(
+                ImportNamePlan(
+                    requested_base,
+                    local,
+                    chain,
+                    requested,
+                    possible_child,
+                    outcome,
+                )
+            )
+
+    return ImportSitePlan(
+        module_id,
+        occurrence.ordinal,
+        occurrence.line,
+        "PLANNED",
+        tuple(output),
+    )

diff --git a/tests/test_cycle_semantics_package_layout.py b/tests/test_cycle_semantics_package_layout.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_package_layout.py
@@ -0,0 +1,218 @@
+import ast
+import json
+from dataclasses import asdict, FrozenInstanceError
+
+import pytest
+
+from contextor.core.cycle_semantics.package_layout import (
+    build_package_layout,
+    plan_package_import,
+)
+from contextor.core.cycle_semantics.provenance import (
+    extract_import_provenance,
+)
+
+
+def _plan(importer, module_ids, source):
+    tree = ast.parse(source)
+    facts = extract_import_provenance(
+        tree,
+        module_id=importer,
+        source_key=importer.replace(".", "/") + ".py",
+        source_path="C:/synthetic/source.py",
+        source_fingerprint="synthetic",
+    )
+    assert len(facts.occurrences) == 1
+    return plan_package_import(
+        importer,
+        facts.occurrences[0],
+        build_package_layout(module_ids),
+    )
+
+
+def test_regular_package_parent_load_chain():
+    p = _plan(
+        "pkg.user",
+        [
+            "pkg.__init__",
+            "pkg.sub.__init__",
+            "pkg.sub.item",
+            "pkg.user",
+        ],
+        "import pkg.sub.item",
+    )
+    assert tuple(
+        (x.name, x.kind, x.indexed_module_ids)
+        for x in p.entries[0].load_chain
+    ) == (
+        ("pkg", "REGULAR_PACKAGE", ("pkg.__init__",)),
+        ("pkg.sub", "REGULAR_PACKAGE", ("pkg.sub.__init__",)),
+        ("pkg.sub.item", "MODULE_FILE", ("pkg.sub.item",)),
+    )
+    assert p.entries[0].local_binding == "pkg"
+    assert p.entries[0].resolution == "LAYOUT_CHAIN_CANDIDATE"
+
+
+def test_dotted_import_alias_binds_alias():
+    p = _plan(
+        "pkg.user",
+        ["pkg.__init__", "pkg.sub", "pkg.user"],
+        "import pkg.sub as alias",
+    )
+    assert p.entries[0].local_binding == "alias"
+    assert p.entries[0].resolution == "LAYOUT_CHAIN_CANDIDATE"
+
+
+def test_from_package_member_remains_ambiguous():
+    p = _plan(
+        "pkg.user",
+        ["pkg.__init__", "pkg.child", "pkg.user"],
+        "from pkg import child as c",
+    )
+    item = p.entries[0]
+    assert item.possible_child_module == "pkg.child"
+    assert item.resolution == "MEMBER_OR_SUBMODULE_UNRESOLVED"
+    assert item.local_binding == "c"
+    assert tuple(x.name for x in item.load_chain) == ("pkg",)
+
+
+def test_relative_from_package_initializer():
+    p = _plan(
+        "pkg.__init__",
+        ["pkg.__init__", "pkg.child"],
+        "from . import child",
+    )
+    assert p.entries[0].requested_name == "pkg"
+    assert p.entries[0].possible_child_module == "pkg.child"
+
+
+def test_relative_import_parent_and_beyond_top():
+    ids = [
+        "pkg.__init__",
+        "pkg.deep.__init__",
+        "pkg.deep.mod",
+        "pkg.child",
+    ]
+    p = _plan(
+        "pkg.deep.mod",
+        ids,
+        "from .. import child",
+    )
+    assert p.entries[0].requested_name == "pkg"
+
+    p = _plan(
+        "pkg.deep.mod",
+        ids,
+        "from ... import child",
+    )
+    assert p.status == "RELATIVE_BEYOND_TOP_LEVEL"
+    assert not p.entries
+
+
+def test_namespace_candidates_are_not_runtime_proof():
+    layout = build_package_layout(
+        ["pkg.a", "pkg.sub.b"]
+    )
+    assert tuple(
+        (n.name, n.kind)
+        for n in layout.nodes
+    ) == (
+        ("pkg", "NAMESPACE_CANDIDATE"),
+        ("pkg.a", "MODULE_FILE"),
+        ("pkg.sub", "NAMESPACE_CANDIDATE"),
+        ("pkg.sub.b", "MODULE_FILE"),
+    )
+    assert layout.authority == (
+        "REPOSITORY_LAYOUT_CANDIDATES_ONLY"
+    )
+
+
+def test_conflicting_indexed_module_and_package_fail_closed():
+    layout = build_package_layout(
+        ["pkg", "pkg.__init__", "pkg.sub"]
+    )
+    assert layout.nodes[0].kind == "AMBIGUOUS_LAYOUT"
+
+    p = _plan(
+        "pkg.sub",
+        ["pkg", "pkg.__init__", "pkg.sub"],
+        "import pkg.sub",
+    )
+    assert p.entries[0].resolution == "LAYOUT_UNRESOLVED"
+
+
+def test_from_plain_module_not_guessed_as_child():
+    p = _plan(
+        "pkg.user",
+        ["pkg.__init__", "pkg.mod", "pkg.user"],
+        "from pkg.mod import method",
+    )
+    assert p.entries[0].possible_child_module is None
+    assert p.entries[0].resolution == "MEMBER_BINDING_UNRESOLVED"
+
+
+def test_external_import_not_claimed_resolved():
+    p = _plan(
+        "pkg.user",
+        ["pkg.user"],
+        "import external.nested",
+    )
+    assert p.entries[0].resolution == "LAYOUT_UNRESOLVED"
+    assert all(
+        node.kind == "UNKNOWN_MODULE"
+        for node in p.entries[0].load_chain
+    )
+
+
+def test_future_directive_keeps_runtime_import_evidence():
+    p = _plan(
+        "pkg.user",
+        ["pkg.user"],
+        "from __future__ import annotations",
+    )
+    assert p.status == "PLANNED"
+    assert p.entries[0].requested_name == "__future__"
+    assert p.entries[0].resolution == "LAYOUT_UNRESOLVED"
+
+
+def test_duplicate_invalid_and_unindexed_importer():
+    with pytest.raises(ValueError):
+        build_package_layout(["pkg.mod", "pkg.mod"])
+
+    with pytest.raises(TypeError):
+        build_package_layout("pkg.mod")
+
+    tree = ast.parse("import pkg")
+    occ = extract_import_provenance(
+        tree,
+        module_id="unknown",
+        source_key="unknown.py",
+        source_path="C:/unknown.py",
+        source_fingerprint="synthetic",
+    ).occurrences[0]
+
+    result = plan_package_import(
+        "unknown",
+        occ,
+        build_package_layout(["pkg.user"]),
+    )
+    assert result.status == "IMPORTER_NOT_INDEXED"
+    assert result.entries == ()
+
+
+def test_deterministic_immutable_and_json_serializable():
+    p = _plan(
+        "pkg.user",
+        ["pkg.__init__", "pkg.user"],
+        "import pkg",
+    )
+    assert p == _plan(
+        "pkg.user",
+        ["pkg.user", "pkg.__init__"],
+        "import pkg",
+    )
+    json.dumps(asdict(p))
+    assert p.authority == "STATIC_LAYOUT_NOT_RUNTIME_PROOF"
+
+    with pytest.raises(FrozenInstanceError):
+        p.status = "FAKE_SUCCESS"

