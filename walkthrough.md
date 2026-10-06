CPA_CANONICAL_REEXPORT_LINEAGE_QUERY_INTEGRATION

STATUS=STEP_PASS
CLASSIFICATION=CANONICAL_REEXPORT_LINEAGE_QUERY_INTEGRATION_CERTIFIED

HEAD_BEFORE=f65b0a66e0fcb8fbac93efcdeae0aa643ca9c181
HEAD_AT_REPORT=f65b0a66e0fcb8fbac93efcdeae0aa643ca9c181
WORKTREE_BEFORE=CLEAN
SOURCE_DRIFT=NONE; actual Contextor source at HEAD matched the discovered symbols and implementation anchors before the edits.

RUNTIME_DISCOVERY
- Contextor architectural discovery was used for build_lineage_query_indexes, RepositoryStateLineageBackend, build_live_lineage_target_catalog, query_live_symbol_lineage, render_symbol_lineage_response, and get_symbol_lineage, plus their concrete owners and consumers. The generic CanonicalLineageBackend protocol remains unchanged.
- Targeted source retrieval initially reported LIVE revision 1528, canonical_state=fresh and workspace_sync=verified for the queried source symbols. The persisted global architecture bundle was older (commit 239c609beef6bc92ef661024ef014c0b640b215d, generated 2026-10-06T17:38:59.679438, workspace_sync=unverified); it was not treated as current source authority.
- Desktop watcher observed edits from revisions 1529 through 1547. Continuity=continuous, resync_required=false; latest syntax_errors, name_collisions and cycles diagnostics are fresh with count 0 and attention_required=false. No MCP update_file or restart was used.
- HEAD stayed unchanged; no commit or push was made.

EVIDENCE_LEDGER
DIRECT_EVIDENCE=Targeted pytest node outputs below; canonical query assertions identify origin owners and hop chains; watcher revisions 1529-1547 are continuous with zero fresh diagnostic counts.
CODE_PATH_PROVED=Contextor symbol/consumer discovery and literal source inspection establish the path from canonical re-export facts through backend, live query, existing target service, response renderer, MCP tool, and docs.
CONTRACT_PROVED=Named node gates verify multi-hop, package, star, cycle/external, no-source-I/O, response sizing/representation, and fresh full-oracle parity.
INFERENCE=The alias index has no persistence path because it is constructed lazily on a backend instance and no persisted model/schema owners were changed.
UNKNOWN=Post-restart hydration freshness remains unverified; no restart occurred. The deferred bare star-bound call-site resolution remains outside this query integration.
REEXPORT_QUERY_INDEX
`build_reexport_lineage_alias_index` derives a per-backend RAM index from validated canonical `reexport_facts_by_module`. It installs named binding edges regardless of `__all__`, excludes self-definition edges, and obtains visible star names from `_assemble_module_export_surfaces`. Star lineage preserves immediate source hops. Query backend validates the full facts/module domain on first use and caches the derived mapping only on that backend instance.

ALIAS_EDGE_CONTRACT
- Direct edge: `exporter::local -> qualified target`, kind=binding; named direct aliases remain queryable even when excluded from `__all__`.
- Own definition: no alias edge.
- Star edge: `exporter::name -> immediate star_source::name`, kind=star, only for canonical visible names.
- Direct namespace entries take precedence over star imports. Multiple star sources preserve the current export-surface model's deterministic first installer; the focused fixture verifies that the first canonical source wins.
- The protocol and persisted state are not extended.

CHAIN_RESOLUTION
Resolution follows immediate edges and canonicalizes only the repository leaf. Multi-hop chains retain intermediate binding and star identities, including a package façade identity when it is itself an intermediate alias. Cycles close the hop list and return status=cycle, reason=reexport_cycle, canonical_target=null. External dotted targets that cannot map to a real indexed module fail closed as status=unresolved, reason=target_outside_repository; no short-name or provider guess is made.

CYCLE_POLICY
PASS. The cycle query returns unresolved to the live caller, retains a cycle chain ending at the repeated identity, has no selected facts, and does not select an arbitrary origin.

PACKAGE_QUERY_IDENTITY
PASS. `pkg::LOCAL` resolves through exact package canonicalization to the real `pkg.__init__::LOCAL` owner with resolution=package_alias and no reexport_chain. `pkg::public_run` resolves through the canonical re-export edge to `pkg.provider::run`. A separate chain confirms that `pkg::public_run` remains a traversable intermediate façade identity.

STAR_QUERY_IDENTITY
PASS. Visible two-hop star aliases resolve to the original `star_src` owner and preserve both immediate star hops. Private `_hidden` is not exported. A named binding with `__all__=[]` remains resolvable. The explicit direct-vs-star precedence and two-source order cases pass.
STAR_BOUND_BARE_CALL_RESOLUTION=DEFERRED_TO_AST_AUDIT

LIVE_TARGET_RESOLUTION
Exact canonical/package target resolution remains first. Only exact qualified not_found queries enter alias fallback. not_alias preserves not_found. A resolved chain is handed to the existing exact catalog and LineageQueryService for the origin. Missing canonical origin fails closed as unavailable with `Canonical re-export origin has no available lineage owner.` Cycle and outside-repository results return unresolved without constructing selected facts.

CANONICAL_ORIGIN_SELECTION
PASS. For `c::exported`, the resolved target is the real `a::foo` artifact (fixture owner `A1/1`), with target.resolution=reexport_alias and original query retained. Existing canonical sections are selected from the origin owner; no synthetic alias artifact or owner was introduced.

MCP_RESPONSE_CONTRACT
PASS. Resolved payloads add only the optional top-level `reexport_chain`; chain is identical under named/indexed representations and never enters `sections`. Rendered sections match the pre-chain payload for each representation. None omits the field. The represented preview's candidate_response_bytes match the exact serialized candidate including the chain. Cycle/external unresolved tool responses include their required error and chain. Documentation remains contract version 1.0.0; no repository policy requiring an additive-field bump was found.

FULL_LIVE_PARITY
FULL_LIVE_REEXPORT_LINEAGE_PARITY=PASS. `test_reexport_lineage_query_retarget_matches_full_oracle` establishes fresh full baseline `c::exported -> a::foo`, changes only `b.py` to target `a::bar`, updates incrementally, and compares the live result and a fresh full oracle: status, canonical target, chain and selected semantic payload. Only revision/provenance keys are normalized for selected payload comparison.

SOURCE_IO_PROOF
REEXPORT_LINEAGE_QUERY_SOURCE_READS=ZERO
REEXPORT_LINEAGE_QUERY_AST_ACCESSES=ZERO
The query-only fixture patches `Module.ast_tree`, `_get_cached_ast` and `Path.open` to raise. Multi-hop, one-hop, package, star, direct-binding, cycle, external and missing-origin alias queries pass under these guards. Full oracle construction is outside this guard.

PERSISTENCE_IMPACT
PERSISTENCE_CHANGE_REQUIRED=NO
SNAPSHOT_SCHEMA_CHANGE_REQUIRED=NO
No repository state, lineage fact, semantic version, snapshot normalization, persistence, or schema files changed. The alias index is derived and RAM-only.

TARGETED_TESTS
- `tests/analysis/test_lineage_query_backend.py`: metadata, indexed owner lookup, fail-closed freshness, lazy alias-index build and incomplete-domain gate.
- `tests/analysis/test_lineage_live_query.py`: exact target, not-found, ambiguity, single-slice lookup and the new package/star/binding/cycle/external/source-I/O integration gate.
- `tests/mcp/test_lineage_response.py`: no-chain freshness behavior, existing represented preview sizing, and the new top-level chain / named-indexed / preview sizing gate.
- `tests/mcp/tools/test_get_symbol_lineage.py`: existing direct response contracts plus resolved-chain forwarding and cycle/external unresolved payload gates.
- Required existing re-export regression nodes: transitive aliased re-export, relative package initializer, star `__all__`, cyclic re-export, RAM-only `__all__` update parity, and package initializer addition propagation.
- New full/live retarget parity node: `tests/test_completeness_freshness_parity_proof.py::test_reexport_lineage_query_retarget_matches_full_oracle`.
- Correct named-node batch result: 32 passed and one initially authored response test failed because its fetch request selected only `interface` while the existing fixture had all canonical sections selected. The test setup was corrected to use `SYMBOL_LINEAGE_SECTION_ORDER`; the exact node then passed on rerun. The final post-chain-change focused rerun passed 5/5, including the changed live query, parity, response, cycle and external nodes.
- Execution-scope deviation: one pytest command accidentally included the positional directory `tests/`; pytest began broad collection and was interrupted at approximately 15% progress. No full-suite completion or result is claimed. The subsequent validation used only explicit node IDs.
- `git diff --check` over the 11 listed source/test/docs files: exit 0. `get_symbol_lineage.json` parsed successfully.

TEST_RESULTS
Required targeted regression gates: PASS after the test-fixture correction and the final package-intermediate-chain change. No production behavior failure observed.
TEST_POLICY_DEVIATION=ACCIDENTAL_BROAD_COLLECTION_STARTED_AND_ABORTED_AT_APPROXIMATELY_15_PERCENT

FILES_CHANGED
- contextor/core/lineage_query/index.py
- contextor/core/lineage_query/backend.py
- contextor/core/lineage_query/live_query.py
- contextor/mcp/lineage_response.py
- contextor/mcp/tools/get_symbol_lineage.py
- contextor/mcp/docs/get_symbol_lineage.json
- tests/analysis/test_lineage_live_query.py
- tests/analysis/test_lineage_query_backend.py
- tests/test_completeness_freshness_parity_proof.py
- tests/mcp/test_lineage_response.py
- tests/mcp/tools/test_get_symbol_lineage.py

MCP_RESTART_REQUIRED=YES_AFTER_STEP
FULL_ANALYSIS_REQUIRED_AFTER_RESTART=NO, provided post-restart hydration confirms canonical_state=fresh, lineage=fresh, complete reexport fact domain and resync_required=false. That hydration has not yet been checked because no restart was requested or performed.

FULL_DIFFS
diff --git a/contextor/core/lineage_query/backend.py b/contextor/core/lineage_query/backend.py
index e0e5a5b..359fddd 100644
--- a/contextor/core/lineage_query/backend.py
+++ b/contextor/core/lineage_query/backend.py
@@ -10,6 +10,13 @@ from contextor.core.domain.lineage_facts import (
     SemanticEndpoint,
     SourceLineageManifest,
 )
+from contextor.core.lineage_query.index import (
+    ReexportLineageResolution,
+    build_reexport_lineage_alias_index,
+    canonicalize_lineage_qualified_identity,
+    resolve_reexport_lineage_alias,
+)
+from contextor.core.reference.shared import validate_reexport_facts_by_module
 
 
 _MISSING = object()
@@ -71,6 +78,45 @@ class RepositoryStateLineageBackend:
 
         self._state = state
         self._sources = raw_sources
+        self._modules = getattr(state, "modules", {})
+        self._reexport_facts_by_module = getattr(
+            state,
+            "reexport_facts_by_module",
+            {},
+        )
+        self._reexport_alias_index = None
+
+    def canonicalize_qualified_identity(
+        self,
+        qualified_name: str,
+    ) -> str:
+        return canonicalize_lineage_qualified_identity(
+            qualified_name,
+            self._modules,
+        )
+
+    def resolve_reexport_alias(
+        self,
+        query: str,
+    ) -> ReexportLineageResolution:
+        if self._reexport_alias_index is None:
+            if not validate_reexport_facts_by_module(
+                self._reexport_facts_by_module,
+                self._modules,
+            ):
+                raise ValueError(
+                    "Canonical re-export facts are unavailable or incomplete."
+                )
+            self._reexport_alias_index = (
+                build_reexport_lineage_alias_index(
+                    self._reexport_facts_by_module
+                )
+            )
+        return resolve_reexport_lineage_alias(
+            query,
+            self._reexport_alias_index,
+            self._modules,
+        )
 
     def metadata(self) -> LineageBackendMetadata:
         raw_revision = getattr(self._state, "revision", None)
diff --git a/contextor/core/lineage_query/index.py b/contextor/core/lineage_query/index.py
index 01482d7..8218469 100644
--- a/contextor/core/lineage_query/index.py
+++ b/contextor/core/lineage_query/index.py
@@ -1,11 +1,341 @@
 from __future__ import annotations
 
 from collections.abc import Mapping
+from dataclasses import dataclass
 
 from contextor.core.domain.lineage_facts import (
     MaterializedLineageSourceFacts,
     SemanticEndpoint,
 )
+from contextor.core.reference.shared import (
+    _canonicalize_package_reference_target,
+    _assemble_module_export_surfaces,
+)
+
+
+@dataclass(frozen=True)
+class ReexportLineageHop:
+    source: str
+    target: str
+    kind: str
+
+    def __post_init__(self) -> None:
+        if not isinstance(self.source, str) or not self.source:
+            raise ValueError("re-export hop source must be a non-empty string.")
+        if not isinstance(self.target, str) or not self.target:
+            raise ValueError("re-export hop target must be a non-empty string.")
+        if self.kind not in {"binding", "star"}:
+            raise ValueError("re-export hop kind must be 'binding' or 'star'.")
+
+
+@dataclass(frozen=True)
+class ReexportLineageResolution:
+    status: str
+    query: str
+    canonical_target: str | None = None
+    hops: tuple[ReexportLineageHop, ...] = ()
+    reason: str | None = None
+
+    def __post_init__(self) -> None:
+        if self.status not in {"not_alias", "resolved", "cycle", "unresolved"}:
+            raise ValueError("re-export lineage resolution status is invalid.")
+        if not isinstance(self.query, str):
+            raise TypeError("re-export lineage query must be a string.")
+        if self.canonical_target is not None and (
+            not isinstance(self.canonical_target, str)
+            or not self.canonical_target
+        ):
+            raise ValueError("canonical_target must be a non-empty string or None.")
+        if not isinstance(self.hops, tuple) or any(
+            not isinstance(hop, ReexportLineageHop) for hop in self.hops
+        ):
+            raise TypeError("re-export lineage hops must be a tuple of hops.")
+        if self.reason is not None and not isinstance(self.reason, str):
+            raise TypeError("re-export lineage reason must be a string or None.")
+
+
+def canonicalize_lineage_qualified_identity(
+    qualified_name: str,
+    modules,
+) -> str:
+    if not isinstance(qualified_name, str):
+        raise TypeError("qualified_name must be a string.")
+    if not isinstance(modules, Mapping):
+        raise TypeError("modules must be a mapping.")
+    if qualified_name.count("::") != 1:
+        return qualified_name
+
+    module_name, symbol_name = qualified_name.split("::", 1)
+    if not module_name or not symbol_name:
+        return qualified_name
+
+    dotted = f"{module_name}.{symbol_name}"
+    canonical_dotted = _canonicalize_package_reference_target(
+        dotted,
+        modules,
+    )
+    if not isinstance(canonical_dotted, str) or not canonical_dotted:
+        return qualified_name
+
+    module_names = set(modules)
+    parts = canonical_dotted.split(".")
+    for split_at in range(len(parts) - 1, 0, -1):
+        candidate_module = ".".join(parts[:split_at])
+        if candidate_module not in module_names:
+            continue
+        candidate_symbol = ".".join(parts[split_at:])
+        if candidate_symbol:
+            return f"{candidate_module}::{candidate_symbol}"
+    return qualified_name
+
+
+def _qualified_reexport_target(
+    target: str,
+    known_modules: set[str],
+) -> str:
+    if target.count("::") == 1:
+        return target
+    parts = target.split(".")
+    for split_at in range(len(parts) - 1, 0, -1):
+        candidate_module = ".".join(parts[:split_at])
+        if candidate_module not in known_modules:
+            continue
+        candidate_symbol = ".".join(parts[split_at:])
+        if candidate_symbol:
+            return f"{candidate_module}::{candidate_symbol}"
+    return target
+
+
+def build_reexport_lineage_alias_index(
+    reexport_facts_by_module,
+) -> dict[str, ReexportLineageHop]:
+    if not isinstance(reexport_facts_by_module, Mapping):
+        raise TypeError("reexport_facts_by_module must be a mapping.")
+
+    facts_by_exporter: dict[str, Mapping[str, object]] = {}
+    known_modules: set[str] = set()
+    for facts in reexport_facts_by_module.values():
+        if not isinstance(facts, Mapping):
+            raise TypeError("canonical re-export fact must be a mapping.")
+        exporter = facts.get("exporter")
+        bindings = facts.get("bindings")
+        star_sources = facts.get("star_sources")
+        if not isinstance(exporter, str) or not exporter:
+            raise ValueError("canonical re-export exporter is invalid.")
+        if not isinstance(bindings, Mapping):
+            raise ValueError("canonical re-export bindings are invalid.")
+        if not isinstance(star_sources, (list, tuple)) or any(
+            not isinstance(source, str) or not source
+            for source in star_sources
+        ):
+            raise ValueError("canonical re-export star_sources are invalid.")
+        if exporter in facts_by_exporter:
+            raise ValueError("canonical re-export exporter identity is duplicated.")
+        facts_by_exporter[exporter] = facts
+        known_modules.add(exporter)
+        known_modules.update(star_sources)
+
+    module_export_surfaces = _assemble_module_export_surfaces(
+        dict(reexport_facts_by_module)
+    )
+    alias_index: dict[str, ReexportLineageHop] = {}
+
+    def install(hop: ReexportLineageHop) -> None:
+        existing = alias_index.get(hop.source)
+        if existing is not None and existing != hop:
+            raise ValueError("canonical re-export alias identity is ambiguous.")
+        alias_index[hop.source] = hop
+
+    for exporter, facts in facts_by_exporter.items():
+        bindings = facts["bindings"]
+        assert isinstance(bindings, Mapping)
+        for local, target in bindings.items():
+            if not isinstance(local, str) or not local:
+                raise ValueError("canonical re-export binding name is invalid.")
+            if not isinstance(target, str) or not target:
+                raise ValueError("canonical re-export binding target is invalid.")
+            source = f"{exporter}::{local}"
+            if f"{exporter}.{local}" == target:
+                continue
+            install(
+                ReexportLineageHop(
+                    source=source,
+                    target=_qualified_reexport_target(target, known_modules),
+                    kind="binding",
+                )
+            )
+
+    # Reproduce the existing export-surface assembler's deterministic
+    # fixed-point ordering to retain the first star source that installs a
+    # visible local. The final visibility set still comes from its canonical
+    # helper above.
+    working_surfaces: dict[str, dict[str, str]] = {}
+    direct_bindings: dict[str, Mapping[str, object]] = {}
+    star_imports: list[tuple[str, str, set[str] | None]] = []
+    for exporter, facts in facts_by_exporter.items():
+        bindings = facts["bindings"]
+        explicit_all = facts.get("explicit_all")
+        if explicit_all is not None and not isinstance(explicit_all, (list, tuple)):
+            raise ValueError("canonical re-export explicit_all is invalid.")
+        allowed = None if explicit_all is None else set(explicit_all)
+        assert isinstance(bindings, Mapping)
+        direct_bindings[exporter] = bindings
+        visible: dict[str, str] = {}
+        for local, target in bindings.items():
+            if not isinstance(local, str) or not isinstance(target, str):
+                raise ValueError("canonical re-export binding is invalid.")
+            if allowed is not None and local not in allowed:
+                continue
+            if allowed is None and local.startswith("_"):
+                continue
+            visible[local] = target
+        working_surfaces[exporter] = visible
+        for source in facts["star_sources"]:
+            star_imports.append((exporter, source, allowed))
+
+    star_winners: dict[tuple[str, str], str] = {}
+    changed = True
+    while changed:
+        changed = False
+        for exporter, source, allowed in star_imports:
+            for local, target in tuple(working_surfaces.get(source, {}).items()):
+                if allowed is not None and local not in allowed:
+                    continue
+                if allowed is None and local.startswith("_"):
+                    continue
+                # A named binding owns its namespace slot even when it is a
+                # self-binding and therefore did not create a binding edge.
+                if local in direct_bindings.get(exporter, {}):
+                    continue
+                winner_key = (exporter, local)
+                if winner_key in star_winners:
+                    continue
+                working_surfaces.setdefault(exporter, {})[local] = target
+                star_winners[winner_key] = source
+                changed = True
+
+    for exporter, visible_bindings in module_export_surfaces.items():
+        facts = facts_by_exporter.get(exporter)
+        if facts is None:
+            continue
+        bindings = facts["bindings"]
+        assert isinstance(bindings, Mapping)
+        for local in visible_bindings:
+            if local in bindings:
+                continue
+            source = star_winners.get((exporter, local))
+            if source is None:
+                continue
+            install(
+                ReexportLineageHop(
+                    source=f"{exporter}::{local}",
+                    target=f"{source}::{local}",
+                    kind="star",
+                )
+            )
+
+    return dict(sorted(alias_index.items()))
+
+
+def resolve_reexport_lineage_alias(
+    query: str,
+    alias_index: Mapping[str, ReexportLineageHop],
+    modules,
+) -> ReexportLineageResolution:
+    if not isinstance(query, str):
+        raise TypeError("query must be a string.")
+    if not isinstance(alias_index, Mapping):
+        raise TypeError("alias_index must be a mapping.")
+    if not isinstance(modules, Mapping):
+        raise TypeError("modules must be a mapping.")
+
+    original = query.strip()
+    if original not in alias_index:
+        return ReexportLineageResolution(
+            status="not_alias",
+            query=original,
+        )
+
+    hops: list[ReexportLineageHop] = []
+    visited: set[str] = set()
+    current = original
+    while True:
+        if current in visited:
+            return ReexportLineageResolution(
+                status="cycle",
+                query=original,
+                hops=tuple(hops),
+                reason="reexport_cycle",
+            )
+        visited.add(current)
+        hop = alias_index.get(current)
+        if hop is None:
+            canonical_target = canonicalize_lineage_qualified_identity(
+                current,
+                modules,
+            )
+            if canonical_target.count("::") != 1:
+                return ReexportLineageResolution(
+                    status="unresolved",
+                    query=original,
+                    hops=tuple(hops),
+                    reason="target_outside_repository",
+                )
+            module_name = canonical_target.split("::", 1)[0]
+            if module_name not in modules:
+                return ReexportLineageResolution(
+                    status="unresolved",
+                    query=original,
+                    hops=tuple(hops),
+                    reason="target_outside_repository",
+                )
+            return ReexportLineageResolution(
+                status="resolved",
+                query=original,
+                canonical_target=canonical_target,
+                hops=tuple(hops),
+            )
+
+        if hop.target in alias_index:
+            # Keep a package façade alias in its re-export identity form long
+            # enough to follow the next edge. Canonicalizing it to
+            # pkg.__init__::name here would skip the alias-index key pkg::name.
+            canonical_target = hop.target
+        else:
+            canonical_target = canonicalize_lineage_qualified_identity(
+                hop.target,
+                modules,
+            )
+            if canonical_target.count("::") != 1:
+                return ReexportLineageResolution(
+                    status="unresolved",
+                    query=original,
+                    hops=tuple(hops),
+                    reason="target_outside_repository",
+                )
+            module_name = canonical_target.split("::", 1)[0]
+            if module_name not in modules:
+                return ReexportLineageResolution(
+                    status="unresolved",
+                    query=original,
+                    hops=tuple(hops),
+                    reason="target_outside_repository",
+                )
+
+        resolved_hop = ReexportLineageHop(
+            source=current,
+            target=canonical_target,
+            kind=hop.kind,
+        )
+        hops.append(resolved_hop)
+        if canonical_target in visited:
+            return ReexportLineageResolution(
+                status="cycle",
+                query=original,
+                hops=tuple(hops),
+                reason="reexport_cycle",
+            )
+        current = canonical_target
 
 
 def lineage_owner_ids_for_source(
diff --git a/contextor/core/lineage_query/live_query.py b/contextor/core/lineage_query/live_query.py
index b34a5c1..793f54b 100644
--- a/contextor/core/lineage_query/live_query.py
+++ b/contextor/core/lineage_query/live_query.py
@@ -1,6 +1,6 @@
 from __future__ import annotations
 
-from dataclasses import dataclass, field
+from dataclasses import dataclass, field, replace
 from collections.abc import Mapping
 
 from contextor.core.analysis.state_manager import (
@@ -9,6 +9,9 @@ from contextor.core.analysis.state_manager import (
 from contextor.core.lineage_query.backend import (
     RepositoryStateLineageBackend,
 )
+from contextor.core.lineage_query.index import (
+    ReexportLineageResolution,
+)
 from contextor.core.domain.lineage_facts import (
     ExtractedSymbolicKind,
     SemanticEndpoint,
@@ -48,6 +51,7 @@ class LiveSymbolLineageQueryResult:
     unavailable_reason: str | None = None
     owner_names: dict[str, str] = field(default_factory=dict)
     state_freshness: dict[str, object] = field(default_factory=dict)
+    reexport_chain: ReexportLineageResolution | None = None
 
 
 def _selected_lineage_flow_matches(
@@ -472,6 +476,7 @@ def query_live_symbol_lineage(
     if not isinstance(query, str):
         raise TypeError("query must be a string.")
 
+    raw_query = query.strip()
     canonical_sections = (
         _canonical_lineage_sections(sections)
     )
@@ -480,10 +485,13 @@ def query_live_symbol_lineage(
     )
 
     try:
+        canonical_query = backend.canonicalize_qualified_identity(
+            raw_query
+        )
         catalog = build_live_lineage_target_catalog(
             state,
             backend,
-            query,
+            canonical_query,
         )
     except ValueError as exc:
         if str(exc) != _UNAVAILABLE_MESSAGE:
@@ -491,7 +499,7 @@ def query_live_symbol_lineage(
         return LiveSymbolLineageQueryResult(
             resolution=LineageTargetResolution(
                 status="unavailable",
-                query=query.strip(),
+                query=raw_query,
             ),
             unavailable_reason=str(exc),
             state_freshness=(
@@ -507,9 +515,134 @@ def query_live_symbol_lineage(
         catalog,
     )
     resolution = service.resolve_target(
-        query
+        canonical_query
     )
 
+    reexport_chain: ReexportLineageResolution | None = None
+    if resolution.status == "resolved" and resolution.target is not None:
+        if canonical_query != raw_query:
+            package_target = replace(
+                resolution.target,
+                resolution="package_alias",
+            )
+            resolution = LineageTargetResolution(
+                status="resolved",
+                query=raw_query,
+                target=package_target,
+            )
+    elif resolution.status == "not_found" and raw_query.count("::") == 1:
+        try:
+            reexport_chain = backend.resolve_reexport_alias(
+                raw_query
+            )
+        except ValueError as exc:
+            if str(exc) != (
+                "Canonical re-export facts are unavailable or incomplete."
+            ):
+                raise
+            return LiveSymbolLineageQueryResult(
+                resolution=LineageTargetResolution(
+                    status="unavailable",
+                    query=raw_query,
+                ),
+                unavailable_reason=str(exc),
+                state_freshness=(
+                    build_live_lineage_state_freshness(
+                        state,
+                        backend,
+                    )
+                ),
+            )
+
+        if reexport_chain.status == "not_alias":
+            reexport_chain = None
+            resolution = LineageTargetResolution(
+                status="not_found",
+                query=raw_query,
+            )
+        elif reexport_chain.status in {"cycle", "unresolved"}:
+            return LiveSymbolLineageQueryResult(
+                resolution=LineageTargetResolution(
+                    status="unresolved",
+                    query=raw_query,
+                ),
+                state_freshness=(
+                    build_live_lineage_state_freshness(
+                        state,
+                        backend,
+                    )
+                ),
+                reexport_chain=reexport_chain,
+            )
+        elif reexport_chain.status == "resolved":
+            assert reexport_chain.canonical_target is not None
+            try:
+                origin_catalog = build_live_lineage_target_catalog(
+                    state,
+                    backend,
+                    reexport_chain.canonical_target,
+                )
+            except ValueError as exc:
+                if str(exc) != _UNAVAILABLE_MESSAGE:
+                    raise
+                origin_catalog = None
+
+            if origin_catalog is None:
+                return LiveSymbolLineageQueryResult(
+                    resolution=LineageTargetResolution(
+                        status="unavailable",
+                        query=raw_query,
+                    ),
+                    unavailable_reason=(
+                        "Canonical re-export origin has no available lineage owner."
+                    ),
+                    state_freshness=(
+                        build_live_lineage_state_freshness(
+                            state,
+                            backend,
+                        )
+                    ),
+                    reexport_chain=reexport_chain,
+                )
+
+            origin_service = LineageQueryService(
+                backend,
+                origin_catalog,
+            )
+            origin_resolution = origin_service.resolve_target(
+                reexport_chain.canonical_target
+            )
+            if (
+                origin_resolution.status != "resolved"
+                or origin_resolution.target is None
+            ):
+                return LiveSymbolLineageQueryResult(
+                    resolution=LineageTargetResolution(
+                        status="unavailable",
+                        query=raw_query,
+                    ),
+                    unavailable_reason=(
+                        "Canonical re-export origin has no available lineage owner."
+                    ),
+                    state_freshness=(
+                        build_live_lineage_state_freshness(
+                            state,
+                            backend,
+                        )
+                    ),
+                    reexport_chain=reexport_chain,
+                )
+
+            resolution = LineageTargetResolution(
+                status="resolved",
+                query=raw_query,
+                target=replace(
+                    origin_resolution.target,
+                    resolution="reexport_alias",
+                ),
+            )
+            service = origin_service
+
     if (
         resolution.status != "resolved"
         or resolution.target is None
@@ -548,4 +681,5 @@ def query_live_symbol_lineage(
         selected=selected,
         owner_names=owner_names,
         state_freshness=state_freshness,
+        reexport_chain=reexport_chain,
     )
diff --git a/contextor/mcp/docs/get_symbol_lineage.json b/contextor/mcp/docs/get_symbol_lineage.json
index a94852e..2b5a78c 100644
--- a/contextor/mcp/docs/get_symbol_lineage.json
+++ b/contextor/mcp/docs/get_symbol_lineage.json
@@ -6,7 +6,7 @@
   ],
   "parameters": [
     "repo_path (string, required): canonical repository root.",
-    "symbol (string, required): active artifact ID or exact module::symbol identity; plain leaves and fuzzy identities are not accepted.",
+    "symbol (string, required): active artifact ID, exact canonical module::symbol identity, exact package façade module::symbol identity, or exact canonical re-export alias module::symbol identity; plain leaves and fuzzy identities are not accepted.",
     "mode (auto|preview|fetch, default \"auto\"): progressive disclosure mode. auto evaluates all canonical lineage sections and returns the complete represented payload only when it fits the 5120-byte auto threshold; preview returns section costs without section payloads; fetch requires an explicit non-empty sections list.",
     "sections (array or null, default null): explicit semantic sections for fetch mode only. Valid names are interface, connections, bindings, parameter_flows, calls_interfaces, returns, state, callbacks, surfaces, and unresolved_dynamic_boundaries.",
     "representation (named|indexed|auto, default \"auto\"): semantic-owner identity representation. named uses canonical module/artifact names when available; indexed retains canonical owner IDs; auto applies exact serialized-size negotiation.",
@@ -19,6 +19,8 @@
     "Semantic sections are selected before transport. auto and preview request the complete canonical section set; fetch sends only the requested sections in canonical section order.",
     "Sections describe the target interface, direct cross-source connections, bindings, parameter flows, calls/interfaces, returns, state access, callbacks, surfaces, and unresolved/dynamic boundaries. get_symbol_lineage does not perform recursive lineage traversal.",
     "Representation applies only to canonical SemanticEndpoint owners. Semantic owners may be module IDs or artifact IDs. Indexed output exposes lookup_index_entries as the resolver for both ID kinds; occurrence and symbolic endpoint identities are not rewritten.",
+    "When an exact re-export alias resolves, the canonical target and semantic sections describe the real origin owner. An optional top-level reexport_chain reports the query identity and each immediate binding or star hop; it is not included in sections or semantic-owner representation conversion.",
+    "A re-export cycle or target outside the repository returns status=unresolved with error=reexport_cycle or error=target_outside_repository and an explanatory reexport_chain.",
     "auto selects indexed representation only when named identities are unavailable or indexed output saves at least 512 serialized bytes; otherwise it emits named output.",
     "For mode=auto, a represented complete candidate above 5120 UTF-8 bytes becomes a representation-aware preview before the general large-output guard runs. A candidate exactly at 5120 bytes may be returned.",
     "The selected final response uses the shared 15360-byte output guard. Explicit fetch above that threshold requires allow_large_output=true.",
@@ -32,6 +34,7 @@
   ],
   "errors": [
     "Invalid mode, section selection, representation, allow_large_output, repository path, or symbol shape returns a controlled error response before lineage execution where applicable.",
+    "Re-export alias cycles and targets that cannot be mapped to a real repository module return status=unresolved; error is reexport_cycle or target_outside_repository, respectively, and reexport_chain carries the attempted alias path.",
     "canonical_live_unavailable means no verified running LIVE authority exists; the tool does not start one automatically.",
     "canonical_live_transport_error and canonical_query_transport_error report authority/IPC transport failure without snapshot fallback.",
     "canonical_query_response_invalid and canonical_query_revision_mismatch fail closed on malformed or cross-revision narrow responses.",
diff --git a/contextor/mcp/lineage_response.py b/contextor/mcp/lineage_response.py
index 30a9ac5..c9bfc43 100644
--- a/contextor/mcp/lineage_response.py
+++ b/contextor/mcp/lineage_response.py
@@ -5,6 +5,7 @@ from dataclasses import dataclass
 from collections.abc import Mapping
 
 from contextor.core.domain.lineage_facts import MaterializedOccurrenceRef, MaterializedSymbolicRef, SemanticEndpoint
+from contextor.core.lineage_query.index import ReexportLineageResolution
 from contextor.core.lineage_query.service import (
     SYMBOL_LINEAGE_SECTION_ORDER,
     LineageFlowMatch, LineageSurfaceMatch, SelectedSymbolLineageFacts, TargetInterfaceFacts,
@@ -114,6 +115,7 @@ def build_symbol_lineage_payload(
     selected: SelectedSymbolLineageFacts,
     *,
     state_freshness: Mapping[str, object] | None = None,
+    reexport_chain: ReexportLineageResolution | None = None,
 ) -> dict:
     if not isinstance(
         selected,
@@ -158,17 +160,46 @@ def build_symbol_lineage_payload(
     result["sections"] = _section_payloads(
         selected
     )
+    if reexport_chain is not None:
+        result["reexport_chain"] = build_reexport_lineage_payload(
+            reexport_chain
+        )
     return result
 
 
+def build_reexport_lineage_payload(
+    resolution: ReexportLineageResolution,
+) -> dict:
+    if not isinstance(resolution, ReexportLineageResolution):
+        raise TypeError("resolution must be ReexportLineageResolution.")
+    payload = {
+        "status": resolution.status,
+        "query": resolution.query,
+        "canonical_target": resolution.canonical_target,
+        "hops": [
+            {
+                "source": hop.source,
+                "target": hop.target,
+                "kind": hop.kind,
+            }
+            for hop in resolution.hops
+        ],
+    }
+    if resolution.reason is not None:
+        payload["reason"] = resolution.reason
+    return payload
+
+
 def build_symbol_lineage_preview(
     selected: SelectedSymbolLineageFacts,
     *,
     state_freshness: Mapping[str, object] | None = None,
+    reexport_chain: ReexportLineageResolution | None = None,
 ) -> dict:
     payload = build_symbol_lineage_payload(
         selected,
         state_freshness=state_freshness,
+        reexport_chain=reexport_chain,
     )
     result = {
         "status": "resolved",
@@ -203,6 +234,10 @@ def build_symbol_lineage_preview(
         result["state_freshness"] = payload[
             "state_freshness"
         ]
+    if "reexport_chain" in payload:
+        result["reexport_chain"] = payload[
+            "reexport_chain"
+        ]
     return result
 
 
@@ -234,6 +269,7 @@ def build_symbol_lineage_represented_payload(
     representation: str = "auto",
     owner_names: Mapping[str, str] | None = None,
     state_freshness: Mapping[str, object] | None = None,
+    reexport_chain: ReexportLineageResolution | None = None,
 ) -> dict:
     if not isinstance(selected, SelectedSymbolLineageFacts): raise TypeError("selected must be SelectedSymbolLineageFacts.")
     if not isinstance(representation, str): raise TypeError("representation must be a string.")
@@ -245,6 +281,7 @@ def build_symbol_lineage_represented_payload(
     base = build_symbol_lineage_payload(
         selected,
         state_freshness=state_freshness,
+        reexport_chain=reexport_chain,
     )
     missing = tuple(owner for owner in _semantic_owner_ids(base) if owner_names is None or owner not in owner_names)
     indexed = dict(base); indexed.update({"representation": "indexed", "requested_representation": requested, "resolver": {"id_kinds": ["module", "artifact"], "resolve_via": "lookup_index_entries"}})
@@ -274,12 +311,14 @@ def _represented_response_candidate(
     representation: str,
     owner_names: Mapping[str, str] | None,
     state_freshness: Mapping[str, object] | None,
+    reexport_chain: ReexportLineageResolution | None,
 ) -> dict:
     result = build_symbol_lineage_represented_payload(
         selected,
         representation=representation,
         owner_names=owner_names,
         state_freshness=state_freshness,
+        reexport_chain=reexport_chain,
     )
     result["mode"] = mode
     return result
@@ -292,6 +331,7 @@ def build_symbol_lineage_represented_preview(
     owner_names: Mapping[str, str] | None = None,
     state_freshness: Mapping[str, object] | None = None,
     candidate_mode: str = "fetch",
+    reexport_chain: ReexportLineageResolution | None = None,
 ) -> dict:
     if candidate_mode not in {"auto", "fetch"}:
         raise ValueError(
@@ -304,6 +344,7 @@ def build_symbol_lineage_represented_preview(
         representation=representation,
         owner_names=owner_names,
         state_freshness=state_freshness,
+        reexport_chain=reexport_chain,
     )
     sections = candidate["sections"]
 
@@ -350,6 +391,11 @@ def build_symbol_lineage_represented_preview(
             "state_freshness"
         ]
 
+    if "reexport_chain" in candidate:
+        result["reexport_chain"] = candidate[
+            "reexport_chain"
+        ]
+
     if "resolver" in candidate:
         result["resolver"] = candidate["resolver"]
 
@@ -365,6 +411,7 @@ def render_symbol_lineage_response(
     owner_names: Mapping[str, str] | None = None,
     state_freshness: Mapping[str, object] | None = None,
     allow_large_output: bool = False,
+    reexport_chain: ReexportLineageResolution | None = None,
 ) -> str:
     if not isinstance(
         selected,
@@ -399,6 +446,7 @@ def render_symbol_lineage_response(
             owner_names=owner_names,
             state_freshness=state_freshness,
             candidate_mode="fetch",
+            reexport_chain=reexport_chain,
         )
         serialized = json.dumps(
             result,
@@ -425,6 +473,7 @@ def render_symbol_lineage_response(
         representation=representation,
         owner_names=owner_names,
         state_freshness=state_freshness,
+        reexport_chain=reexport_chain,
     )
     candidate_bytes = (
         mcp_rep.serialized_json_bytes(
@@ -444,6 +493,7 @@ def render_symbol_lineage_response(
                 owner_names=owner_names,
                 state_freshness=state_freshness,
                 candidate_mode="auto",
+                reexport_chain=reexport_chain,
             )
         )
         preview["auto_fetch"] = {
diff --git a/contextor/mcp/tools/get_symbol_lineage.py b/contextor/mcp/tools/get_symbol_lineage.py
index 7a1e171..1ac32fb 100644
--- a/contextor/mcp/tools/get_symbol_lineage.py
+++ b/contextor/mcp/tools/get_symbol_lineage.py
@@ -3,6 +3,7 @@ from __future__ import annotations
 import json
 from pathlib import Path
 
+from contextor.core.lineage_query.index import ReexportLineageResolution
 from contextor.core.lineage_query.service import (
     LineageTargetResolution,
     ResolvedLineageTarget,
@@ -10,6 +11,7 @@ from contextor.core.lineage_query.service import (
 from contextor.mcp import representation as mcp_rep
 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp.lineage_response import (
+    build_reexport_lineage_payload,
     plan_symbol_lineage_response,
     render_symbol_lineage_response,
 )
@@ -38,6 +40,7 @@ def _resolution_response(
     *,
     state_freshness: dict[str, object],
     unavailable_reason: str | None = None,
+    reexport_chain: ReexportLineageResolution | None = None,
 ) -> str:
     if resolution.status == "unavailable":
         return json.dumps(
@@ -68,6 +71,20 @@ def _resolution_response(
             indent=2,
             ensure_ascii=False,
         )
+    if resolution.status == "unresolved" and reexport_chain is not None:
+        return json.dumps(
+            {
+                "status": "unresolved",
+                "symbol": resolution.query,
+                "error": reexport_chain.reason,
+                "reexport_chain": build_reexport_lineage_payload(
+                    reexport_chain
+                ),
+                "state_freshness": state_freshness,
+            },
+            indent=2,
+            ensure_ascii=False,
+        )
     if resolution.status == "ambiguous":
         return json.dumps(
             {
@@ -148,6 +165,7 @@ def get_symbol_lineage(
             resolution,
             state_freshness=result.state_freshness,
             unavailable_reason=result.unavailable_reason,
+            reexport_chain=result.reexport_chain,
         )
     if result.selected is None:
         return _error(
@@ -155,14 +173,19 @@ def get_symbol_lineage(
             message="Resolved lineage target returned no selected facts.",
         )
     try:
+        render_kwargs = {
+            "mode": plan.mode,
+            "sections": requested_sections,
+            "representation": normalized_representation,
+            "owner_names": result.owner_names,
+            "state_freshness": result.state_freshness,
+            "allow_large_output": allow_large_output,
+        }
+        if result.reexport_chain is not None:
+            render_kwargs["reexport_chain"] = result.reexport_chain
         return render_symbol_lineage_response(
             result.selected,
-            mode=plan.mode,
-            sections=requested_sections,
-            representation=normalized_representation,
-            owner_names=result.owner_names,
-            state_freshness=result.state_freshness,
-            allow_large_output=allow_large_output,
+            **render_kwargs,
         )
     except (TypeError, ValueError) as exc:
         return _error("lineage_response_failed", message=str(exc))
diff --git a/tests/analysis/test_lineage_live_query.py b/tests/analysis/test_lineage_live_query.py
index 5c75f4f..b1060af 100644
--- a/tests/analysis/test_lineage_live_query.py
+++ b/tests/analysis/test_lineage_live_query.py
@@ -1,5 +1,7 @@
 from dataclasses import replace
 from types import SimpleNamespace
+from pathlib import Path
+from unittest.mock import patch
 
 import pytest
 
@@ -21,6 +23,7 @@ from contextor.core.domain.lineage_facts import (
     SourceSpan,
     build_module_global_slot,
 )
+from contextor.core.domain.module import Module
 from contextor.core.lineage_query.backend import (
     RepositoryStateLineageBackend,
 )
@@ -143,6 +146,20 @@ def _fixture():
         lineage_semantic_anchor_bindings_complete=(
             anchor_complete
         ),
+        reexport_facts_by_module={
+            "pkg.mod": {
+                "exporter": "pkg.mod",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            },
+            "pkg.other": {
+                "exporter": "pkg.other",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            },
+        },
     )
     return (
         state,
@@ -150,6 +167,45 @@ def _fixture():
     )
 
 
+def _reexport_query_fixture(module_paths, reexport_facts, definitions):
+    modules = {
+        module_id: Module(
+            module_id,
+            path,
+            str(Path(path).resolve()),
+            [],
+        )
+        for module_id, path in module_paths.items()
+    }
+    sources = {
+        path: _source(
+            path,
+            f"{index + 1:064x}",
+            definitions.get(module_id, ()),
+        )
+        for index, (module_id, path) in enumerate(module_paths.items())
+    }
+    (
+        owner_source_index,
+        source_owner_index,
+        anchor_complete,
+    ) = build_lineage_query_indexes(sources)
+    state = SimpleNamespace(
+        revision=19,
+        provenance="live",
+        modules=modules,
+        reexport_facts_by_module=reexport_facts,
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version="1",
+        lineage_facts_by_source=sources,
+        lineage_owner_source_index=owner_source_index,
+        lineage_source_owner_index=source_owner_index,
+        lineage_query_index_state="fresh",
+        lineage_semantic_anchor_bindings_complete=anchor_complete,
+    )
+    return state
+
+
 def test_live_target_catalog_resolves_artifact_id_only_through_owner_index(
     monkeypatch,
 ):
@@ -475,6 +531,319 @@ def test_live_symbol_lineage_query_resolves_exact_qualified_identity():
     )
 
 
+def test_live_symbol_lineage_query_resolves_reexports_without_source_io(
+    monkeypatch,
+):
+    module_paths = {
+        "a": "a.py",
+        "b": "b.py",
+        "c": "c.py",
+        "d": "d.py",
+        "pkg.__init__": "pkg/__init__.py",
+        "pkg.provider": "pkg/provider.py",
+        "star_src": "star_src.py",
+        "star_src_second": "star_src_second.py",
+        "star_mid": "star_mid.py",
+        "star_dst": "star_dst.py",
+        "direct_src": "direct_src.py",
+        "direct_dst": "direct_dst.py",
+        "direct_override": "direct_override.py",
+        "cycle_a": "cycle_a.py",
+        "cycle_b": "cycle_b.py",
+        "external_dst": "external_dst.py",
+    }
+
+    def facts(exporter, *, bindings=None, explicit_all=None, star_sources=()):
+        return {
+            "exporter": exporter,
+            "explicit_all": explicit_all,
+            "bindings": {} if bindings is None else bindings,
+            "star_sources": list(star_sources),
+        }
+
+    reexport_facts = {
+        "a": facts("a", bindings={"foo": "a.foo"}),
+        "b": facts("b", bindings={"public_foo": "a.foo"}),
+        "c": facts("c", bindings={"exported": "b.public_foo"}),
+        "d": facts("d", bindings={"exported_run": "pkg.public_run"}),
+        "pkg.__init__": facts(
+            "pkg",
+            bindings={
+                "LOCAL": "pkg.LOCAL",
+                "public_run": "pkg.provider.run",
+            },
+            explicit_all=["public_run"],
+        ),
+        "pkg.provider": facts(
+            "pkg.provider",
+            bindings={"run": "pkg.provider.run"},
+        ),
+        "star_src": facts(
+            "star_src",
+            bindings={
+                "visible": "star_src.visible",
+                "_hidden": "star_src._hidden",
+                "shared": "star_src.shared",
+            },
+            explicit_all=["visible", "shared"],
+        ),
+        "star_src_second": facts(
+            "star_src_second",
+            bindings={"shared": "star_src_second.shared"},
+            explicit_all=["shared"],
+        ),
+        "star_mid": facts(
+            "star_mid",
+            star_sources=["star_src", "star_src_second"],
+        ),
+        "star_dst": facts("star_dst", star_sources=["star_mid"]),
+        "direct_src": facts(
+            "direct_src",
+            bindings={"foo": "direct_src.foo"},
+        ),
+        "direct_dst": facts(
+            "direct_dst",
+            bindings={"hidden": "direct_src.foo"},
+            explicit_all=[],
+        ),
+        "direct_override": facts(
+            "direct_override",
+            bindings={"visible": "a.foo"},
+            explicit_all=["visible"],
+            star_sources=["star_src"],
+        ),
+        "cycle_a": facts(
+            "cycle_a",
+            bindings={"value": "cycle_b.value"},
+            explicit_all=["value"],
+        ),
+        "cycle_b": facts(
+            "cycle_b",
+            bindings={"value": "cycle_a.value"},
+            explicit_all=["value"],
+        ),
+        "external_dst": facts(
+            "external_dst",
+            bindings={"public": "thirdparty.api.foo"},
+        ),
+    }
+    definitions = {
+        "a": (("A1/1", "a::foo"),),
+        "pkg.__init__": (("A2/1", "pkg.__init__::LOCAL"),),
+        "pkg.provider": (("A3/1", "pkg.provider::run"),),
+        "star_src": (
+            ("A4/1", "star_src::visible"),
+            ("A4/2", "star_src::_hidden"),
+            ("A4/3", "star_src::shared"),
+        ),
+        "star_src_second": (("A6/1", "star_src_second::shared"),),
+        "direct_src": (("A5/1", "direct_src::foo"),),
+    }
+    state = _reexport_query_fixture(
+        module_paths,
+        reexport_facts,
+        definitions,
+    )
+    missing_origin_state = _reexport_query_fixture(
+        module_paths,
+        reexport_facts,
+        definitions={
+            key: value
+            for key, value in definitions.items()
+            if key != "a"
+        },
+    )
+
+    import contextor.core.domain.module as module_domain
+
+    def fail_source_access(*_args, **_kwargs):
+        raise AssertionError("re-export lineage query accessed source or AST")
+
+    with (
+        patch.object(
+            Module,
+            "ast_tree",
+            new=property(fail_source_access),
+        ),
+        patch.object(
+            module_domain,
+            "_get_cached_ast",
+            side_effect=fail_source_access,
+        ),
+        patch.object(
+            Path,
+            "open",
+            side_effect=fail_source_access,
+        ),
+    ):
+        multi_hop = query_live_symbol_lineage(
+            state,
+            "c::exported",
+            ("interface",),
+        )
+        one_hop = query_live_symbol_lineage(
+            state,
+            "b::public_foo",
+            ("interface",),
+        )
+        package_alias = query_live_symbol_lineage(
+            state,
+            "pkg::public_run",
+            ("interface",),
+        )
+        package_alias_chain = query_live_symbol_lineage(
+            state,
+            "d::exported_run",
+            ("interface",),
+        )
+        package_local = query_live_symbol_lineage(
+            state,
+            "pkg::LOCAL",
+            ("interface",),
+        )
+        star_alias = query_live_symbol_lineage(
+            state,
+            "star_dst::visible",
+            ("interface",),
+        )
+        star_private = query_live_symbol_lineage(
+            state,
+            "star_dst::_hidden",
+            ("interface",),
+        )
+        star_multiple = query_live_symbol_lineage(
+            state,
+            "star_dst::shared",
+            ("interface",),
+        )
+        direct_alias = query_live_symbol_lineage(
+            state,
+            "direct_dst::hidden",
+            ("interface",),
+        )
+        direct_override = query_live_symbol_lineage(
+            state,
+            "direct_override::visible",
+            ("interface",),
+        )
+        cycle = query_live_symbol_lineage(
+            state,
+            "cycle_a::value",
+            ("interface",),
+        )
+        external = query_live_symbol_lineage(
+            state,
+            "external_dst::public",
+            ("interface",),
+        )
+        missing_origin = query_live_symbol_lineage(
+            missing_origin_state,
+            "c::exported",
+            ("interface",),
+        )
+
+    assert multi_hop.resolution.status == "resolved"
+    assert multi_hop.resolution.target is not None
+    assert multi_hop.resolution.target.qualified_name == "a::foo"
+    assert multi_hop.resolution.target.resolution == "reexport_alias"
+    assert multi_hop.resolution.target.artifact_id == "A1/1"
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in multi_hop.reexport_chain.hops
+    ] == [
+        ("c::exported", "b::public_foo", "binding"),
+        ("b::public_foo", "a::foo", "binding"),
+    ]
+
+    assert one_hop.resolution.target is not None
+    assert one_hop.resolution.target.qualified_name == "a::foo"
+    assert len(one_hop.reexport_chain.hops) == 1
+
+    assert package_alias.resolution.target is not None
+    assert package_alias.resolution.target.qualified_name == (
+        "pkg.provider::run"
+    )
+    assert package_alias.resolution.target.resolution == "reexport_alias"
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in package_alias.reexport_chain.hops
+    ] == [("pkg::public_run", "pkg.provider::run", "binding")]
+    assert package_alias_chain.resolution.target is not None
+    assert package_alias_chain.resolution.target.qualified_name == (
+        "pkg.provider::run"
+    )
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in package_alias_chain.reexport_chain.hops
+    ] == [
+        ("d::exported_run", "pkg::public_run", "binding"),
+        ("pkg::public_run", "pkg.provider::run", "binding"),
+    ]
+
+    assert package_local.resolution.target is not None
+    assert package_local.resolution.target.qualified_name == (
+        "pkg.__init__::LOCAL"
+    )
+    assert package_local.resolution.target.resolution == "package_alias"
+    assert package_local.reexport_chain is None
+
+    assert star_alias.resolution.target is not None
+    assert star_alias.resolution.target.qualified_name == (
+        "star_src::visible"
+    )
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in star_alias.reexport_chain.hops
+    ] == [
+        ("star_dst::visible", "star_mid::visible", "star"),
+        ("star_mid::visible", "star_src::visible", "star"),
+    ]
+    assert star_private.resolution.status == "not_found"
+    assert star_private.reexport_chain is None
+    assert star_multiple.resolution.target is not None
+    assert star_multiple.resolution.target.qualified_name == (
+        "star_src::shared"
+    )
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in star_multiple.reexport_chain.hops
+    ] == [
+        ("star_dst::shared", "star_mid::shared", "star"),
+        ("star_mid::shared", "star_src::shared", "star"),
+    ]
+
+    assert direct_alias.resolution.target is not None
+    assert direct_alias.resolution.target.qualified_name == (
+        "direct_src::foo"
+    )
+    assert direct_alias.reexport_chain.hops[0].kind == "binding"
+    assert direct_override.resolution.target is not None
+    assert direct_override.resolution.target.qualified_name == "a::foo"
+    assert direct_override.reexport_chain.hops[0].kind == "binding"
+
+    assert cycle.resolution.status == "unresolved"
+    assert cycle.selected is None
+    assert cycle.reexport_chain.status == "cycle"
+    assert cycle.reexport_chain.reason == "reexport_cycle"
+    assert cycle.reexport_chain.canonical_target is None
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in cycle.reexport_chain.hops
+    ] == [
+        ("cycle_a::value", "cycle_b::value", "binding"),
+        ("cycle_b::value", "cycle_a::value", "binding"),
+    ]
+    assert external.resolution.status == "unresolved"
+    assert external.reexport_chain.status == "unresolved"
+    assert external.reexport_chain.reason == "target_outside_repository"
+    assert external.reexport_chain.canonical_target is None
+
+    assert missing_origin.resolution.status == "unavailable"
+    assert missing_origin.unavailable_reason == (
+        "Canonical re-export origin has no available lineage owner."
+    )
+
+
 @pytest.mark.parametrize(
     ("query", "expected_status"),
     (
diff --git a/tests/analysis/test_lineage_query_backend.py b/tests/analysis/test_lineage_query_backend.py
index 8d524df..ba646c1 100644
--- a/tests/analysis/test_lineage_query_backend.py
+++ b/tests/analysis/test_lineage_query_backend.py
@@ -13,6 +13,7 @@ from contextor.core.lineage_query import (
     LineageBackendMetadata,
     RepositoryStateLineageBackend,
 )
+from contextor.core.lineage_query import backend as backend_module
 
 
 def _slice(source_key: str) -> MaterializedLineageSourceFacts:
@@ -69,6 +70,74 @@ def test_repository_state_backend_exposes_canonical_metadata():
     )
 
 
+def test_repository_state_backend_builds_reexport_alias_index_lazily(
+    monkeypatch,
+):
+    modules = {
+        "pkg.a": SimpleNamespace(path="pkg/a.py"),
+        "pkg.b": SimpleNamespace(path="pkg/b.py"),
+    }
+    reexport_facts = {
+        "pkg.a": {
+            "exporter": "pkg.a",
+            "explicit_all": None,
+            "bindings": {"foo": "pkg.a.foo"},
+            "star_sources": [],
+        },
+        "pkg.b": {
+            "exporter": "pkg.b",
+            "explicit_all": None,
+            "bindings": {"public": "pkg.a.foo"},
+            "star_sources": [],
+        },
+    }
+    state = SimpleNamespace(
+        **{
+            **vars(_state()[0]),
+            "modules": modules,
+            "reexport_facts_by_module": reexport_facts,
+        }
+    )
+    backend = RepositoryStateLineageBackend(state)
+    assert backend._modules is modules
+    assert backend._reexport_facts_by_module is reexport_facts
+    assert backend._reexport_alias_index is None
+
+    original_builder = backend_module.build_reexport_lineage_alias_index
+    builds = []
+
+    def build_spy(facts):
+        builds.append(facts)
+        return original_builder(facts)
+
+    monkeypatch.setattr(
+        backend_module,
+        "build_reexport_lineage_alias_index",
+        build_spy,
+    )
+    first = backend.resolve_reexport_alias("pkg.b::public")
+    second = backend.resolve_reexport_alias("pkg.b::public")
+
+    assert first == second
+    assert first.status == "resolved"
+    assert first.canonical_target == "pkg.a::foo"
+    assert len(first.hops) == 1
+    assert builds == [reexport_facts]
+
+
+def test_repository_state_backend_reexport_alias_resolution_fails_closed():
+    state, _, _ = _state()
+    state.modules = {"pkg.a": SimpleNamespace(path="pkg/a.py")}
+    state.reexport_facts_by_module = {}
+    backend = RepositoryStateLineageBackend(state)
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical re-export facts are unavailable or incomplete",
+    ):
+        backend.resolve_reexport_alias("pkg.a::missing")
+
+
 def test_repository_state_backend_preserves_slice_identity_and_order():
     state, source_a, source_b = _state()
     backend = RepositoryStateLineageBackend(state)
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
index b64426c..ddcb207 100644
--- a/tests/mcp/test_lineage_response.py
+++ b/tests/mcp/test_lineage_response.py
@@ -12,6 +12,10 @@ from contextor.core.domain.lineage_facts import (
     build_parameter_value_slot, build_return_slot, build_module_global_slot, ParameterKind,
 )
 from contextor.core.lineage_query.backend import LineageBackendMetadata
+from contextor.core.lineage_query.index import (
+    ReexportLineageHop,
+    ReexportLineageResolution,
+)
 from contextor.core.lineage_query.service import (
     SYMBOL_LINEAGE_SECTION_ORDER, DirectLineageFacts, LexicalScopeFacts,
     LineageAnchorMatch, LineageFlowMatch, LineageInterfaceDescriptorMatch, LineageSurfaceMatch,
@@ -605,7 +609,7 @@ def test_symbol_lineage_renderer_fails_closed_on_selection_plan_mismatch():
         render_symbol_lineage_response(
             selected,
             mode="fetch",
-            sections=("interface",),
+            sections=SYMBOL_LINEAGE_SECTION_ORDER,
             representation="indexed",
         )
 
@@ -742,6 +746,151 @@ def test_symbol_lineage_represented_preview_sizes_candidate_with_freshness():
     )
 
 
+def test_reexport_chain_is_top_level_and_representation_independent():
+    selected = _selected_lineage_fixture()
+    chain = ReexportLineageResolution(
+        status="resolved",
+        query="c::exported",
+        canonical_target="a::foo",
+        hops=(
+            ReexportLineageHop(
+                "c::exported",
+                "b::public_foo",
+                "binding",
+            ),
+            ReexportLineageHop(
+                "b::public_foo",
+                "a::foo",
+                "binding",
+            ),
+        ),
+    )
+    owner_names = _owner_names_fixture()
+    chain_payload = {
+        "status": "resolved",
+        "query": "c::exported",
+        "canonical_target": "a::foo",
+        "hops": [
+            {
+                "source": "c::exported",
+                "target": "b::public_foo",
+                "kind": "binding",
+            },
+            {
+                "source": "b::public_foo",
+                "target": "a::foo",
+                "kind": "binding",
+            },
+        ],
+    }
+
+    baseline_named = build_symbol_lineage_represented_payload(
+        selected,
+        representation="named",
+        owner_names=owner_names,
+    )
+    baseline_indexed = build_symbol_lineage_represented_payload(
+        selected,
+        representation="indexed",
+        owner_names=owner_names,
+    )
+    named = build_symbol_lineage_represented_payload(
+        selected,
+        representation="named",
+        owner_names=owner_names,
+        reexport_chain=chain,
+    )
+    indexed = build_symbol_lineage_represented_payload(
+        selected,
+        representation="indexed",
+        owner_names=owner_names,
+        reexport_chain=chain,
+    )
+
+    assert "reexport_chain" not in baseline_named
+    assert "reexport_chain" not in baseline_indexed
+    assert named["reexport_chain"] == indexed["reexport_chain"] == (
+        chain_payload
+    )
+    assert named["sections"] == baseline_named["sections"]
+    assert indexed["sections"] == baseline_indexed["sections"]
+    assert "reexport_chain" not in named["sections"]
+    assert "reexport_chain" not in indexed["sections"]
+
+    named_preview = build_symbol_lineage_preview(
+        selected,
+        reexport_chain=chain,
+    )
+    assert named_preview["reexport_chain"] == chain_payload
+
+    rendered_named = json.loads(
+        render_symbol_lineage_response(
+            selected,
+            mode="fetch",
+            sections=SYMBOL_LINEAGE_SECTION_ORDER,
+            representation="named",
+            owner_names=owner_names,
+            reexport_chain=chain,
+        )
+    )
+    rendered_indexed = json.loads(
+        render_symbol_lineage_response(
+            selected,
+            mode="fetch",
+            sections=SYMBOL_LINEAGE_SECTION_ORDER,
+            representation="indexed",
+            owner_names=owner_names,
+            reexport_chain=chain,
+        )
+    )
+    rendered_named_without_chain = json.loads(
+        render_symbol_lineage_response(
+            selected,
+            mode="fetch",
+            sections=SYMBOL_LINEAGE_SECTION_ORDER,
+            representation="named",
+            owner_names=owner_names,
+        )
+    )
+    rendered_indexed_without_chain = json.loads(
+        render_symbol_lineage_response(
+            selected,
+            mode="fetch",
+            sections=SYMBOL_LINEAGE_SECTION_ORDER,
+            representation="indexed",
+            owner_names=owner_names,
+        )
+    )
+    assert rendered_named["reexport_chain"] == (
+        rendered_indexed["reexport_chain"]
+    ) == chain_payload
+    assert rendered_named["sections"] == (
+        rendered_named_without_chain["sections"]
+    )
+    assert rendered_indexed["sections"] == (
+        rendered_indexed_without_chain["sections"]
+    )
+
+    preview = build_symbol_lineage_represented_preview(
+        selected,
+        representation="indexed",
+        owner_names=owner_names,
+        candidate_mode="fetch",
+        reexport_chain=chain,
+    )
+    candidate = build_symbol_lineage_represented_payload(
+        selected,
+        representation="indexed",
+        owner_names=owner_names,
+        reexport_chain=chain,
+    )
+    candidate["mode"] = "fetch"
+    assert preview["reexport_chain"] == chain_payload
+    assert preview["candidate_response_bytes"] == (
+        mcp_rep.serialized_json_bytes(candidate)
+    )
+
+
 def test_symbol_lineage_auto_threshold_includes_freshness_envelope():
     selected = _with_empty_selected_sections(
         _selected_lineage_fixture()
diff --git a/tests/mcp/tools/test_get_symbol_lineage.py b/tests/mcp/tools/test_get_symbol_lineage.py
index e5fc4c7..419cde6 100644
--- a/tests/mcp/tools/test_get_symbol_lineage.py
+++ b/tests/mcp/tools/test_get_symbol_lineage.py
@@ -4,6 +4,10 @@ from types import SimpleNamespace
 import pytest
 
 from contextor.core.lineage_query.live_query import LiveSymbolLineageQueryResult
+from contextor.core.lineage_query.index import (
+    ReexportLineageHop,
+    ReexportLineageResolution,
+)
 from contextor.core.lineage_query.service import (
     SYMBOL_LINEAGE_SECTION_ORDER,
     LineageTargetResolution,
@@ -23,10 +27,10 @@ def _target(artifact_id="A17/2", qualified_name="pkg.mod::handler"):
     return ResolvedLineageTarget(artifact_id=artifact_id, qualified_name=qualified_name, module_name=module_name, symbol_name=symbol_name, resolution="exact_id")
 
 
-def _transport_result(resolution, *, selected=None, owner_names=None, revision=12, unavailable_reason=None):
+def _transport_result(resolution, *, selected=None, owner_names=None, revision=12, unavailable_reason=None, reexport_chain=None):
     return LiveSymbolLineageTransportResult(
         status="ok", revision=revision,
-        result=LiveSymbolLineageQueryResult(resolution=resolution, selected=selected, unavailable_reason=unavailable_reason, owner_names={} if owner_names is None else owner_names, state_freshness=_freshness(revision)),
+        result=LiveSymbolLineageQueryResult(resolution=resolution, selected=selected, unavailable_reason=unavailable_reason, owner_names={} if owner_names is None else owner_names, state_freshness=_freshness(revision), reexport_chain=reexport_chain),
     )
 
 
@@ -46,6 +50,65 @@ def test_get_symbol_lineage_auto_plans_before_one_narrow_query_and_delegates_ren
     assert observed["render"] == {"selected": marker, "mode": "auto", "sections": None, "representation": "named", "owner_names": {"A17/2": "pkg.mod::handler"}, "state_freshness": _freshness(), "allow_large_output": False}
 
 
+def test_get_symbol_lineage_forwards_resolved_reexport_chain_to_renderer(
+    tmp_path,
+    monkeypatch,
+):
+    marker = SimpleNamespace()
+    target = _target("A17/2", "a::foo")
+    chain = ReexportLineageResolution(
+        status="resolved",
+        query="c::exported",
+        canonical_target="a::foo",
+        hops=(
+            ReexportLineageHop(
+                "c::exported",
+                "b::public_foo",
+                "binding",
+            ),
+            ReexportLineageHop(
+                "b::public_foo",
+                "a::foo",
+                "binding",
+            ),
+        ),
+    )
+    observed = {}
+
+    monkeypatch.setattr(
+        mcp_runtime,
+        "query_live_symbol_lineage_narrow",
+        lambda *_args, **_kwargs: _transport_result(
+            LineageTargetResolution(
+                status="resolved",
+                query="c::exported",
+                target=target,
+            ),
+            selected=marker,
+            reexport_chain=chain,
+        ),
+    )
+    monkeypatch.setattr(
+        tool,
+        "render_symbol_lineage_response",
+        lambda selected, **kwargs: observed.update(
+            {"selected": selected, **kwargs}
+        ) or '{"status":"resolved"}',
+    )
+
+    result = json.loads(
+        tool.get_symbol_lineage(
+            str(tmp_path),
+            "c::exported",
+            representation="named",
+        )
+    )
+
+    assert result["status"] == "resolved"
+    assert observed["selected"] is marker
+    assert observed["reexport_chain"] is chain
+
+
 def test_get_symbol_lineage_fetch_sends_canonical_section_order_but_preserves_request_for_renderer(tmp_path, monkeypatch):
     marker, target, observed = SimpleNamespace(), _target(), {}
     def narrow(_root, *, query, sections):
@@ -95,6 +158,101 @@ def test_get_symbol_lineage_preserves_ambiguity_candidates_without_guessing(tmp_
     assert [candidate["artifact_id"] for candidate in result["candidates"]] == ["A17/2", "A18/1"]
 
 
+def test_get_symbol_lineage_returns_cycle_as_unresolved_without_renderer(
+    tmp_path,
+    monkeypatch,
+):
+    chain = ReexportLineageResolution(
+        status="cycle",
+        query="cycle_a::value",
+        hops=(
+            ReexportLineageHop(
+                "cycle_a::value",
+                "cycle_b::value",
+                "binding",
+            ),
+            ReexportLineageHop(
+                "cycle_b::value",
+                "cycle_a::value",
+                "binding",
+            ),
+        ),
+        reason="reexport_cycle",
+    )
+    monkeypatch.setattr(
+        mcp_runtime,
+        "query_live_symbol_lineage_narrow",
+        lambda *_args, **_kwargs: _transport_result(
+            LineageTargetResolution(
+                status="unresolved",
+                query="cycle_a::value",
+            ),
+            reexport_chain=chain,
+        ),
+    )
+    monkeypatch.setattr(
+        tool,
+        "render_symbol_lineage_response",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(
+            AssertionError("unresolved re-export rendered as resolved")
+        ),
+    )
+
+    result = json.loads(
+        tool.get_symbol_lineage(
+            str(tmp_path),
+            "cycle_a::value",
+        )
+    )
+
+    assert result["status"] == "unresolved"
+    assert result["error"] == "reexport_cycle"
+    assert result["reexport_chain"]["status"] == "cycle"
+    assert result["reexport_chain"]["reason"] == "reexport_cycle"
+    assert result["state_freshness"] == _freshness()
+
+
+def test_get_symbol_lineage_returns_external_reexport_as_unresolved(
+    tmp_path,
+    monkeypatch,
+):
+    chain = ReexportLineageResolution(
+        status="unresolved",
+        query="external_dst::public",
+        reason="target_outside_repository",
+    )
+    monkeypatch.setattr(
+        mcp_runtime,
+        "query_live_symbol_lineage_narrow",
+        lambda *_args, **_kwargs: _transport_result(
+            LineageTargetResolution(
+                status="unresolved",
+                query="external_dst::public",
+            ),
+            reexport_chain=chain,
+        ),
+    )
+    monkeypatch.setattr(
+        tool,
+        "render_symbol_lineage_response",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(
+            AssertionError("external unresolved re-export was rendered")
+        ),
+    )
+
+    result = json.loads(
+        tool.get_symbol_lineage(
+            str(tmp_path),
+            "external_dst::public",
+        )
+    )
+
+    assert result["status"] == "unresolved"
+    assert result["error"] == "target_outside_repository"
+    assert result["reexport_chain"]["status"] == "unresolved"
+    assert result["reexport_chain"]["canonical_target"] is None
+
+
 def test_get_symbol_lineage_rejects_resolved_result_without_selected_facts(tmp_path, monkeypatch):
     target = _target()
     monkeypatch.setattr(mcp_runtime, "query_live_symbol_lineage_narrow", lambda *_args, **_kwargs: _transport_result(LineageTargetResolution(status="resolved", query="A17/2", target=target), selected=None))
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index 56f2f0c..66faef5 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -5,6 +5,7 @@ Stage 3C.2a — Execution Completeness, Freshness & Full-State Parity Proof Test
 """
 
 from copy import deepcopy
+from dataclasses import asdict
 from pathlib import Path
 from unittest.mock import patch, MagicMock
 
@@ -20,6 +21,7 @@ from contextor.core.domain.module import Module
 from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.domain.usage_facts import ModuleUsageFacts, UsageDelta
 from contextor.core.live_state.hydration import hydrate_repository_engine
+from contextor.core.lineage_query.live_query import query_live_symbol_lineage
 from contextor.core.reference.engine import extract_module_usage_facts
 from contextor.core.reporting_engine.graph_analytics import (
     _CALL_USAGE_CHANNELS,
@@ -1340,6 +1342,115 @@ def test_reexport_retarget_matches_full_oracle(tmp_path):
     )
 
 
+def test_reexport_lineage_query_retarget_matches_full_oracle(tmp_path):
+    provider = tmp_path / "a.py"
+    reexporter = tmp_path / "b.py"
+    consumer = tmp_path / "c.py"
+    provider.write_text(
+        "def foo():\n"
+        "    return 'foo'\n"
+        "\n"
+        "def bar():\n"
+        "    return 'bar'\n",
+        encoding="utf-8",
+    )
+    reexporter.write_text(
+        "from a import foo as public_value\n"
+        "__all__ = ['public_value']\n",
+        encoding="utf-8",
+    )
+    consumer.write_text(
+        "from b import public_value as exported\n"
+        "__all__ = ['exported']\n",
+        encoding="utf-8",
+    )
+
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+
+    baseline = query_live_symbol_lineage(
+        engine.state,
+        "c::exported",
+        ("interface", "connections", "bindings"),
+    )
+    assert baseline.resolution.status == "resolved"
+    assert baseline.resolution.target is not None
+    assert baseline.resolution.target.qualified_name == "a::foo"
+    assert baseline.reexport_chain is not None
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in baseline.reexport_chain.hops
+    ] == [
+        ("c::exported", "b::public_value", "binding"),
+        ("b::public_value", "a::foo", "binding"),
+    ]
+
+    reexporter.write_text(
+        "from a import bar as public_value\n"
+        "__all__ = ['public_value']\n",
+        encoding="utf-8",
+    )
+    engine.update_file(str(reexporter))
+    incremental = query_live_symbol_lineage(
+        engine.state,
+        "c::exported",
+        ("interface", "connections", "bindings"),
+    )
+    oracle_state = _build_full_static_state(tmp_path)
+    full = query_live_symbol_lineage(
+        oracle_state,
+        "c::exported",
+        ("interface", "connections", "bindings"),
+    )
+
+    assert incremental.resolution.status == full.resolution.status == (
+        "resolved"
+    )
+    assert incremental.resolution.target is not None
+    assert full.resolution.target is not None
+    assert incremental.resolution.target.qualified_name == "a::bar"
+    assert incremental.resolution.target.qualified_name == (
+        full.resolution.target.qualified_name
+    )
+    assert incremental.reexport_chain == full.reexport_chain
+    assert incremental.reexport_chain is not None
+    assert [
+        (hop.source, hop.target, hop.kind)
+        for hop in incremental.reexport_chain.hops
+    ] == [
+        ("c::exported", "b::public_value", "binding"),
+        ("b::public_value", "a::bar", "binding"),
+    ]
+
+    def without_revision_provenance(value):
+        if isinstance(value, dict):
+            return {
+                key: without_revision_provenance(item)
+                for key, item in value.items()
+                if key not in {"revision", "provenance"}
+            }
+        if isinstance(value, tuple):
+            return tuple(
+                without_revision_provenance(item)
+                for item in value
+            )
+        if isinstance(value, list):
+            return [
+                without_revision_provenance(item)
+                for item in value
+            ]
+        return value
+
+    assert incremental.selected is not None
+    assert full.selected is not None
+    assert without_revision_provenance(
+        asdict(incremental.selected)
+    ) == without_revision_provenance(asdict(full.selected))
+
+
 def test_reexport_all_only_change_is_ram_only_and_matches_full_oracle(
     tmp_path,
     monkeypatch,


