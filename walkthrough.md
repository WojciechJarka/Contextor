# CONTEXTOR_B0G4C7_CANONICAL_EDGE_IMPORT_SITE_ATTRIBUTION

## SOURCE_PRECHECK
DIRECT_EVIDENCE: HEAD 0be273578c980e5b45eaba2e5fd75dc913bc2f54; initial Git status empty; both requested files absent. Repository Python 3.10.9. Existing owners provenance, scc and ParsedSourceInput had canonical fresh, workspace_sync=verified at revision 432. Their fetched signatures and data fields match the supplied implementation. The extractor has 8 confirmed static consumers; SCC analyzer has 2. No material source drift.
GIT_STATUS_AFTER:
?? contextor/core/cycle_semantics/edge_sites.py
?? tests/test_cycle_semantics_edge_sites.py

## HEAD_BEFORE
0be273578c980e5b45eaba2e5fd75dc913bc2f54

## HEAD_AFTER
0be273578c980e5b45eaba2e5fd75dc913bc2f54

## LIVE_REVISION_BEFORE
432; activity_epoch=1beab26da2ff4932852caa7db6ff4242; resync_required=false. Fresh syntax, collisions and cycles. Collision count 0; structural cycle path count 16.

## LIVE_REVISION_AFTER
434; same activity_epoch; resync_required=false; event continuity continuous. DIRECT_EVIDENCE: desktop_watcher UPDATED edge_sites.py at revision 433 and test_cycle_semantics_edge_sites.py at revision 434. Both modules canonical_state=fresh, workspace_sync=verified; graph, topology, cycles and collisions fresh.

## FILES_CHANGED
- contextor/core/cycle_semantics/edge_sites.py (new)
- tests/test_cycle_semantics_edge_sites.py (new)
walkthrough.md is the requested report artifact.

## IMPLEMENTATION_CONTRACT
CONTRACT_PROVED: Both new files byte-for-byte match the auditor-supplied CONTENT blocks after newline normalization. No existing production/test module or __init__.py was edited. The function accepts a complete hard-edge mapping and caller-supplied ParsedSourceInput mapping, computes cyclic topology, and attributes lexical candidates to each internal edge without reading analyzed files or executing analyzed imports.

## TEST_COMMAND
Baseline:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

Post-change:
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_cycle_semantics_edge_sites.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_layout.py tests/test_cycle_semantics_evidence.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_scc.py tests/test_cycle_semantics_initialization_model.py tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py

## TEST_RESULTS
DIRECT_EVIDENCE: baseline 190 passed in 10.25s; post-change 204 passed in 11.93s. Full pytest suite was not run.

## CANONICAL_EDGE_PRESERVATION
CODE_PATH_PROVED: topology is computed from the input hard_edges. Every topology.cyclic_components internal edge receives exactly one HardEdgeSiteEvidence, including unmatched/invalid-source edges. Input graph is not modified. Tests cover two-edge cycles, missing/unmatched edges, determinism and graph immutability. No repository graph snapshot or FULL analysis was requested.

## IMPORT_OCCURRENCE_ATTRIBUTION
CODE_PATH_PROVED: source AST provenance retains ordinal, line, column, import form, requested name, member, raw scopes and controls. Candidate sites are deterministically ordered and multiple occurrences remain distinct. LEXICAL_CANDIDATES is lexical evidence only.

## PACKAGE_INITIALIZER_CANDIDATES
CODE_PATH_PROVED: _canonical retains file and package-initializer identities when indexed; _parents emits PARENT_INITIALIZER candidates; OPTIONAL_FROM_CHILD remains a candidate. Tests cover both kinds. No runtime re-execution or submodule resolution is asserted.

## RELATIVE_IMPORT_EVIDENCE
CODE_PATH_PROVED: _absolute_from uses importer package context and level, rejects invalid names/climbs, then matches indexed targets. Tests cover package-relative and second-level relative forms. Candidate matching is conservative, not runtime resolution.

## FUNCTION_AND_GUARD_SCOPE_EVIDENCE
CODE_PATH_PROVED: _activation distinguishes MODULE_TOP_LEVEL, GUARDED_TOP_LEVEL, FUNCTION_SCOPED and OTHER_SCOPED while retaining raw frames. Tests cover module, function and guarded occurrences. MODULE_TOP_LEVEL does not certify unconditional execution.

## MISSING_SOURCE_FAIL_CLOSED
CODE_PATH_PROVED: invalid/missing ParsedSourceInput, invalid AST/fingerprint and AST budget excess mark the source invalid; its internal edges remain with SOURCE_MISSING_OR_INVALID. Valid source without a match remains NO_MATCHING_LEXICAL_SITE. Tests cover missing source, invalid fingerprint and unmatched lexical site. Oversized AST behavior follows the exact code path; no dedicated oversized fixture was supplied.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0, both fresh in canonical LIVE diagnostics at revisions 432 and 434.

## STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER
16 -> 16 reported paths, both fresh in canonical LIVE diagnostics at revisions 432 and 434.

## NO_SAFETY_CERTIFICATION
No runtime safety verdict or cold-import certification was made. The report evidence_scope explicitly excludes runtime certification.

## NO_WARNING_SUPPRESSION
No warning suppression, import detector change, graph policy change or diagnostic suppression was added.

## NO_DIRECT_LIVE_PUBLICATION
No update_file, publish, FULL analysis, restart or direct canonical mutation was requested. Desktop watcher produced the two observed canonical updates.

## UNRESOLVED_LIMITATIONS
UNKNOWN: The 204 focused tests do not exhaust every Python import runtime state. The provided implementation does not prove activation or actual from-import child resolution. Oversized-source behavior was reviewed from the exact code path but was not separately tested by the supplied test file.

## FINAL_VERDICT
B0G4C7_PASS

## FULL_DIFFS

diff --git a/contextor/core/cycle_semantics/edge_sites.py b/contextor/core/cycle_semantics/edge_sites.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/edge_sites.py
@@ -0,0 +1,383 @@
+"""Source-snapshot lexical candidates for canonical cyclic hard edges.
+
+Matches are provenance evidence, never proof of import activation or runtime
+resolution. Unmatched edges remain explicit, rather than being discarded.
+"""
+
+from __future__ import annotations
+
+import ast
+from collections.abc import Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import ParsedSourceInput
+
+from .provenance import ControlFrame, ScopeFrame, extract_import_provenance
+from .scc import ImportCycleTopology, analyze_import_cycle_topology
+
+MAX_SOURCE_AST_NODES = 100_000
+
+
+@dataclass(frozen=True)
+class LexicalEdgeSite:
+    ordinal: int
+    line: int
+    column: int
+    form: str
+    match_kind: str
+    requested_name: str
+    matched_member: str | None
+    scopes: tuple[ScopeFrame, ...]
+    controls: tuple[ControlFrame, ...]
+    activation_scope: str
+
+
+@dataclass(frozen=True)
+class HardEdgeSiteEvidence:
+    source: str
+    target: str
+    status: str
+    sites: tuple[LexicalEdgeSite, ...]
+
+
+@dataclass(frozen=True)
+class SCCImportSiteEvidence:
+    members: tuple[str, ...]
+    internal_edges: tuple[HardEdgeSiteEvidence, ...]
+    matched_edge_count: int
+    unresolved_edge_count: int
+    evidence_scope: str = "LEXICAL_IMPORT_CANDIDATES_NOT_EXECUTION"
+
+
+@dataclass(frozen=True)
+class CyclicImportSiteReport:
+    topology: ImportCycleTopology
+    components: tuple[SCCImportSiteEvidence, ...]
+    evidence_scope: str = "SNAPSHOT_LEXICAL_EVIDENCE_NOT_RUNTIME_CERTIFICATION"
+
+
+def _canonical(name: str, indexed: set[str]) -> tuple[str, ...]:
+    """Keep indexed file/package collisions as distinct candidates."""
+    return tuple(
+        candidate
+        for candidate in (name, name + ".__init__")
+        if candidate in indexed
+    )
+
+
+def _parents(name: str, indexed: set[str]) -> tuple[str, ...]:
+    pieces = name.split(".")
+    return tuple(
+        prefix + ".__init__"
+        for length in range(1, len(pieces))
+        if (
+            prefix := ".".join(pieces[:length])
+        ) + ".__init__" in indexed
+    )
+
+
+def _absolute_from(
+    importer: str,
+    module: str | None,
+    level: int,
+) -> str | None:
+    if level == 0:
+        return (
+            module
+            if module
+            and all(p.isidentifier() for p in module.split("."))
+            else None
+        )
+
+    if level < 0:
+        return None
+
+    context = (
+        importer.rsplit(".", 1)[0]
+        if not importer.endswith(".__init__")
+        else importer.removesuffix(".__init__")
+    )
+
+    parts = context.split(".") if context else []
+    climb = level - 1
+
+    if not parts or climb >= len(parts):
+        return None
+
+    parent = parts[:len(parts) - climb]
+
+    if module:
+        if not all(p.isidentifier() for p in module.split(".")):
+            return None
+        parent.extend(module.split("."))
+
+    return ".".join(parent)
+
+
+def _candidate_targets(
+    occurrence,
+    importer: str,
+    indexed: set[str],
+) -> tuple[tuple[str, str, str, str | None], ...]:
+    """Return canonical target, match kind, request and member."""
+    found: set[tuple[str, str, str, str | None]] = set()
+
+    if occurrence.form == "IMPORT":
+        for requested, _alias in occurrence.aliases:
+            if (
+                not requested
+                or not all(
+                    p.isidentifier()
+                    for p in requested.split(".")
+                )
+            ):
+                continue
+
+            for candidate in _canonical(requested, indexed):
+                found.add((
+                    candidate,
+                    "DIRECT_MODULE",
+                    requested,
+                    None,
+                ))
+
+            for candidate in _parents(requested, indexed):
+                found.add((
+                    candidate,
+                    "PARENT_INITIALIZER",
+                    requested,
+                    None,
+                ))
+
+    elif occurrence.form == "IMPORT_FROM":
+        base = _absolute_from(
+            importer,
+            occurrence.module,
+            occurrence.level,
+        )
+
+        if base is None:
+            return ()
+
+        for candidate in _canonical(base, indexed):
+            found.add((
+                candidate,
+                "FROM_BASE",
+                base,
+                None,
+            ))
+
+        for candidate in _parents(base, indexed):
+            found.add((
+                candidate,
+                "PARENT_INITIALIZER",
+                base,
+                None,
+            ))
+
+        for member, _alias in occurrence.aliases:
+            if member == "*" or not member.isidentifier():
+                continue
+
+            child = base + "." + member
+
+            for candidate in _canonical(child, indexed):
+                found.add((
+                    candidate,
+                    "OPTIONAL_FROM_CHILD",
+                    base,
+                    member,
+                ))
+
+    return tuple(sorted(found))
+
+
+def _activation(
+    scopes: tuple[ScopeFrame, ...],
+    controls: tuple[ControlFrame, ...],
+) -> str:
+    if any(
+        scope.kind in {"FUNCTION", "ASYNC_FUNCTION"}
+        for scope in scopes
+    ):
+        return "FUNCTION_SCOPED"
+
+    if scopes:
+        return "OTHER_SCOPED"
+
+    if controls:
+        return "GUARDED_TOP_LEVEL"
+
+    return "MODULE_TOP_LEVEL"
+
+
+def analyze_cyclic_import_sites(
+    hard_edges: Mapping[
+        str,
+        set[str] | frozenset[str] | list[str] | tuple[str, ...],
+    ],
+    parsed_sources: Mapping[str, ParsedSourceInput],
+) -> CyclicImportSiteReport:
+    """Join canonical internal SCC edges to lexical AST candidates.
+
+    All graph edges survive even when source or lexical evidence is missing.
+    The model performs no runtime import execution or source reads.
+    """
+    if not isinstance(hard_edges, Mapping):
+        raise TypeError("hard_edges must be a mapping")
+
+    topology = analyze_import_cycle_topology(hard_edges)
+
+    if not isinstance(parsed_sources, Mapping):
+        raise TypeError("parsed_sources must be a mapping")
+
+    indexed = set(hard_edges)
+
+    for targets in hard_edges.values():
+        indexed.update(targets)
+
+    members = {
+        name
+        for component in topology.cyclic_components
+        for name in component.members
+    }
+
+    available: dict[
+        str,
+        dict[str, tuple[LexicalEdgeSite, ...]],
+    ] = {}
+
+    invalid: set[str] = set()
+
+    for module in sorted(members):
+        source = parsed_sources.get(module)
+
+        if (
+            not isinstance(source, ParsedSourceInput)
+            or not isinstance(source.tree, ast.Module)
+            or not isinstance(source.source_fingerprint, str)
+            or len(source.source_fingerprint) != 64
+            or any(
+                c not in "0123456789abcdef"
+                for c in source.source_fingerprint
+            )
+        ):
+            invalid.add(module)
+            continue
+
+        node_count = 0
+
+        for _ in ast.walk(source.tree):
+            node_count += 1
+
+            if node_count > MAX_SOURCE_AST_NODES:
+                invalid.add(module)
+                break
+
+        if module in invalid:
+            continue
+
+        evidence = extract_import_provenance(
+            source.tree,
+            module_id=module,
+            source_key=module,
+            source_path=module,
+            source_fingerprint=source.source_fingerprint,
+        )
+
+        matches: dict[
+            str,
+            set[LexicalEdgeSite],
+        ] = {}
+
+        for occurrence in evidence.occurrences:
+            candidates = _candidate_targets(
+                occurrence,
+                module,
+                indexed,
+            )
+
+            for target, kind, requested, member in candidates:
+                site = LexicalEdgeSite(
+                    ordinal=occurrence.ordinal,
+                    line=occurrence.line,
+                    column=occurrence.column,
+                    form=occurrence.form,
+                    match_kind=kind,
+                    requested_name=requested,
+                    matched_member=member,
+                    scopes=occurrence.scopes,
+                    controls=occurrence.controls,
+                    activation_scope=_activation(
+                        occurrence.scopes,
+                        occurrence.controls,
+                    ),
+                )
+
+                matches.setdefault(target, set()).add(site)
+
+        available[module] = {
+            target: tuple(
+                sorted(
+                    sites,
+                    key=lambda site: (
+                        site.ordinal,
+                        site.match_kind,
+                        site.matched_member or "",
+                    ),
+                )
+            )
+            for target, sites in matches.items()
+        }
+
+    components: list[SCCImportSiteEvidence] = []
+
+    for component in topology.cyclic_components:
+        edges: list[HardEdgeSiteEvidence] = []
+
+        for source, target in component.internal_edges:
+            if source in invalid:
+                edges.append(
+                    HardEdgeSiteEvidence(
+                        source,
+                        target,
+                        "SOURCE_MISSING_OR_INVALID",
+                        (),
+                    )
+                )
+                continue
+
+            sites = available[source].get(target, ())
+
+            edges.append(
+                HardEdgeSiteEvidence(
+                    source,
+                    target,
+                    (
+                        "LEXICAL_CANDIDATES"
+                        if sites
+                        else "NO_MATCHING_LEXICAL_SITE"
+                    ),
+                    sites,
+                )
+            )
+
+        components.append(
+            SCCImportSiteEvidence(
+                members=component.members,
+                internal_edges=tuple(edges),
+                matched_edge_count=sum(
+                    edge.status == "LEXICAL_CANDIDATES"
+                    for edge in edges
+                ),
+                unresolved_edge_count=sum(
+                    edge.status != "LEXICAL_CANDIDATES"
+                    for edge in edges
+                ),
+            )
+        )
+
+    return CyclicImportSiteReport(
+        topology=topology,
+        components=tuple(components),
+    )

diff --git a/tests/test_cycle_semantics_edge_sites.py b/tests/test_cycle_semantics_edge_sites.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_edge_sites.py
@@ -0,0 +1,278 @@
+import ast
+import hashlib
+import json
+from dataclasses import FrozenInstanceError, asdict
+
+import pytest
+
+from contextor.core.source import ParsedSourceInput
+from contextor.core.cycle_semantics.edge_sites import (
+    analyze_cyclic_import_sites as analyze,
+)
+
+
+def _sources(**items):
+    return {
+        name: ParsedSourceInput(
+            ast.parse(code),
+            hashlib.sha256(code.encode()).hexdigest(),
+        )
+        for name, code in items.items()
+    }
+
+
+def test_plain_import_cycle():
+    result = analyze(
+        {"a": {"b"}, "b": {"a"}},
+        _sources(a="import b", b="import a"),
+    )
+    component = result.components[0]
+    assert component.matched_edge_count == 2
+    assert all(
+        edge.sites[0].match_kind == "DIRECT_MODULE"
+        for edge in component.internal_edges
+    )
+
+
+def test_relative_package_cycle():
+    graph = {
+        "pkg.__init__": {"pkg.child"},
+        "pkg.child": {"pkg.__init__"},
+    }
+    result = analyze(
+        graph,
+        _sources(**{
+            "pkg.__init__": "from . import child",
+            "pkg.child": "from pkg import value",
+        }),
+    )
+    edges = {
+        (edge.source, edge.target): edge
+        for edge in result.components[0].internal_edges
+    }
+    assert edges[
+        "pkg.__init__", "pkg.child"
+    ].sites[0].match_kind == "OPTIONAL_FROM_CHILD"
+    assert edges[
+        "pkg.child", "pkg.__init__"
+    ].sites[0].match_kind == "FROM_BASE"
+
+
+def test_parent_initializer_candidate():
+    graph = {
+        "pkg.__init__": {"pkg.child"},
+        "pkg.child": {"pkg.__init__"},
+    }
+    result = analyze(
+        graph,
+        _sources(**{
+            "pkg.__init__": "import pkg.child",
+            "pkg.child": "import pkg.child",
+        }),
+    )
+    edge = next(
+        edge
+        for edge in result.components[0].internal_edges
+        if edge.source == "pkg.child"
+    )
+    assert edge.sites[0].match_kind == "PARENT_INITIALIZER"
+
+
+def test_function_scope_and_guard_sites_are_not_eager_proofs():
+    result = analyze(
+        {"a": {"b"}, "b": {"a"}},
+        _sources(
+            a=(
+                "import b\n"
+                "def f():\n"
+                "    import b\n"
+                "if False:\n"
+                "    import b"
+            ),
+            b="import a",
+        ),
+    )
+    edge = next(
+        edge
+        for edge in result.components[0].internal_edges
+        if edge.source == "a"
+    )
+    assert [
+        site.activation_scope
+        for site in edge.sites
+    ] == [
+        "MODULE_TOP_LEVEL",
+        "FUNCTION_SCOPED",
+        "GUARDED_TOP_LEVEL",
+    ]
+    assert edge.sites[1].scopes
+    assert edge.sites[2].controls
+
+
+def test_only_function_local_candidate_is_preserved():
+    result = analyze(
+        {"a": {"b"}, "b": {"a"}},
+        _sources(
+            a="def f():\n    import b",
+            b="import a",
+        ),
+    )
+    edge = next(
+        edge
+        for edge in result.components[0].internal_edges
+        if edge.source == "a"
+    )
+    assert edge.status == "LEXICAL_CANDIDATES"
+    assert edge.sites[0].activation_scope == "FUNCTION_SCOPED"
+
+
+def test_missing_and_unmatched_not_dropped():
+    result = analyze(
+        {"a": {"b"}, "b": {"a"}},
+        _sources(a="pass"),
+    )
+    assert {
+        edge.status
+        for edge in result.components[0].internal_edges
+    } == {
+        "NO_MATCHING_LEXICAL_SITE",
+        "SOURCE_MISSING_OR_INVALID",
+    }
+    assert result.components[0].unresolved_edge_count == 2
+
+
+def test_unrelated_sources_do_not_change_results():
+    graph = {
+        "a": {"b"},
+        "b": {"a"},
+        "z": set(),
+    }
+    first = analyze(
+        graph,
+        _sources(
+            a="import b",
+            b="import a",
+            z="pass",
+        ),
+    )
+    second = analyze(
+        graph,
+        _sources(
+            a="import b",
+            b="import a",
+            z="import a",
+        ),
+    )
+    assert first == second
+
+
+def test_from_possible_child_is_not_proof():
+    graph = {
+        "pkg.__init__": {"pkg.x"},
+        "pkg.x": {"pkg.__init__"},
+    }
+    result = analyze(
+        graph,
+        _sources(**{
+            "pkg.__init__": "from pkg import x",
+            "pkg.x": "import pkg",
+        }),
+    )
+    edge = next(
+        edge
+        for edge in result.components[0].internal_edges
+        if edge.source == "pkg.__init__"
+    )
+    assert edge.sites[0].match_kind == "OPTIONAL_FROM_CHILD"
+    assert result.evidence_scope.endswith(
+        "NOT_RUNTIME_CERTIFICATION"
+    )
+
+
+def test_no_cycle():
+    result = analyze(
+        {"a": {"b"}, "b": set()},
+        _sources(a="import b", b="pass"),
+    )
+    assert result.components == ()
+
+
+def test_invalid_source_ast():
+    result = analyze(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            "a": ParsedSourceInput(
+                ast.parse("import b"),
+                hashlib.sha256(b"import b").hexdigest(),
+            ),
+            "b": None,
+        },
+    )
+    assert result.components[0].unresolved_edge_count == 1
+
+
+def test_relative_second_level():
+    graph = {
+        "p.__init__": {"p.sub.mod"},
+        "p.sub.__init__": {"p.__init__"},
+        "p.sub.mod": {
+            "p.__init__",
+            "p.sub.__init__",
+        },
+    }
+    sources = _sources(**{
+        "p.__init__": "from p.sub import mod",
+        "p.sub.__init__": "from .. import foo",
+        "p.sub.mod": "from .. import foo",
+    })
+    result = analyze(graph, sources)
+    edge = next(
+        edge
+        for edge in result.components[0].internal_edges
+        if edge.source == "p.sub.mod"
+        and edge.target == "p.__init__"
+    )
+    assert edge.sites[0].match_kind == "FROM_BASE"
+
+
+def test_determinism_and_frozen():
+    graph = {"a": {"b"}, "b": {"a"}}
+    sources = _sources(a="import b", b="import a")
+    result = analyze(graph, sources)
+    assert result == analyze(graph, sources)
+    json.dumps(asdict(result))
+
+    with pytest.raises(FrozenInstanceError):
+        result.components[0].matched_edge_count = 99
+
+    assert graph == {
+        "a": {"b"},
+        "b": {"a"},
+    }
+
+
+def test_invalid_input_raises():
+    with pytest.raises(TypeError):
+        analyze({"a": {"a"}}, None)
+
+    with pytest.raises(TypeError):
+        analyze(None, {})
+
+
+def test_invalid_fingerprint_is_not_treated_as_source():
+    result = analyze(
+        {"a": {"b"}, "b": {"a"}},
+        {
+            "a": ParsedSourceInput(
+                ast.parse("import b"),
+                "invalid",
+            ),
+            "b": _sources(b="import a")["b"],
+        },
+    )
+    edge = next(
+        edge
+        for edge in result.components[0].internal_edges
+        if edge.source == "a"
+    )
+    assert edge.status == "SOURCE_MISSING_OR_INVALID"

