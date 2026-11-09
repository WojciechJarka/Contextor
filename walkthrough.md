# P3-V1 — evaluator semantic version and receipt invalidation

## FILES_CHANGED

- `contextor/core/cycle_semantics/evidence.py`
- `contextor/core/cycle_semantics/generation_manifest.py`
- `contextor/core/cycle_semantics/partial_scc_claims.py`
- `contextor/core/cycle_semantics/partial_scc_publication.py`
- `contextor/core/cycle_semantics/optional_scc_publication.py`
- `contextor/core/cycle_semantics/publication_binding.py`
- `tests/test_cycle_semantics_evidence.py`
- `tests/test_cycle_semantics_optional_child_manifest_digest.py`
- `tests/test_cycle_semantics_partial_scc_publication.py`
- `tests/test_cycle_semantics_optional_scc_publication.py`
- `tests/test_cycle_semantics_publication_binding.py`

`walkthrough.md` jest raportem, nie plikiem produkcyjnym/testowym. HEAD przed/po `09b3c97d8106220f24763575cf35a31fa5e8609f`; worktree początkowo czysty. Bez zmian CHANGELOG, FULL, restartu, commitu, push lub historii Git.

## PREVIOUS_VERSION_CONTRACT

DIRECT_EVIDENCE: przed zmianą hard evidence=/3, optional evidence=/4; hard manifest=/2, optional manifest=/3; partial receipt=/1, optional receipt=/1, prepared binding=/2. Hard manifest nie zawierał własnego semantic epoch, a weryfikacja partial claims sprawdzała głównie kształt SHA-256. `publication_binding` odtwarzał digest hard manifestu, lecz bez epoch. Optional manifest posiadał witness z wersją i odtwarzalny digest. `partial_scc_publication` re-seal historycznej preparation sprawdzał deklaracje, ale bez nowej bariery epoch. Legacy prepared binding /1 pozostawał czytelny przez verifier; `warning_eligibility` wymaga aktualnej wersji publikacji i manifestu.

## NEW_SEMANTIC_EPOCH

CODE_PATH_PROVED: `evidence.py` ma hard `cycle-semantics-evidence/4` oraz optional `cycle-semantics-evidence/5`. Existing component token nadal zawiera semantic_version, bez zmiany source fingerprint. Stary hard evidence /3 z identycznym grafem i source manifest fingerprint daje `EVIDENCE_SEMANTIC_VERSION_MISMATCH` i INDETERMINATE; nowy dowód nadal daje MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS.

## HARD_MANIFEST_BINDING

Hard manifest ma wersję `cycle-source-manifest/3` oraz nowe `evidence_semantic_version`, domyślnie None dla historycznych/niekompletnych obiektów, nigdy interpretowane jako aktualne. Nowy digest obejmuje wersję manifestu, epoch, graf, claims i źródła. `verify_prepared_hard_manifest_digest` odtwarza digest oraz sprawdza typy, selekcję HARD_ONLY, authority, kompletne deklaracje i zgodność podpisów źródeł. Jest używany w `validate_partial_scc_claims` i `publication_binding._validated_claim_digest`. Nie uruchamia evaluatora. Stary hard manifest /2, epoch /3 lub brak epoch nie przechodzą; próba re-seal starej preparation kończy się ValueError.

## OPTIONAL_MANIFEST_BINDING

Optional manifest ma wersję `cycle-source-manifest/4`. Nowe pole epoch to `cycle-semantics-evidence/5`, identyczne z optional witness. Digest wiąże nowy epoch; verifier wymaga aktualnych wersji obu pól, ich równości i odtwarza cały digest. Stary optional evidence /4, manifest /3 lub brak epoch nie przechodzą. Dotychczasowe component evidence tokens i witness pozostały.

## RECEIPT_INVALIDATION

Wersje: partial co-publication /2, optional co-publication /2, prepared binding /3. Istniejące seal/verify sprawdzają aktualną wersję, a re-seal przechodzi przez nowe manifest gates. Testy zmieniają wyłącznie wersję lub epoch w świeżym, poprawnym receipt/preparation, zachowując source SHA, graph SHA, revision, state_id i repo_id; stare dokumenty nie przechodzą weryfikacji. Świeże receipt nadal przechodzą seal/load/verify. Brak zmian strukturalnych SCC.

## LEGACY_AUTHORITY_BOUNDARY

`publication_binding.verify_co_published_cycle_manifest` nadal może diagnostycznie weryfikować legacy /1 według wcześniejszego kontraktu. `warning_eligibility._verified_model_pass_cycle_paths` wymaga dokładnie aktualnego `PUBLICATION_BINDING_VERSION` oraz `MANIFEST_VERSION`; legacy nie może nadać warning authority. Partial/optional installed claims korzystają z aktualnych receipt version w seal/verify i sprawdzają świeżość, generację oraz authority.

## OLD_EVIDENCE_NEGATIVE_TESTS

- Hard evidence /3 przy identycznym źródle/grafie: INDETERMINATE.
- Hard manifest /2, epoch /3 i brak epoch: digest verifier false; publication binding odrzuca.
- Optional manifest /3, epoch /4, brak epoch i stary optional witness /4: digest verifier false.
- Partial receipt /1 i optional receipt /1: verify false przy niezmienionej generacji.
- Prepared binding /2: verify false przy niezmienionej generacji.
- Re-seal starej partial i optional preparation: ValueError.

## FRESH_EVIDENCE_POSITIVE_TESTS

Świeżo przygotowany hard/optional manifest przechodzi digest verification. Istniejące celowane testy potwierdzają source evidence, preparation validation, receipt seal/load/verify, installed claims i warning eligibility, w tym realną ścieżkę pozytywnego MODEL_PASS. Nie wyłączono suppression bezwarunkowo. Conditional evidence nie jest promowane do ordinary MODEL_PASS.

## TARGETED_TESTS

Końcowy zestaw 15 bezpośrednio związanych modułów: **427 passed w 104.75 s**. Obejmuje evidence, optional manifest/worker, partial claims/publication, optional publication, publication binding, installed partial/optional, warning eligibility oraz P3-D1/D1F/D2/D3 passive classes. Wcześniejsze podzestawy 136, 183, 39 oraz pięć nowych p3_v1 również przeszły; nie powtarzano ich po końcowym przejściu. `git diff --check` ograniczone do 11 plików source/test: exit 0. Pełny raport zawiera literalny diff, którego puste linie z prefiksem `+` Git traktuje jako trailing whitespace raportu. Bez pełnego pytest.

## MCP_POST_CHANGE_AUDIT

Contextor canonical revision 1252; wszystkie sześć zmienionych plików produkcyjnych i pięć testowych mają osobno `workspace_sync=verified`. Syntax errors=0; hard structural DFS paths=16; soft-dependent potential SCC=1. Nie dodano nowej krawędzi importu modułów (nowe importy symboli pozostają we wcześniej zależnych modułach). `cycle_semantics=stale`, bez FULL. SOURCE_PASS jest potwierdzone, RUNTIME_ADOPTED=UNKNOWN; bieżący persistent LIVE/MCP nie był restartowany i sam watcher revision nie dowodzi adopcji.

## FULL_DIFFS

Pełny `git diff --no-ext-diff` względem HEAD dla każdego pliku z FILES_CHANGED:

```diff
diff --git a/contextor/core/cycle_semantics/evidence.py b/contextor/core/cycle_semantics/evidence.py
index 608d60e..ceba439 100644
--- a/contextor/core/cycle_semantics/evidence.py
+++ b/contextor/core/cycle_semantics/evidence.py
@@ -29,8 +29,8 @@ from .scenarios import (
     CycleComponentScenarios, CycleScenarioReport, analyze_cycle_scenarios,
 )
 
-EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/3"
-OPTIONAL_EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/4"
+EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/4"
+OPTIONAL_EVIDENCE_SEMANTIC_VERSION = "cycle-semantics-evidence/5"
 _MISSING = "MISSING"
 
 
diff --git a/contextor/core/cycle_semantics/generation_manifest.py b/contextor/core/cycle_semantics/generation_manifest.py
index 7805f93..f9c6c92 100644
--- a/contextor/core/cycle_semantics/generation_manifest.py
+++ b/contextor/core/cycle_semantics/generation_manifest.py
@@ -18,7 +18,11 @@ from .contracts import (
     CycleSemanticsSnapshot,
     fingerprint_hard_edges,
 )
-from .evidence import OPTIONAL_EVIDENCE_SEMANTIC_VERSION, SourceBoundCycleEvidence
+from .evidence import (
+    EVIDENCE_SEMANTIC_VERSION,
+    OPTIONAL_EVIDENCE_SEMANTIC_VERSION,
+    SourceBoundCycleEvidence,
+)
 from .source_proof import (
     assess_scc_source_bytes,
     assess_optional_scc_source_bytes,
@@ -27,8 +31,8 @@ from .model_source_closure import CycleModelSourceClosure
 from .evidence import _scenario_fingerprint
 
 
-MANIFEST_VERSION = "cycle-source-manifest/2"
-OPTIONAL_MANIFEST_VERSION = "cycle-source-manifest/3"
+MANIFEST_VERSION = "cycle-source-manifest/3"
+OPTIONAL_MANIFEST_VERSION = "cycle-source-manifest/4"
 _AUTHORITY = "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
 
 
@@ -69,6 +73,7 @@ class PreparedCycleSourceManifest:
     authority: str = _AUTHORITY
     source_selection: str = "HARD_ONLY"
     optional_witness: OptionalManifestEvidenceWitness | None = None
+    evidence_semantic_version: str | None = None
 
 
 def prepare_cycle_source_manifest(
@@ -230,6 +235,7 @@ def prepare_cycle_source_manifest(
         if source_selection == "HARD_ONLY":
             manifest_hash: str | None = _digest((
                 MANIFEST_VERSION,
+                EVIDENCE_SEMANTIC_VERSION,
                 graph_hash,
                 tuple((
                     component.members,
@@ -254,7 +260,7 @@ def prepare_cycle_source_manifest(
             manifest_hash = _digest((
                 OPTIONAL_MANIFEST_VERSION,
                 "OPTIONAL_NAMED_CHILDREN",
-                optional_witness.evidence_semantic_version,
+                OPTIONAL_EVIDENCE_SEMANTIC_VERSION,
                 graph_hash,
                 optional_witness.source_manifest_fingerprint,
                 tuple((
@@ -277,6 +283,11 @@ def prepare_cycle_source_manifest(
         version=manifest_version,
         source_selection=source_selection,
         optional_witness=optional_witness,
+        evidence_semantic_version=(
+            EVIDENCE_SEMANTIC_VERSION
+            if source_selection == "HARD_ONLY"
+            else OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+        ),
     )
 
 
@@ -288,10 +299,82 @@ def _is_sha256(value: object) -> bool:
     )
 
 
+def verify_prepared_hard_manifest_digest(manifest: object) -> bool:
+    """Replay the current hard-only declaration digest."""
+    if type(manifest) is not PreparedCycleSourceManifest:
+        return False
+    if (
+        manifest.version != MANIFEST_VERSION
+        or manifest.evidence_semantic_version != EVIDENCE_SEMANTIC_VERSION
+        or manifest.source_selection != "HARD_ONLY"
+        or manifest.optional_witness is not None
+        or manifest.authority != _AUTHORITY
+        or not _is_sha256(manifest.graph_sha256)
+        or not _is_sha256(manifest.source_manifest_sha256)
+        or type(manifest.components) is not tuple
+        or not manifest.components
+    ):
+        return False
+    accepted: dict[str, tuple[str, str]] = {}
+    for component in manifest.components:
+        if (
+            type(component) is not PreparedSCCSourceBinding
+            or type(component.members) is not tuple
+            or not component.members
+            or component.members != tuple(sorted(set(component.members)))
+            or component.preparation_state != "PREPARED_UNPUBLISHED"
+            or component.reason is not None
+            or component.model_classification not in {
+                "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+                "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+            }
+            or component.model_kind not in {"FLAT_MODULE", "REGULAR_PACKAGE"}
+            or not _is_sha256(component.model_evidence_sha256)
+            or type(component.source_signatures) is not tuple
+            or not component.source_signatures
+        ):
+            return False
+        names = []
+        for row in component.source_signatures:
+            if (
+                type(row) is not tuple
+                or len(row) != 3
+                or type(row[0]) is not str
+                or not row[0]
+                or not _is_sha256(row[1])
+                or not _is_sha256(row[2])
+            ):
+                return False
+            names.append(row[0])
+            signature = (row[1], row[2])
+            if row[0] in accepted and accepted[row[0]] != signature:
+                return False
+            accepted[row[0]] = signature
+        if tuple(names) != tuple(sorted(set(names))):
+            return False
+    ordered_sources = tuple(
+        (module, *accepted[module]) for module in sorted(accepted)
+    )
+    expected = _digest((
+        MANIFEST_VERSION,
+        EVIDENCE_SEMANTIC_VERSION,
+        manifest.graph_sha256,
+        tuple((
+            component.members,
+            component.model_classification,
+            component.model_kind,
+            component.model_evidence_sha256,
+            component.source_signatures,
+        ) for component in manifest.components),
+        ordered_sources,
+    ))
+    return expected == manifest.source_manifest_sha256
+
+
 def verify_prepared_optional_manifest_digest(
     manifest: object,
 ) -> bool:
-    """Replay a v3 declaration digest without certifying source origin.
+    """Replay the current optional declaration digest without source origin.
 
     The witness makes the digest reproducible from the manifest.
     This validates internal consistency of caller-supplied declarations.
@@ -305,6 +388,8 @@ def verify_prepared_optional_manifest_digest(
 
     if (
         manifest.version != OPTIONAL_MANIFEST_VERSION
+        or manifest.evidence_semantic_version
+        != OPTIONAL_EVIDENCE_SEMANTIC_VERSION
         or manifest.source_selection != "OPTIONAL_NAMED_CHILDREN"
         or manifest.authority != _AUTHORITY
         or not _is_sha256(manifest.graph_sha256)
@@ -312,6 +397,8 @@ def verify_prepared_optional_manifest_digest(
         or type(witness) is not OptionalManifestEvidenceWitness
         or witness.evidence_semantic_version
         != OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+        or witness.evidence_semantic_version
+        != manifest.evidence_semantic_version
         or not _is_sha256(witness.source_manifest_fingerprint)
         or type(components) is not tuple
         or not components
diff --git a/contextor/core/cycle_semantics/optional_scc_publication.py b/contextor/core/cycle_semantics/optional_scc_publication.py
index 17410d6..55fdca4 100644
--- a/contextor/core/cycle_semantics/optional_scc_publication.py
+++ b/contextor/core/cycle_semantics/optional_scc_publication.py
@@ -30,7 +30,7 @@ from .partial_scc_claims import (
 
 
 OPTIONAL_SCC_PUBLICATION_VERSION = (
-    "cycle-optional-scc-co-publication/1"
+    "cycle-optional-scc-co-publication/2"
 )
 
 OPTIONAL_SCC_PUBLICATION_AUTHORITY = (
diff --git a/contextor/core/cycle_semantics/partial_scc_claims.py b/contextor/core/cycle_semantics/partial_scc_claims.py
index 1cd17a4..7a9bd30 100644
--- a/contextor/core/cycle_semantics/partial_scc_claims.py
+++ b/contextor/core/cycle_semantics/partial_scc_claims.py
@@ -16,6 +16,7 @@ from .generation_manifest import (
     PreparedCycleSourceManifest,
     PreparedSCCSourceBinding,
     verify_prepared_optional_manifest_digest,
+    verify_prepared_hard_manifest_digest,
 )
 from .model_source_closure import (
     compute_cycle_model_source_closures,
@@ -130,6 +131,7 @@ def validate_partial_scc_claims(
                 or manifest.source_selection != "HARD_ONLY"
                 or manifest.components != declarations
                 or manifest.version != MANIFEST_VERSION
+                or not verify_prepared_hard_manifest_digest(manifest)
                 or manifest.optional_witness is not None
                 or manifest.authority
                 != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
diff --git a/contextor/core/cycle_semantics/partial_scc_publication.py b/contextor/core/cycle_semantics/partial_scc_publication.py
index 9ee5c21..8a574fd 100644
--- a/contextor/core/cycle_semantics/partial_scc_publication.py
+++ b/contextor/core/cycle_semantics/partial_scc_publication.py
@@ -19,7 +19,7 @@ from .partial_scc_claims import (
 )
 
 
-PARTIAL_SCC_PUBLICATION_VERSION = "cycle-partial-scc-co-publication/1"
+PARTIAL_SCC_PUBLICATION_VERSION = "cycle-partial-scc-co-publication/2"
 PARTIAL_SCC_PUBLICATION_AUTHORITY = (
     "COMMITTED_PARTIAL_SCC_DECLARATIONS_NOT_SOURCE_CERTIFIED"
 )
diff --git a/contextor/core/cycle_semantics/publication_binding.py b/contextor/core/cycle_semantics/publication_binding.py
index d267f34..e02a354 100644
--- a/contextor/core/cycle_semantics/publication_binding.py
+++ b/contextor/core/cycle_semantics/publication_binding.py
@@ -19,12 +19,13 @@ from .generation_manifest import (
     PreparedCycleSourceManifest,
     PreparedSCCSourceBinding,
     _digest,
+    verify_prepared_hard_manifest_digest,
 )
 from .scc import analyze_import_cycle_topology
 from .model_source_closure import compute_cycle_model_source_closures
 
 
-PUBLICATION_BINDING_VERSION = "cycle-prepared-co-publication/2"
+PUBLICATION_BINDING_VERSION = "cycle-prepared-co-publication/3"
 _LEGACY_MANIFEST_VERSION = "cycle-source-manifest/1"
 _LEGACY_BINDING_VERSION = "cycle-prepared-co-publication/1"
 PUBLICATION_AUTHORITY = (
@@ -57,6 +58,8 @@ def _validated_claim_digest(
     """Validate declarations, not source-byte authenticity."""
     if type(manifest) is not PreparedCycleSourceManifest:
         raise ValueError("prepared manifest contract missing")
+    if not legacy and not verify_prepared_hard_manifest_digest(manifest):
+        raise ValueError("prepared manifest is incomplete or unsupported")
     if (
         manifest.version != (
             _LEGACY_MANIFEST_VERSION if legacy else MANIFEST_VERSION
@@ -231,15 +234,22 @@ def _validated_claim_digest(
         (name, *accepted[name])
         for name in sorted(accepted)
     )
-    expected_manifest_hash = _digest((
-        _LEGACY_MANIFEST_VERSION if legacy else MANIFEST_VERSION,
-        graph_hash,
-        (
-            tuple(component.members for component in cyclic)
-            if legacy else tuple(claims)
-        ),
-        ordered_sources,
-    ))
+    expected_manifest_hash = (
+        _digest((
+            _LEGACY_MANIFEST_VERSION,
+            graph_hash,
+            tuple(component.members for component in cyclic),
+            ordered_sources,
+        ))
+        if legacy
+        else _digest((
+            MANIFEST_VERSION,
+            manifest.evidence_semantic_version,
+            graph_hash,
+            tuple(claims),
+            ordered_sources,
+        ))
+    )
     if manifest.source_manifest_sha256 != expected_manifest_hash:
         raise ValueError(
             "prepared source manifest digest mismatch"
diff --git a/tests/test_cycle_semantics_evidence.py b/tests/test_cycle_semantics_evidence.py
index 09bbcc6..d9bcb46 100644
--- a/tests/test_cycle_semantics_evidence.py
+++ b/tests/test_cycle_semantics_evidence.py
@@ -222,6 +222,24 @@ def _one(edges=PAIR, sources=PASS):
     return result, index, snapshot, evidence
 
 
+def test_p3_v1_old_hard_evidence_epoch_rejected_with_same_source():
+    index, snapshot, current = _bound(PAIR, PASS)
+    assert current.semantic_version == EVIDENCE_SEMANTIC_VERSION
+    assert assess(PAIR, index, snapshot, current)[0].model_classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+    stale = replace(
+        current, semantic_version="cycle-semantics-evidence/3",
+    )
+    assert stale.graph_fingerprint == current.graph_fingerprint
+    assert stale.source_manifest_fingerprint == (
+        current.source_manifest_fingerprint
+    )
+    verdict = assess(PAIR, index, snapshot, stale)
+    assert verdict[0].reason == "EVIDENCE_SEMANTIC_VERSION_MISMATCH"
+    assert verdict[0].model_classification == "INDETERMINATE"
+
+
 def test_p0_t01_mutual_import_all_entries_pass():
     result, _, _, _ = _one()
     assert result == (SCCModelEvidenceAssessment(
diff --git a/tests/test_cycle_semantics_optional_child_manifest_digest.py b/tests/test_cycle_semantics_optional_child_manifest_digest.py
index 125c39a..ea36620 100644
--- a/tests/test_cycle_semantics_optional_child_manifest_digest.py
+++ b/tests/test_cycle_semantics_optional_child_manifest_digest.py
@@ -13,6 +13,9 @@ from contextor.core.cycle_semantics.generation_manifest import (
     prepare_cycle_source_manifest,
     verify_prepared_optional_manifest_digest,
 )
+from contextor.core.cycle_semantics.evidence import (
+    OPTIONAL_EVIDENCE_SEMANTIC_VERSION,
+)
 from contextor.core.cycle_semantics.publication_binding import (
     _validated_claim_digest,
 )
@@ -60,6 +63,32 @@ def test_optional_manifest_digest_replays(tmp_path):
         OptionalManifestEvidenceWitness
     )
     assert verify_prepared_optional_manifest_digest(manifest)
+
+
+def test_p3_v1_optional_epoch_rejects_old_manifest_and_evidence(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+    assert manifest.evidence_semantic_version == (
+        OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+    )
+    assert manifest.optional_witness.evidence_semantic_version == (
+        OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+    )
+    for stale in (
+        replace(manifest, evidence_semantic_version=None),
+        replace(
+            manifest,
+            evidence_semantic_version="cycle-semantics-evidence/4",
+        ),
+        replace(manifest, version="cycle-source-manifest/3"),
+        replace(
+            manifest,
+            optional_witness=replace(
+                manifest.optional_witness,
+                evidence_semantic_version="cycle-semantics-evidence/4",
+            ),
+        ),
+    ):
+        assert not verify_prepared_optional_manifest_digest(stale)
     assert verify_prepared_optional_manifest_digest(manifest)
 
 
diff --git a/tests/test_cycle_semantics_optional_scc_publication.py b/tests/test_cycle_semantics_optional_scc_publication.py
index 3001733..dd996e6 100644
--- a/tests/test_cycle_semantics_optional_scc_publication.py
+++ b/tests/test_cycle_semantics_optional_scc_publication.py
@@ -82,6 +82,34 @@ def _verify(state, metadata):
     )
 
 
+def test_p3_v1_old_optional_receipt_and_manifest_cannot_revalidate(
+    tmp_path, isolated_dirs,
+):
+    _, preparation, state, origin = _case(tmp_path)
+    cache = tmp_path / "optional-v1-store"
+    _save(cache, state, origin, preparation=preparation)
+    loaded, metadata = _load(cache, origin)
+    assert _verify(loaded, metadata)
+    receipt = loaded.cycle_optional_source_publication
+    loaded.cycle_optional_source_publication = replace(
+        receipt, version="cycle-optional-scc-co-publication/1",
+    )
+    assert not _verify(loaded, metadata)
+    stale_preparation = replace(
+        preparation,
+        manifest=replace(
+            preparation.manifest,
+            evidence_semantic_version="cycle-semantics-evidence/4",
+        ),
+    )
+    with pytest.raises(ValueError):
+        seal_optional_scc_preparation(
+            loaded, stale_preparation,
+            revision=metadata.revision, state_id=metadata.state_id,
+            repo_id=metadata.repo_id, root_path=metadata.root_path,
+        )
+
+
 def test_t01_canonical_writer_seals_and_loader_verifies(
     tmp_path, isolated_dirs,
 ):
diff --git a/tests/test_cycle_semantics_partial_scc_publication.py b/tests/test_cycle_semantics_partial_scc_publication.py
index 97df07b..a967102 100644
--- a/tests/test_cycle_semantics_partial_scc_publication.py
+++ b/tests/test_cycle_semantics_partial_scc_publication.py
@@ -79,6 +79,33 @@ def _verify(state, metadata):
     )
 
 
+def test_p3_v1_old_partial_receipt_cannot_revalidate(
+    tmp_path, isolated_dirs,
+):
+    state, preparation = _case(tmp_path, TWO_PASS)
+    _save(state, tmp_path, partial=preparation)
+    loaded, metadata = load_snapshot(tmp_path, "partial-state")
+    assert _verify(loaded, metadata)
+    receipt = loaded.cycle_partial_source_publication
+    loaded.cycle_partial_source_publication = replace(
+        receipt, version="cycle-partial-scc-co-publication/1",
+    )
+    assert not _verify(loaded, metadata)
+    stale_preparation = replace(
+        preparation,
+        manifest=replace(
+            preparation.manifest,
+            evidence_semantic_version="cycle-semantics-evidence/3",
+        ),
+    )
+    with pytest.raises(ValueError):
+        seal_partial_scc_preparation(
+            loaded, stale_preparation,
+            revision=metadata.revision, state_id=metadata.state_id,
+            repo_id=metadata.repo_id, root_path=metadata.root_path,
+        )
+
+
 def _tamper(root, metadata, mutate):
     path = root / metadata.state_file
     payload = pickle.loads(path.read_bytes())
diff --git a/tests/test_cycle_semantics_publication_binding.py b/tests/test_cycle_semantics_publication_binding.py
index 43037cb..df45738 100644
--- a/tests/test_cycle_semantics_publication_binding.py
+++ b/tests/test_cycle_semantics_publication_binding.py
@@ -11,14 +11,19 @@ from contextor.core.analysis.state_manager import (
     RepositoryAnalysisState,
 )
 from contextor.core.cycle_semantics.generation_manifest import (
+    MANIFEST_VERSION,
     prepare_cycle_source_manifest,
+    verify_prepared_hard_manifest_digest,
 )
+from contextor.core.cycle_semantics.evidence import EVIDENCE_SEMANTIC_VERSION
 from contextor.core.cycle_semantics.lifecycle import (
     invalidate_cycle_semantics,
 )
 from contextor.core.cycle_semantics.publication_binding import (
     PUBLICATION_AUTHORITY,
+    PUBLICATION_BINDING_VERSION,
     CanonicalCycleManifestReceipt,
+    _validated_claim_digest,
     verify_co_published_cycle_manifest,
 )
 from contextor.core.domain.graph import ProjectGraph
@@ -56,6 +61,38 @@ def _case():
     return state, prepared
 
 
+def test_p3_v1_hard_epoch_rejects_old_manifest_and_resealing():
+    state, current = _case()
+    assert current.version == MANIFEST_VERSION
+    assert current.evidence_semantic_version == EVIDENCE_SEMANTIC_VERSION
+    assert verify_prepared_hard_manifest_digest(current)
+    for stale in (
+        replace(current, evidence_semantic_version=None),
+        replace(current, evidence_semantic_version="cycle-semantics-evidence/3"),
+        replace(current, version="cycle-source-manifest/2"),
+    ):
+        assert not verify_prepared_hard_manifest_digest(stale)
+        with pytest.raises(ValueError, match="incomplete or unsupported"):
+            _validated_claim_digest(state, stale)
+
+
+def test_p3_v1_old_publication_binding_is_not_warning_authority(
+    tmp_path, isolated_dirs,
+):
+    state, prepared = _case()
+    _save(state, tmp_path, 1, prepared)
+    loaded, metadata = load_snapshot(tmp_path, "cycle-state")
+    receipt = loaded.cycle_source_publication
+    assert receipt.version == PUBLICATION_BINDING_VERSION
+    loaded.cycle_source_publication = replace(
+        receipt, version="cycle-prepared-co-publication/2",
+    )
+    assert not verify_co_published_cycle_manifest(
+        loaded, revision=metadata.revision, state_id=metadata.state_id,
+        repo_id=metadata.repo_id, root_path=metadata.root_path,
+    )
+
+
 def _save(state, root, revision, prepared=None):
     return save_snapshot(
         state,
```

## FINAL_VERDICT

SOURCE_PASS / RUNTIME_ADOPTED_UNKNOWN. Nowy semantic epoch odrzuca stare hard/optional manifesty i receipts w ścieżkach warning eligibility; świeża klasyfikacja MODEL_PASS pozostaje możliwa. Bez FULL/restartu nie ma certyfikacji bieżącej publikacji LIVE. STOP.
