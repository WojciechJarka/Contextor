# CONTEXTOR C16-B03-P1D3E

## FILES_CHANGED

- contextor/core/cycle_semantics/generation_manifest.py
- contextor/core/cycle_semantics/partial_scc_claims.py
- contextor/core/cycle_semantics/publication_binding.py
- tests/test_cycle_semantics_optional_child_manifest_digest.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; seven specified modules; `-B -m pytest -q -rs -p no:cacheprovider`; basetemp outside repository. 97 passed in 20.73 s. `git diff --check` passed. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP module contexts for all four changed modules: canonical_revision=1032, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. An intermediate partial_scc_claims read at revision 1031 returned workspace_sync=unverified; the final read at revision 1032 returned verified. Cycle semantics family remains stale. No production FULL, update_file, restart, or commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/generation_manifest.py b/contextor/core/cycle_semantics/generation_manifest.py
index b2522e1..066f43e 100644
--- a/contextor/core/cycle_semantics/generation_manifest.py
+++ b/contextor/core/cycle_semantics/generation_manifest.py
@@ -18,7 +18,7 @@ from .contracts import (
     CycleSemanticsSnapshot,
     fingerprint_hard_edges,
 )
-from .evidence import SourceBoundCycleEvidence
+from .evidence import OPTIONAL_EVIDENCE_SEMANTIC_VERSION, SourceBoundCycleEvidence
 from .source_proof import (
     assess_scc_source_bytes,
     assess_optional_scc_source_bytes,
@@ -53,6 +53,13 @@ class PreparedSCCSourceBinding:
     model_evidence_sha256: str | None = None
 
 
+@dataclass(frozen=True)
+class OptionalManifestEvidenceWitness:
+    evidence_semantic_version: str
+    source_manifest_fingerprint: str
+    component_evidence_tokens: tuple[str, ...]
+
+
 @dataclass(frozen=True)
 class PreparedCycleSourceManifest:
     graph_sha256: str
@@ -61,6 +68,7 @@ class PreparedCycleSourceManifest:
     version: str = MANIFEST_VERSION
     authority: str = _AUTHORITY
     source_selection: str = "HARD_ONLY"
+    optional_witness: OptionalManifestEvidenceWitness | None = None
 
 
 def prepare_cycle_source_manifest(
@@ -212,6 +220,8 @@ def prepare_cycle_source_manifest(
 
     # A global manifest digest must not imply completeness
     # when even one SCC lacks sufficient evidence.
+    optional_witness: OptionalManifestEvidenceWitness | None = None
+
     if all_complete:
         ordered_sources = tuple(
             (module, *accepted_signatures[module])
@@ -231,19 +241,29 @@ def prepare_cycle_source_manifest(
                 ordered_sources,
             ))
         else:
+            optional_witness = OptionalManifestEvidenceWitness(
+                evidence_semantic_version=source_evidence.semantic_version,
+                source_manifest_fingerprint=(
+                    source_evidence.source_manifest_fingerprint
+                ),
+                component_evidence_tokens=tuple(
+                    component.evidence_token
+                    for component in source_evidence.components
+                ),
+            )
             manifest_hash = _digest((
                 OPTIONAL_MANIFEST_VERSION,
                 "OPTIONAL_NAMED_CHILDREN",
-                source_evidence.semantic_version,
+                optional_witness.evidence_semantic_version,
                 graph_hash,
-                source_evidence.source_manifest_fingerprint,
+                optional_witness.source_manifest_fingerprint,
                 tuple((
                     component.members,
                     component.model_classification,
                     component.model_kind,
                     component.model_evidence_sha256,
                     component.source_signatures,
-                    source_evidence.components[position].evidence_token,
+                    optional_witness.component_evidence_tokens[position],
                 ) for position, component in enumerate(prepared)),
                 ordered_sources,
             ))
@@ -256,4 +276,137 @@ def prepare_cycle_source_manifest(
         components=tuple(prepared),
         version=manifest_version,
         source_selection=source_selection,
+        optional_witness=optional_witness,
     )
+
+
+def _is_sha256(value: object) -> bool:
+    return (
+        type(value) is str
+        and len(value) == 64
+        and all(char in "0123456789abcdef" for char in value)
+    )
+
+
+def verify_prepared_optional_manifest_digest(
+    manifest: object,
+) -> bool:
+    """Replay a v3 declaration digest without certifying source origin.
+
+    The witness makes the digest reproducible from the manifest.
+    This validates internal consistency of caller-supplied declarations.
+    It does not authenticate source bytes, canonical ownership or LIVE.
+    """
+    if type(manifest) is not PreparedCycleSourceManifest:
+        return False
+
+    witness = manifest.optional_witness
+    components = manifest.components
+
+    if (
+        manifest.version != OPTIONAL_MANIFEST_VERSION
+        or manifest.source_selection != "OPTIONAL_NAMED_CHILDREN"
+        or manifest.authority != _AUTHORITY
+        or not _is_sha256(manifest.graph_sha256)
+        or not _is_sha256(manifest.source_manifest_sha256)
+        or type(witness) is not OptionalManifestEvidenceWitness
+        or witness.evidence_semantic_version
+        != OPTIONAL_EVIDENCE_SEMANTIC_VERSION
+        or not _is_sha256(witness.source_manifest_fingerprint)
+        or type(components) is not tuple
+        or not components
+        or type(witness.component_evidence_tokens) is not tuple
+        or len(witness.component_evidence_tokens) != len(components)
+        or any(
+            not _is_sha256(token)
+            for token in witness.component_evidence_tokens
+        )
+    ):
+        return False
+
+    accepted: dict[str, tuple[str, str]] = {}
+
+    for component in components:
+        if type(component) is not PreparedSCCSourceBinding:
+            return False
+
+        if (
+            type(component.members) is not tuple
+            or not component.members
+            or any(
+                type(name) is not str or not name
+                for name in component.members
+            )
+            or component.members != tuple(sorted(set(component.members)))
+            or component.preparation_state != "PREPARED_UNPUBLISHED"
+            or component.reason is not None
+            or component.model_classification not in {
+                "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
+                "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
+            }
+            or component.model_kind not in {
+                "FLAT_MODULE",
+                "REGULAR_PACKAGE",
+            }
+            or not _is_sha256(component.model_evidence_sha256)
+            or type(component.source_signatures) is not tuple
+            or not component.source_signatures
+        ):
+            return False
+
+        names: list[str] = []
+
+        for row in component.source_signatures:
+            if type(row) is not tuple or len(row) != 3:
+                return False
+
+            module, raw_sha256, ast_sha256 = row
+
+            if (
+                type(module) is not str
+                or not module
+                or not _is_sha256(raw_sha256)
+                or not _is_sha256(ast_sha256)
+            ):
+                return False
+
+            names.append(module)
+            signature = (raw_sha256, ast_sha256)
+
+            if module in accepted and accepted[module] != signature:
+                return False
+
+            accepted[module] = signature
+
+        if tuple(names) != tuple(sorted(set(names))):
+            return False
+
+    ordered_sources = tuple(
+        (module, *accepted[module])
+        for module in sorted(accepted)
+    )
+
+    if (
+        witness.source_manifest_fingerprint
+        != _digest(ordered_sources)
+    ):
+        return False
+
+    expected = _digest((
+        OPTIONAL_MANIFEST_VERSION,
+        "OPTIONAL_NAMED_CHILDREN",
+        witness.evidence_semantic_version,
+        manifest.graph_sha256,
+        witness.source_manifest_fingerprint,
+        tuple((
+            component.members,
+            component.model_classification,
+            component.model_kind,
+            component.model_evidence_sha256,
+            component.source_signatures,
+            witness.component_evidence_tokens[position],
+        ) for position, component in enumerate(components)),
+        ordered_sources,
+    ))
+
+    return expected == manifest.source_manifest_sha256
diff --git a/contextor/core/cycle_semantics/partial_scc_claims.py b/contextor/core/cycle_semantics/partial_scc_claims.py
index eaa4a4b..1cd17a4 100644
--- a/contextor/core/cycle_semantics/partial_scc_claims.py
+++ b/contextor/core/cycle_semantics/partial_scc_claims.py
@@ -15,6 +15,7 @@ from .generation_manifest import (
     OPTIONAL_MANIFEST_VERSION,
     PreparedCycleSourceManifest,
     PreparedSCCSourceBinding,
+    verify_prepared_optional_manifest_digest,
 )
 from .model_source_closure import (
     compute_cycle_model_source_closures,
@@ -129,6 +130,7 @@ def validate_partial_scc_claims(
                 or manifest.source_selection != "HARD_ONLY"
                 or manifest.components != declarations
                 or manifest.version != MANIFEST_VERSION
+                or manifest.optional_witness is not None
                 or manifest.authority
                 != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
                 or manifest.graph_sha256 != snapshot.graph_sha256
@@ -307,6 +309,7 @@ def validate_optional_partial_scc_claims(
                 or type(manifest) is not PreparedCycleSourceManifest
                 or manifest.source_selection != "OPTIONAL_NAMED_CHILDREN"
                 or manifest.version != OPTIONAL_MANIFEST_VERSION
+                or not verify_prepared_optional_manifest_digest(manifest)
                 or manifest.authority
                 != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
                 or manifest.graph_sha256 != graph_sha256
diff --git a/contextor/core/cycle_semantics/publication_binding.py b/contextor/core/cycle_semantics/publication_binding.py
index 39237e8..d267f34 100644
--- a/contextor/core/cycle_semantics/publication_binding.py
+++ b/contextor/core/cycle_semantics/publication_binding.py
@@ -61,6 +61,8 @@ def _validated_claim_digest(
         manifest.version != (
             _LEGACY_MANIFEST_VERSION if legacy else MANIFEST_VERSION
         )
+        or manifest.source_selection != "HARD_ONLY"
+        or manifest.optional_witness is not None
         or manifest.authority
         != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
         or not isinstance(manifest.source_manifest_sha256, str)

diff --git a/tests/test_cycle_semantics_optional_child_manifest_digest.py b/tests/test_cycle_semantics_optional_child_manifest_digest.py
new file mode 100644
index 0000000..a4e6787
--- /dev/null
+++ b/tests/test_cycle_semantics_optional_child_manifest_digest.py
@@ -0,0 +1,334 @@
+"""P1D3E: v3 manifest digest replay, without source certification."""
+
+from dataclasses import replace
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.generation_manifest import (
+    MANIFEST_VERSION,
+    OPTIONAL_MANIFEST_VERSION,
+    OptionalManifestEvidenceWitness,
+    _digest,
+    prepare_cycle_source_manifest,
+    verify_prepared_optional_manifest_digest,
+)
+from contextor.core.cycle_semantics.publication_binding import (
+    _validated_claim_digest,
+)
+from contextor.core.cycle_semantics.partial_scc_claims import (
+    validate_optional_partial_scc_claims,
+    validate_partial_scc_claims,
+)
+from tests.test_cycle_semantics_optional_child_byte_replay import (
+    _fixture,
+)
+from tests.test_cycle_semantics_optional_child_manifest import (
+    _prepare,
+)
+from tests.test_cycle_semantics_optional_child_partial_claims import (
+    _case as real_case,
+    _check,
+)
+from tests.test_cycle_semantics_optional_child_scenarios import (
+    FILES,
+)
+from tests.test_cycle_semantics_evidence import (
+    PAIR,
+    PASS,
+    _bound,
+    _p1b_snapshots,
+)
+from tests.test_cycle_semantics_partial_scc_claims import (
+    _case as legacy_case,
+)
+from tests.test_original_worker_partial_scc_preparation import (
+    TWO_PASS,
+)
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch, isolated_dirs):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def test_optional_manifest_digest_replays(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+
+    assert manifest.version == OPTIONAL_MANIFEST_VERSION
+    assert type(manifest.optional_witness) is (
+        OptionalManifestEvidenceWitness
+    )
+    assert verify_prepared_optional_manifest_digest(manifest)
+    assert verify_prepared_optional_manifest_digest(manifest)
+
+
+def test_valid_sha256_forgery_is_rejected(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+
+    changed = replace(
+        manifest,
+        source_manifest_sha256="0" * 64,
+    )
+
+    assert not verify_prepared_optional_manifest_digest(changed)
+
+
+def test_component_token_tampering_is_rejected(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+    witness = manifest.optional_witness
+
+    changed = replace(
+        manifest,
+        optional_witness=replace(
+            witness,
+            component_evidence_tokens=("0" * 64,),
+        ),
+    )
+
+    assert not verify_prepared_optional_manifest_digest(changed)
+
+
+def test_missing_witness_is_rejected(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+
+    assert not verify_prepared_optional_manifest_digest(
+        replace(manifest, optional_witness=None)
+    )
+
+
+def test_wrong_evidence_semantic_version_is_rejected(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+
+    changed = replace(
+        manifest,
+        optional_witness=replace(
+            manifest.optional_witness,
+            evidence_semantic_version="cycle-semantics-evidence/3",
+        ),
+    )
+
+    assert not verify_prepared_optional_manifest_digest(changed)
+
+
+def test_forged_source_manifest_fails_even_with_rehashed_outer_digest(
+    tmp_path,
+):
+    manifest = _prepare(_fixture(tmp_path))
+    witness = replace(
+        manifest.optional_witness,
+        source_manifest_fingerprint="0" * 64,
+    )
+
+    accepted = {
+        module: (raw, ast_hash)
+        for component in manifest.components
+        for module, raw, ast_hash in component.source_signatures
+    }
+    ordered = tuple(
+        (name, *accepted[name])
+        for name in sorted(accepted)
+    )
+
+    forged_hash = _digest((
+        OPTIONAL_MANIFEST_VERSION,
+        "OPTIONAL_NAMED_CHILDREN",
+        witness.evidence_semantic_version,
+        manifest.graph_sha256,
+        witness.source_manifest_fingerprint,
+        tuple((
+            component.members,
+            component.model_classification,
+            component.model_kind,
+            component.model_evidence_sha256,
+            component.source_signatures,
+            witness.component_evidence_tokens[position],
+        ) for position, component in enumerate(manifest.components)),
+        ordered,
+    ))
+
+    changed = replace(
+        manifest,
+        source_manifest_sha256=forged_hash,
+        optional_witness=witness,
+    )
+
+    assert not verify_prepared_optional_manifest_digest(changed)
+
+
+def test_modified_component_source_signature_rejected(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+    component = manifest.components[0]
+
+    changed_rows = list(component.source_signatures)
+    name, _, ast_hash = changed_rows[0]
+    changed_rows[0] = (name, "0" * 64, ast_hash)
+
+    changed = replace(
+        manifest,
+        components=(
+            replace(
+                component,
+                source_signatures=tuple(changed_rows),
+            ),
+        ),
+    )
+
+    assert not verify_prepared_optional_manifest_digest(changed)
+
+
+def test_missing_optional_child_blocks_complete_digest(tmp_path):
+    case = list(_fixture(tmp_path))
+    case[4] = dict(case[4])
+    case[4].pop("pkg.child")
+
+    manifest = _prepare(case)
+
+    assert manifest.source_manifest_sha256 is None
+    assert manifest.optional_witness is None
+    assert not verify_prepared_optional_manifest_digest(manifest)
+
+
+def test_multiple_scc_component_token_order_is_bound(tmp_path):
+    case = _fixture(
+        tmp_path,
+        files={
+            **FILES,
+            "pkg/x.py": "import pkg.y\n",
+            "pkg/y.py": "import pkg.x\n",
+        },
+    )
+    manifest = _prepare(case)
+
+    assert len(manifest.components) == 2
+    assert verify_prepared_optional_manifest_digest(manifest)
+
+    witness = manifest.optional_witness
+
+    changed = replace(
+        manifest,
+        optional_witness=replace(
+            witness,
+            component_evidence_tokens=tuple(
+                reversed(witness.component_evidence_tokens)
+            ),
+        ),
+    )
+
+    assert not verify_prepared_optional_manifest_digest(changed)
+
+
+def test_optional_claim_validator_rejects_forged_64_hex_digest(
+    tmp_path,
+):
+    case = list(real_case(tmp_path))
+    preparation = case[2]
+
+    assert _check(case) is not None
+
+    forged = replace(
+        preparation.manifest,
+        source_manifest_sha256="0" * 64,
+    )
+    case[2] = replace(preparation, manifest=forged)
+
+    assert _check(case) is None
+
+
+def test_optional_claim_validator_rejects_forged_witness(
+    tmp_path,
+):
+    case = list(real_case(tmp_path))
+    preparation = case[2]
+    manifest = preparation.manifest
+
+    forged = replace(
+        manifest,
+        optional_witness=replace(
+            manifest.optional_witness,
+            component_evidence_tokens=("0" * 64,),
+        ),
+    )
+    case[2] = replace(preparation, manifest=forged)
+
+    assert _check(case) is None
+
+
+def test_legacy_hard_only_digest_and_no_witness():
+    index, snapshot, evidence = _bound(PAIR, PASS)
+
+    manifest = prepare_cycle_source_manifest(
+        PAIR,
+        index,
+        snapshot,
+        evidence,
+        _p1b_snapshots(PASS),
+    )
+
+    assert manifest.version == MANIFEST_VERSION
+    assert manifest.source_selection == "HARD_ONLY"
+    assert manifest.optional_witness is None
+    assert manifest.source_manifest_sha256 is not None
+    assert not verify_prepared_optional_manifest_digest(manifest)
+
+
+def test_hard_only_publication_rejects_injected_optional_witness(
+    tmp_path,
+):
+    edges, snapshot, preparation = legacy_case(
+        tmp_path, TWO_PASS
+    )
+
+    witness = OptionalManifestEvidenceWitness(
+        evidence_semantic_version="cycle-semantics-evidence/4",
+        source_manifest_fingerprint="0" * 64,
+        component_evidence_tokens=(
+            "0" * 64,
+            "0" * 64,
+        ),
+    )
+
+    assert preparation.manifest is not None
+
+    mutated_manifest = replace(
+        preparation.manifest,
+        optional_witness=witness,
+    )
+    mutated_preparation = replace(
+        preparation,
+        manifest=mutated_manifest,
+    )
+
+    assert validate_partial_scc_claims(
+        edges,
+        snapshot,
+        mutated_preparation,
+    ) is None
+
+    with pytest.raises(
+        ValueError,
+        match="prepared manifest is incomplete or unsupported",
+    ):
+        _validated_claim_digest(None, mutated_manifest)
+
+
+def test_optional_digest_replay_never_publishes(tmp_path):
+    manifest = _prepare(_fixture(tmp_path))
+
+    assert verify_prepared_optional_manifest_digest(manifest)
+
+    with pytest.raises(ValueError):
+        _validated_claim_digest(None, manifest)
+
+
+def test_digest_replay_performs_no_filesystem_read(
+    tmp_path, monkeypatch,
+):
+    manifest = _prepare(_fixture(tmp_path))
+
+    def forbidden(self):
+        raise AssertionError("source reread forbidden")
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(Path, "read_bytes", forbidden)
+        assert verify_prepared_optional_manifest_digest(manifest)
```

## FINAL_VERDICT

PASS
