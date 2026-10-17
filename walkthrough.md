# CONTEXTOR_B0G4C28_AUTOMATIC_CONDITIONAL_REEXPORT_SELECTOR

TASK: Controlled literal implementation of standalone conditional delayed-reexport candidate discovery.
HEAD_BEFORE: 2795a193809a0b42926df5d9bb72371cde01b4d7
HEAD_AFTER: 2795a193809a0b42926df5d9bb72371cde01b4d7
GIT_STATUS:
```text
?? contextor/core/cycle_semantics/conditional_discovery.py
?? tests/test_cycle_semantics_conditional_discovery.py
```
FILES_CHANGED:
- contextor\core\cycle_semantics\conditional_discovery.py (new production file)
- tests\test_cycle_semantics_conditional_discovery.py (new focused test file)

MODEL_CONTRACT_PRECHECK: DIRECT_EVIDENCE — Contextor MCP at revision 462 reported canonical_state=fresh, workspace_sync=verified for conditional_export.py, edge_sites.py, package_layout.py and source.py. Complete implementations of analyze_conditional_reexport_order, _exact_hop, analyze_cyclic_import_sites, build_package_layout and ParsedSourceInput were fetched. Canonical owner of source-order assessment is conditional_export; edge_sites owns lexical SCC attribution; package_layout owns package identity. Existing direct consumer of conditional_export was its focused test module; new selector has only its new test as current consumer. Blast radius of conditional_export had one direct test consumer and no downstream consumers before edits. Symbol lineage was inspected in preview. No existing equivalent selector was found in the verified contract.
EXACT_PRODUCTION_IMPLEMENTATION: CONTRACT_PROVED — production file byte-for-byte matches the attachment's authorized CONTENT block after its final newline. No package reexport or integration was added.
CANONICAL_SCC_INPUT: CODE_PATH_PROVED — consumes CyclicImportSiteReport components and internal edges; no simple-cycle enumeration or repository analysis.
PACKAGE_LAYOUT_FILTERING: CODE_PATH_PROVED — build_package_layout requires unique REGULAR_PACKAGE or MODULE_FILE identity, rejecting ambiguous layout.
LEXICAL_SOURCE_SITE_VALIDATION: CODE_PATH_PROVED — requires LEXICAL_CANDIDATES, unique _exact_hop and matching source location, IMPORT_FROM, FROM_BASE, MODULE_TOP_LEVEL and unguarded site.
PROVIDER_EXPORT_MATCHING: CODE_PATH_PROVED — matching unique FunctionDef must follow provider outgoing import; closing lookup must request same export; C26F validates complete selected chain.
BOUNDED_BFS_SELECTION: CODE_PATH_PROVED — iterative BFS selects one shortest validated return path per provider outgoing, max_searches 1..4096. No recursive unbounded traversal.
DETERMINISM_AND_DEDUPLICATION: TEST_COVERED — reversed graph/source insertion yields equal report; ordered SCC/edge traversal and seen chain/export identities.
AMBIGUOUS_SOURCE_HANDLING: TEST_COVERED — missing source, invalid fingerprint, invalid CPython compilation and ambiguous package layout fail closed; unmatched structural edges remain reported.
SOURCE_SNAPSHOT_BINDING_LIMITATION: CONTRACT_PROVED — NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY. Supplied AST/fingerprint collection is not atomically tied to canonical LIVE revision.
SEARCH_COVERAGE_STATUS: TEST_COVERED — BOUNDED_SELECTION_COMPLETE, PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE and PARTIAL_SEARCH_LIMIT exercised.
RUNTIME_EXECUTION_UNKNOWN: CONTRACT_PROVED — UNKNOWN_NOT_EVALUATED; no runtime ImportError or safety claim.

ISOLATED_TEST_RESULTS: 13 passed in 1.53s after final test edit; 13 passed before test constant rename as well.
FOCUSED_TEST_RESULTS: 23 files, 376 passed in 31.31s after final edit; prior run 376 passed in 50.75s. Full repository suite was not run. A preliminary invocation with an unexpanded PowerShell glob collected no tests; corrected with explicit file paths.
GIT_DIFF_CHECK: git diff --check and no-index --check for both new files produced no whitespace diagnostics. The combined shell's final exit code was 1 because git diff --no-index reports file differences.

LIVE_AUTHORITY_BEFORE_AFTER: DIRECT_EVIDENCE — identical complete nonsecret identity before/after: repo_id=ctx_8efc50d8; root_path=C:\Temp\Contextor_Repo; runtime_domain_id=rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654; service_instance_id=6f13273feccb46cb9c23fbbfee03afe1; lease_generation=31; service_pid=11632; process_start_identity=134367226998365614; endpoint_fingerprint=1367eadf1a11448d1a74eec69518da568d80ee42be8f16ce15e54998e989fcbd. Read-only LiveStateClient(is_owner=False), _read_endpoint and _status_matches_endpoint were used; no owner request.
ACTIVITY_EPOCH_BEFORE_AFTER: bbd40ce1942841df94718acedc12561f -> bbd40ce1942841df94718acedc12561f.
LIVE_REVISION_BEFORE_AFTER: 462 -> 465.
LIVE_EVENT_CONTINUITY: DIRECT_EVIDENCE — continuous; 463 desktop_watcher UPDATED production file, 464 desktop_watcher UPDATED test file, 465 desktop_watcher UPDATED test file after a local test-constant rename. resync_required=false. At 464 Contextor detected a name collision for SOURCES; 465 resolved it after rename.
WORKSPACE_SYNC: DIRECT_EVIDENCE — both new files verified at canonical revision 465.
CANONICAL_FRESHNESS: DIRECT_EVIDENCE — canonical_state=fresh, graph/cycles/collisions fresh, syntax diagnostics checked_and_none for both files, 0 syntax errors.
COLLISION_COUNT_BEFORE_AFTER: 0 -> 0, fresh. Transient 1 at revision 464 was resolved by revision 465; current canonical name collision query reports 0.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16 -> 16, fresh.
NO_RUNTIME_IMPORT_EXECUTION: DIRECT_EVIDENCE — only synthetic AST fixtures were parsed/compiled; no real GUI or Repo Generator module was imported by the test file.
NO_WARNING_SUPPRESSION: CODE_PATH_PROVED — no graph, detector, classification or diagnostics changes; structural cycles remained 16.
NO_RUNTIME_SAFETY_CERTIFICATION: CONTRACT_PROVED — selector explicitly reports runtime UNKNOWN.
FINAL_VERDICT: B0G4C28_PASS.

FULL_DIFFS:

## contextor\core\cycle_semantics\conditional_discovery.py

```diff
diff --git "a/contextor\\core\\cycle_semantics\\conditional_discovery.py" "b/contextor\\core\\cycle_semantics\\conditional_discovery.py"
new file mode 100644
index 0000000..00232fe
--- /dev/null
+++ "b/contextor\\core\\cycle_semantics\\conditional_discovery.py"
@@ -0,0 +1,424 @@
+"""Bounded discovery of conditional delayed-reexport candidates.
+
+Structural and lexical evidence is not execution evidence.
+Inputs do not authenticate an atomic canonical source snapshot.
+"""
+
+from __future__ import annotations
+
+import ast
+from collections import deque
+from collections.abc import Iterable, Mapping
+from dataclasses import dataclass
+
+from contextor.core.source import ParsedSourceInput
+
+from .conditional_export import (
+    ConditionalReexportAssessment,
+    _exact_hop,
+    _logical_module,
+    analyze_conditional_reexport_order,
+)
+from .edge_sites import CyclicImportSiteReport
+from .package_layout import build_package_layout
+
+
+@dataclass(frozen=True)
+class DiscoveredConditionalReexport:
+    package_initializer: str
+    provider: str
+    export_name: str
+    outgoing_target: str
+    assessment: ConditionalReexportAssessment
+
+
+@dataclass(frozen=True)
+class ConditionalDiscoveryReport:
+    candidates: tuple[DiscoveredConditionalReexport, ...]
+    examined_outgoing_count: int
+    unavailable_source_modules: tuple[str, ...]
+    unresolved_lexical_edge_count: int
+    coverage_status: str
+    search_scope: str = (
+        "ONE_SHORTEST_VALIDATED_PATH_PER_PROVIDER_OUTGOING"
+    )
+    source_snapshot_binding: str = (
+        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
+    )
+    runtime_execution_status: str = (
+        "UNKNOWN_NOT_EVALUATED"
+    )
+
+
+def _usable_source(
+    source: object,
+) -> ast.Module | None:
+    if (
+        not isinstance(source, ParsedSourceInput)
+        or not isinstance(source.tree, ast.Module)
+        or not isinstance(source.source_fingerprint, str)
+        or len(source.source_fingerprint) != 64
+        or any(
+            char not in "0123456789abcdef"
+            for char in source.source_fingerprint
+        )
+    ):
+        return None
+
+    count = 0
+
+    for _ in ast.walk(source.tree):
+        count += 1
+
+        if count > 100_000:
+            return None
+
+    try:
+        compile(
+            source.tree,
+            "<conditional_discovery>",
+            "exec",
+            dont_inherit=True,
+        )
+    except (
+        SyntaxError,
+        TypeError,
+        ValueError,
+        RecursionError,
+        OverflowError,
+    ):
+        return None
+
+    return source.tree
+
+
+def _shortest_return_path(
+    start: str,
+    package: str,
+    provider: str,
+    export_name: str,
+    adjacency: Mapping[str, tuple[str, ...]],
+    hops: Mapping[tuple[str, str], object],
+) -> tuple[str, ...] | None:
+    """Iterative BFS with deterministic lexical tie resolution."""
+    if start in {package, provider}:
+        return None
+
+    queue = deque([start])
+    previous: dict[str, str | None] = {
+        start: None,
+    }
+
+    while queue:
+        current = queue.popleft()
+
+        if current == package:
+            break
+
+        for target in adjacency.get(current, ()):
+            if target == provider:
+                continue
+
+            if (
+                target == package
+                and hops[(current, target)].requested_member
+                != export_name
+            ):
+                continue
+
+            if target in previous:
+                continue
+
+            previous[target] = current
+            queue.append(target)
+
+    if package not in previous:
+        return None
+
+    reverse_path = []
+    current: str | None = package
+
+    while current is not None:
+        reverse_path.append(current)
+        current = previous[current]
+
+    return tuple(reversed(reverse_path))
+
+
+def discover_conditional_reexports(
+    import_sites: CyclicImportSiteReport,
+    parsed_sources: Mapping[str, ParsedSourceInput],
+    indexed_module_ids: Iterable[str],
+    *,
+    max_searches: int = 256,
+) -> ConditionalDiscoveryReport:
+    """Discover bounded candidate chains, then validate with C26F.
+
+    The caller must supply a coherent candidate graph and source
+    collection. This function cannot establish LIVE revision
+    atomicity or runtime execution.
+    """
+
+    if not isinstance(import_sites, CyclicImportSiteReport):
+        raise TypeError(
+            "import_sites must be CyclicImportSiteReport"
+        )
+
+    if not isinstance(parsed_sources, Mapping):
+        raise TypeError(
+            "parsed_sources must be a mapping"
+        )
+
+    if (
+        type(max_searches) is not int
+        or not 1 <= max_searches <= 4096
+    ):
+        raise ValueError(
+            "max_searches must be in range 1..4096"
+        )
+
+    layout = build_package_layout(indexed_module_ids)
+
+    layout_by_name = {
+        node.name: node
+        for node in layout.nodes
+    }
+
+    candidates = []
+    seen = set()
+    unavailable = set()
+    unresolved = 0
+    examined = 0
+    truncated = False
+
+    for component in sorted(
+        import_sites.components,
+        key=lambda item: item.members,
+    ):
+        members = set(component.members)
+
+        trees = {}
+
+        for member in sorted(members):
+            tree = _usable_source(
+                parsed_sources.get(member)
+            )
+
+            if tree is None:
+                unavailable.add(member)
+            else:
+                trees[member] = tree
+
+        edge_records = {
+            (edge.source, edge.target): edge
+            for edge in component.internal_edges
+        }
+
+        eligible_hops = {}
+
+        for source, target in sorted(edge_records):
+            edge = edge_records[(source, target)]
+
+            if edge.status != "LEXICAL_CANDIDATES":
+                unresolved += 1
+                continue
+
+            if source not in trees or target not in trees:
+                continue
+
+            source_layout = layout_by_name.get(
+                _logical_module(source)
+            )
+            target_layout = layout_by_name.get(
+                _logical_module(target)
+            )
+
+            if (
+                source_layout is None
+                or target_layout is None
+                or source_layout.kind not in {
+                    "REGULAR_PACKAGE",
+                    "MODULE_FILE",
+                }
+                or target_layout.kind not in {
+                    "REGULAR_PACKAGE",
+                    "MODULE_FILE",
+                }
+                or source_layout.indexed_module_ids
+                != (source,)
+                or target_layout.indexed_module_ids
+                != (target,)
+            ):
+                continue
+
+            hop = _exact_hop(
+                trees,
+                source,
+                target,
+            )
+
+            if hop is None:
+                continue
+
+            if not any(
+                site.line == hop.line
+                and site.column == hop.column
+                and site.form == "IMPORT_FROM"
+                and site.match_kind == "FROM_BASE"
+                and site.activation_scope
+                == "MODULE_TOP_LEVEL"
+                and not site.controls
+                for site in edge.sites
+            ):
+                continue
+
+            eligible_hops[(source, target)] = hop
+
+        adjacency_dict: dict[str, list[str]] = {}
+
+        for source, target in sorted(eligible_hops):
+            adjacency_dict.setdefault(
+                source, []
+            ).append(target)
+
+        adjacency = {
+            source: tuple(sorted(set(targets)))
+            for source, targets
+            in adjacency_dict.items()
+        }
+
+        package_initializers = sorted(
+            member
+            for member in members
+            if member.endswith(".__init__")
+            and member in trees
+            and (
+                node := layout_by_name.get(
+                    _logical_module(member)
+                )
+            ) is not None
+            and node.kind == "REGULAR_PACKAGE"
+            and node.indexed_module_ids == (member,)
+        )
+
+        for package in package_initializers:
+            for provider in adjacency.get(package, ()):
+                first_hop = eligible_hops[
+                    (package, provider)
+                ]
+
+                export_name = first_hop.requested_member
+
+                provider_tree = trees[provider]
+
+                definitions = [
+                    statement
+                    for statement in provider_tree.body
+                    if isinstance(
+                        statement,
+                        ast.FunctionDef,
+                    )
+                    and statement.name == export_name
+                ]
+
+                if len(definitions) != 1:
+                    continue
+
+                definition_line = definitions[0].lineno
+
+                for outgoing in adjacency.get(provider, ()):
+                    outgoing_hop = eligible_hops[
+                        (provider, outgoing)
+                    ]
+
+                    if outgoing_hop.line >= definition_line:
+                        continue
+
+                    if examined >= max_searches:
+                        truncated = True
+                        break
+
+                    examined += 1
+
+                    return_path = _shortest_return_path(
+                        outgoing,
+                        package,
+                        provider,
+                        export_name,
+                        adjacency,
+                        eligible_hops,
+                    )
+
+                    if return_path is None:
+                        continue
+
+                    chain = (
+                        package,
+                        provider,
+                    ) + return_path
+
+                    if (
+                        len(chain) < 4
+                        or len(set(chain[:-1]))
+                        != len(chain) - 1
+                    ):
+                        continue
+
+                    identity = (
+                        chain,
+                        export_name,
+                    )
+
+                    if identity in seen:
+                        continue
+
+                    seen.add(identity)
+
+                    assessment = (
+                        analyze_conditional_reexport_order(
+                            trees,
+                            chain,
+                            export_name,
+                        )
+                    )
+
+                    if assessment.status != (
+                        "CONDITIONAL_DELAYED_REEXPORT"
+                    ):
+                        continue
+
+                    candidates.append(
+                        DiscoveredConditionalReexport(
+                            package_initializer=package,
+                            provider=provider,
+                            export_name=export_name,
+                            outgoing_target=outgoing,
+                            assessment=assessment,
+                        )
+                    )
+
+                if truncated:
+                    break
+
+            if truncated:
+                break
+
+        if truncated:
+            break
+
+    if truncated:
+        coverage = "PARTIAL_SEARCH_LIMIT"
+    elif unavailable or unresolved:
+        coverage = "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"
+    else:
+        coverage = "BOUNDED_SELECTION_COMPLETE"
+
+    return ConditionalDiscoveryReport(
+        candidates=tuple(candidates),
+        examined_outgoing_count=examined,
+        unavailable_source_modules=tuple(
+            sorted(unavailable)
+        ),
+        unresolved_lexical_edge_count=unresolved,
+        coverage_status=coverage,
+    )
```

## tests\test_cycle_semantics_conditional_discovery.py

```diff
diff --git "a/tests\\test_cycle_semantics_conditional_discovery.py" "b/tests\\test_cycle_semantics_conditional_discovery.py"
new file mode 100644
index 0000000..e22a028
--- /dev/null
+++ "b/tests\\test_cycle_semantics_conditional_discovery.py"
@@ -0,0 +1,205 @@
+"""Focused synthetic contracts for conditional reexport discovery."""
+
+import ast
+from dataclasses import asdict
+from hashlib import sha256
+import json
+
+import pytest
+
+from contextor.core.cycle_semantics.conditional_discovery import (
+    discover_conditional_reexports,
+)
+from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
+from contextor.core.source import ParsedSourceInput
+
+
+GRAPH = {
+    "repo.__init__": ("repo.main",),
+    "repo.main": ("repo.filters", "ui.__init__"),
+    "repo.filters": ("ui.__init__",),
+    "ui.__init__": ("ui.gui",),
+    "ui.gui": ("repo.__init__",),
+}
+
+C28_FIXTURE_SOURCES = {
+    "repo.__init__": "from repo.main import run_repo_generator\n",
+    "repo.main": (
+        "from repo.filters import FilterWindow\n"
+        "from ui import theme\n"
+        "\n"
+        "def run_repo_generator(parent=None):\n"
+        "    pass\n"
+    ),
+    "repo.filters": "from ui import theme\n",
+    "ui.__init__": "from .gui import run\n",
+    "ui.gui": (
+        "from repo import run_repo_generator\n"
+        "\n"
+        "def run(*, single_instance=None):\n"
+        "    pass\n"
+    ),
+}
+
+
+def _inputs(*, sources=None, graph=None, indexed=None):
+    source_text = C28_FIXTURE_SOURCES if sources is None else sources
+    edges = GRAPH if graph is None else graph
+    parsed = {
+        module: ParsedSourceInput(
+            tree=ast.parse(text),
+            source_fingerprint=sha256(text.encode("utf-8")).hexdigest(),
+        )
+        for module, text in source_text.items()
+    }
+    sites = analyze_cyclic_import_sites(edges, parsed)
+    module_ids = tuple(GRAPH) if indexed is None else indexed
+    return sites, parsed, module_ids
+
+
+def _discover(*, sources=None, graph=None, indexed=None, max_searches=256):
+    sites, parsed, module_ids = _inputs(
+        sources=sources, graph=graph, indexed=indexed
+    )
+    return discover_conditional_reexports(
+        sites, parsed, module_ids, max_searches=max_searches
+    )
+
+
+def _chains(report):
+    return {candidate.assessment.chain for candidate in report.candidates}
+
+
+VIA_FILTERS = (
+    "repo.__init__", "repo.main", "repo.filters",
+    "ui.__init__", "ui.gui", "repo.__init__",
+)
+DIRECT = (
+    "repo.__init__", "repo.main", "ui.__init__",
+    "ui.gui", "repo.__init__",
+)
+
+
+def test_c28_discovers_two_distinct_outgoing_paths():
+    report = _discover()
+    assert len(report.candidates) == 2
+    assert _chains(report) == {VIA_FILTERS, DIRECT}
+    assert {item.export_name for item in report.candidates} == {
+        "run_repo_generator"
+    }
+    assert {item.assessment.status for item in report.candidates} == {
+        "CONDITIONAL_DELAYED_REEXPORT"
+    }
+    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+    assert report.source_snapshot_binding == "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
+    assert report.coverage_status == "BOUNDED_SELECTION_COMPLETE"
+
+
+def test_c28_determinism_independent_graph_order():
+    graph = dict(reversed(list(GRAPH.items())))
+    sources = dict(reversed(list(C28_FIXTURE_SOURCES.items())))
+    assert _discover() == _discover(graph=graph, sources=sources)
+
+
+def test_c28_function_scoped_return_is_not_eager():
+    sources = dict(C28_FIXTURE_SOURCES)
+    sources["repo.filters"] = "def later():\n    from ui import theme\n"
+    report = _discover(sources=sources)
+    assert _chains(report) == {DIRECT}
+
+
+def test_c28_mismatched_closing_export():
+    sources = dict(C28_FIXTURE_SOURCES)
+    sources["ui.gui"] = "from repo import other_name\n"
+    report = _discover(sources=sources)
+    assert report.candidates == ()
+    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+
+
+def test_c28_duplicate_exact_source_hop_rejected():
+    sources = dict(C28_FIXTURE_SOURCES)
+    sources["repo.filters"] = "from ui import theme\nfrom ui import theme\n"
+    report = _discover(sources=sources)
+    assert _chains(report) == {DIRECT}
+
+
+def test_c28_ambiguous_layout_rejected():
+    report = _discover(indexed=tuple(GRAPH) + ("repo",))
+    assert report.candidates == ()
+
+
+def test_c28_missing_source_partial():
+    sources = dict(C28_FIXTURE_SOURCES)
+    del sources["repo.filters"]
+    report = _discover(sources=sources)
+    assert "repo.filters" in report.unavailable_source_modules
+    assert report.coverage_status == "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"
+    assert _chains(report) == {DIRECT}
+    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
+
+
+def test_c28_invalid_fingerprint_is_not_trusted():
+    sites, parsed, indexed = _inputs()
+    parsed["ui.gui"] = ParsedSourceInput(parsed["ui.gui"].tree, "invalid")
+    report = discover_conditional_reexports(
+        analyze_cyclic_import_sites(GRAPH, parsed), parsed, indexed
+    )
+    assert report.candidates == ()
+    assert "ui.gui" in report.unavailable_source_modules
+    assert report.coverage_status == "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"
+
+
+def test_c28_bounded_search_limit():
+    report = _discover(max_searches=1)
+    assert report.examined_outgoing_count == 1
+    assert report.coverage_status == "PARTIAL_SEARCH_LIMIT"
+    assert len(report.candidates) < 2
+
+
+def test_c28_source_ast_immutability_and_json():
+    sites, parsed, indexed = _inputs()
+    before = {
+        module: ast.dump(source.tree, include_attributes=True)
+        for module, source in parsed.items()
+    }
+    first = discover_conditional_reexports(sites, parsed, indexed)
+    second = discover_conditional_reexports(sites, parsed, indexed)
+    after = {
+        module: ast.dump(source.tree, include_attributes=True)
+        for module, source in parsed.items()
+    }
+    assert first == second
+    assert before == after
+    json.dumps(asdict(first))
+
+
+def test_c28_unresolved_lexical_edges_preserved():
+    graph = dict(GRAPH)
+    graph["repo.filters"] = ("ui.__init__", "repo.__init__")
+    report = _discover(graph=graph)
+    assert report.unresolved_lexical_edge_count >= 1
+    assert report.coverage_status == "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"
+    assert _chains(report) == {VIA_FILTERS, DIRECT}
+
+
+def test_c28_rejects_invalid_search_limits():
+    sites, parsed, indexed = _inputs()
+    for limit in (0, -1, 4097, True):
+        with pytest.raises(ValueError):
+            discover_conditional_reexports(
+                sites, parsed, indexed, max_searches=limit
+            )
+
+
+def test_c28_invalid_cpython_module_fails_closed():
+    sources = dict(C28_FIXTURE_SOURCES)
+    sources["ui.gui"] = (
+        "from repo import run_repo_generator\n"
+        "def invalid():\n"
+        "    from repo import *\n"
+    )
+    assert isinstance(ast.parse(sources["ui.gui"]), ast.Module)
+    report = _discover(sources=sources)
+    assert report.candidates == ()
+    assert "ui.gui" in report.unavailable_source_modules
+    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
```
