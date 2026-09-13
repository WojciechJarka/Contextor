# F2L D1L1 Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/core/analysis/lineage_materialization.py`
- `tests/analysis/test_lineage_materialization.py`

`walkthrough.md` is excluded from its own ACTUAL_DIFF.

## SLOT_PROOF

`test_build_extracted_callable_interface_descriptor_has_exact_slots` proves return and parameter-value slots plus positional bindings for positional-only, positional-or-keyword, and vararg parameters, and keyword bindings for positional-or-keyword, keyword-only, and varkw parameters.

## GENERATION_INDEPENDENT_DIGEST_PROOF

`test_callable_interface_signature_digest_is_owner_generation_independent` proves owners `A1/1` and `A1/2` have distinct owner IDs and slots but the same SHA256 signature digest.

## REDEFINITION_FAIL_CLOSED_PROOF

`test_callable_interface_conflicting_redefinitions_fail_closed` proves distinct `pkg.mod::run` descriptors for one active owner yield `{}`.

## TESTS_RUN

```text
.\.venv\Scripts\python.exe -m py_compile contextor/core/analysis/lineage_materialization.py
.\.venv\Scripts\python.exe -m pytest -q tests/analysis/test_lineage_materialization.py
20 passed in 1.55s
git diff --check -- contextor/core/analysis/lineage_materialization.py tests/analysis/test_lineage_materialization.py
PASS
```

## ACTUAL_DIFF

```diff
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index 502b825..d4efd5c 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -2,6 +2,8 @@
 
 from __future__ import annotations
 
+import hashlib
+
 from dataclasses import dataclass
 from types import MappingProxyType
 from typing import Mapping
@@ -12,11 +14,13 @@ from contextor.core.analysis.lineage_extraction_contracts import (
 )
 from contextor.core.domain.lineage_facts import (
     LINEAGE_FACTS_SEMANTIC_VERSION,
+    ExtractedAnchorFact,
     ExtractedLineageSourceFacts,
     ExtractedOccurrenceRef,
     ExtractedSymbolicKind,
     ExtractedSymbolicRef,
     LineageConfidence,
+    LineageFamilyStatus,
     MaterializedAnchorFact,
     MaterializedFlowFact,
     MaterializedLineageSourceFacts,
@@ -31,13 +35,31 @@ from contextor.core.domain.lineage_facts import (
     SemanticEndpointRole,
     SemanticInterfaceDescriptor,
     SourceLineageManifest,
+    build_keyword_binding_slot,
     build_module_global_slot,
     build_parameter_value_slot,
+    build_positional_binding_slot,
     build_return_slot,
     claims_exact_semantic_target,
 )
 
 
+_CALLABLE_INTERFACE_ANCHOR_KINDS = frozenset(
+    {
+        "function",
+        "async_function",
+    }
+)
+
+_PARAMETER_KIND_BY_LOCAL_KIND = {
+    "parameter_posonly": ParameterKind.POSITIONAL_ONLY,
+    "parameter_poskw": ParameterKind.POSITIONAL_OR_KEYWORD,
+    "parameter_vararg": ParameterKind.VAR_POSITIONAL,
+    "parameter_kwonly": ParameterKind.KEYWORD_ONLY,
+    "parameter_varkw": ParameterKind.VAR_KEYWORD,
+}
+
+
 @dataclass(frozen=True)
 class LineageResolutionContext:
     """Narrow read-only evidence of currently active canonical identities."""
@@ -78,6 +100,204 @@ class LineageOriginUnavailableError(ValueError):
     """A legacy semantic endpoint cannot be safely re-resolved."""
 
 
+def _callable_interface_descriptor(
+    owner_id: str,
+    callable_anchor: ExtractedAnchorFact,
+    anchors: tuple[ExtractedAnchorFact, ...],
+) -> SemanticInterfaceDescriptor:
+    parameters = tuple(
+        sorted(
+            (
+                anchor
+                for anchor in anchors
+                if (
+                    anchor.kind == "parameter"
+                    and anchor.owner_local_id
+                    == callable_anchor.local_id
+                )
+            ),
+            key=lambda anchor: (
+                anchor.span.start_line,
+                anchor.span.start_column,
+                anchor.local_id,
+            ),
+        )
+    )
+
+    slots = {build_return_slot(owner_id)}
+    signature_tokens = [
+        f"callable={callable_anchor.kind}",
+    ]
+
+    for parameter in parameters:
+        local_kind, _path, ordinal, name = (
+            parse_local_occurrence_id(
+                parameter.local_id
+            )
+        )
+        try:
+            kind = _PARAMETER_KIND_BY_LOCAL_KIND[
+                local_kind
+            ]
+        except KeyError as exc:
+            raise ValueError(
+                "Parameter anchor must use a canonical "
+                "parameter local-id kind."
+            ) from exc
+        if name is None:
+            raise ValueError(
+                "Parameter anchor must have a canonical name."
+            )
+
+        slots.add(
+            build_parameter_value_slot(
+                owner_id,
+                kind,
+                ordinal=ordinal,
+                name=name,
+            )
+        )
+
+        if kind in {
+            ParameterKind.POSITIONAL_ONLY,
+            ParameterKind.POSITIONAL_OR_KEYWORD,
+        }:
+            slots.add(
+                build_positional_binding_slot(
+                    owner_id,
+                    kind,
+                    ordinal=ordinal,
+                )
+            )
+        elif kind is ParameterKind.VAR_POSITIONAL:
+            slots.add(
+                build_positional_binding_slot(
+                    owner_id,
+                    kind,
+                )
+            )
+
+        if kind in {
+            ParameterKind.POSITIONAL_OR_KEYWORD,
+            ParameterKind.KEYWORD_ONLY,
+        }:
+            slots.add(
+                build_keyword_binding_slot(
+                    owner_id,
+                    kind,
+                    name=name,
+                )
+            )
+        elif kind is ParameterKind.VAR_KEYWORD:
+            slots.add(
+                build_keyword_binding_slot(
+                    owner_id,
+                    kind,
+                )
+            )
+
+        has_ordinal = kind in {
+            ParameterKind.POSITIONAL_ONLY,
+            ParameterKind.POSITIONAL_OR_KEYWORD,
+        }
+        signature_tokens.append(
+            f"parameter={kind.value}:{ordinal if has_ordinal else '-'}:{name}"
+        )
+
+    signature_digest = hashlib.sha256(
+        "\x1f".join(signature_tokens).encode("utf-8")
+    ).hexdigest()
+
+    return SemanticInterfaceDescriptor(
+        owner_id=owner_id,
+        slots=tuple(sorted(slots)),
+        signature_digest=signature_digest,
+    )
+
+
+def build_extracted_callable_interface_descriptors(
+    sources: Mapping[str, ExtractedLineageSourceFacts],
+    active_artifact_ids: Mapping[str, str],
+) -> dict[str, SemanticInterfaceDescriptor]:
+    if not isinstance(sources, Mapping):
+        raise TypeError("sources must be a mapping.")
+    if not isinstance(active_artifact_ids, Mapping):
+        raise TypeError(
+            "active_artifact_ids must be a mapping."
+        )
+
+    descriptors: dict[
+        str,
+        SemanticInterfaceDescriptor,
+    ] = {}
+    ambiguous_owner_ids: set[str] = set()
+
+    for source_key in sorted(sources):
+        source = sources[source_key]
+        if not isinstance(
+            source,
+            ExtractedLineageSourceFacts,
+        ):
+            raise TypeError(
+                "lineage source value has invalid type."
+            )
+        if source.source_key != source_key:
+            raise ValueError(
+                "lineage mapping key does not match "
+                "source key."
+            )
+        if source.status is not LineageFamilyStatus.FRESH:
+            continue
+
+        anchors_by_id = {
+            anchor.local_id: anchor
+            for anchor in source.anchors
+        }
+        module_name = _module_name_from_source_key(
+            source.source_key
+        )
+
+        for anchor in source.anchors:
+            if (
+                anchor.kind
+                not in _CALLABLE_INTERFACE_ANCHOR_KINDS
+            ):
+                continue
+
+            symbol_path = _anchor_symbol_path(
+                anchor,
+                anchors_by_id,
+            )
+            if symbol_path is None:
+                continue
+
+            qualified_name = (
+                f"{module_name}::{symbol_path}"
+            )
+            owner_id = active_artifact_ids.get(
+                qualified_name
+            )
+            if owner_id is None:
+                continue
+            if owner_id in ambiguous_owner_ids:
+                continue
+
+            candidate = _callable_interface_descriptor(
+                owner_id,
+                anchor,
+                source.anchors,
+            )
+            existing = descriptors.get(owner_id)
+
+            if existing is None:
+                descriptors[owner_id] = candidate
+            elif existing != candidate:
+                descriptors.pop(owner_id, None)
+                ambiguous_owner_ids.add(owner_id)
+
+    return dict(sorted(descriptors.items()))
+
+
 def materialize_lineage_source_facts(
     extracted: ExtractedLineageSourceFacts,
     resolution: LineageResolutionContext,
@@ -499,15 +719,8 @@ def _slot_for(reference: ExtractedSymbolicRef, owner_id: str) -> str | None:
     local_kind, _path, ordinal, name = parse_local_occurrence_id(
         reference.source_local_id
     )
-    parameter_kinds = {
-        "parameter_posonly": ParameterKind.POSITIONAL_ONLY,
-        "parameter_poskw": ParameterKind.POSITIONAL_OR_KEYWORD,
-        "parameter_vararg": ParameterKind.VAR_POSITIONAL,
-        "parameter_kwonly": ParameterKind.KEYWORD_ONLY,
-        "parameter_varkw": ParameterKind.VAR_KEYWORD,
-    }
     try:
-        kind = parameter_kinds[local_kind]
+        kind = _PARAMETER_KIND_BY_LOCAL_KIND[local_kind]
     except KeyError as exc:
         raise ValueError(
             "Parameter symbolic reference must point at a parameter local id."
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index d0c3568..4680ca0 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -1,11 +1,16 @@
 from __future__ import annotations
 
+import ast
 import builtins
 
 import pytest
 
+from contextor.core.analysis.lineage_extraction import (
+    extract_lineage_source_facts,
+)
 from contextor.core.analysis.lineage_materialization import (
     LineageResolutionContext,
+    build_extracted_callable_interface_descriptors,
     materialize_lineage_source_facts,
     reresolve_materialized_lineage_source_facts,
 )
@@ -38,7 +43,9 @@ from contextor.core.domain.lineage_facts import (
     SourceSpan,
     SurfaceDeclarationEvidence,
     SurfaceKind,
+    build_keyword_binding_slot,
     build_parameter_value_slot,
+    build_positional_binding_slot,
     build_return_slot,
 )
 
@@ -557,3 +564,123 @@ def test_exact_surface_requires_endpoint_but_unresolved_surface_keeps_symbolic_b
         unresolved, _context(artifacts={"pkg.mod::target": "A9/1"})
     )
     assert isinstance(result.surfaces[0].exposed, MaterializedSymbolicRef)
+
+
+def _callable_interface_facts(source: str):
+    return extract_lineage_source_facts(
+        ast.parse(source),
+        source_key="pkg/mod.py",
+        source_fingerprint="f" * 64,
+    )
+
+
+def test_build_extracted_callable_interface_descriptor_has_exact_slots():
+    facts = _callable_interface_facts(
+        "def run(a, /, b, *args, c, **kwargs):\n"
+        "    return b\n"
+    )
+    owner = "A1/1"
+
+    result = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts},
+        {"pkg.mod::run": owner},
+    )
+
+    assert tuple(result) == (owner,)
+    descriptor = result[owner]
+    assert descriptor.owner_id == owner
+    assert descriptor.slots == tuple(
+        sorted(
+            {
+                build_return_slot(owner),
+                build_parameter_value_slot(
+                    owner,
+                    ParameterKind.POSITIONAL_ONLY,
+                    ordinal=0,
+                ),
+                build_positional_binding_slot(
+                    owner,
+                    ParameterKind.POSITIONAL_ONLY,
+                    ordinal=0,
+                ),
+                build_parameter_value_slot(
+                    owner,
+                    ParameterKind.POSITIONAL_OR_KEYWORD,
+                    ordinal=0,
+                ),
+                build_positional_binding_slot(
+                    owner,
+                    ParameterKind.POSITIONAL_OR_KEYWORD,
+                    ordinal=0,
+                ),
+                build_keyword_binding_slot(
+                    owner,
+                    ParameterKind.POSITIONAL_OR_KEYWORD,
+                    name="b",
+                ),
+                build_parameter_value_slot(
+                    owner,
+                    ParameterKind.VAR_POSITIONAL,
+                ),
+                build_positional_binding_slot(
+                    owner,
+                    ParameterKind.VAR_POSITIONAL,
+                ),
+                build_parameter_value_slot(
+                    owner,
+                    ParameterKind.KEYWORD_ONLY,
+                    name="c",
+                ),
+                build_keyword_binding_slot(
+                    owner,
+                    ParameterKind.KEYWORD_ONLY,
+                    name="c",
+                ),
+                build_parameter_value_slot(
+                    owner,
+                    ParameterKind.VAR_KEYWORD,
+                ),
+                build_keyword_binding_slot(
+                    owner,
+                    ParameterKind.VAR_KEYWORD,
+                ),
+            }
+        )
+    )
+
+
+def test_callable_interface_signature_digest_is_owner_generation_independent():
+    facts = _callable_interface_facts(
+        "def run(value, *, mode):\n"
+        "    return value\n"
+    )
+
+    first = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts},
+        {"pkg.mod::run": "A1/1"},
+    )["A1/1"]
+    second = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts},
+        {"pkg.mod::run": "A1/2"},
+    )["A1/2"]
+
+    assert first.owner_id != second.owner_id
+    assert first.slots != second.slots
+    assert first.signature_digest == second.signature_digest
+
+
+def test_callable_interface_conflicting_redefinitions_fail_closed():
+    facts = _callable_interface_facts(
+        "def run(value):\n"
+        "    return value\n"
+        "\n"
+        "def run(value, mode):\n"
+        "    return value\n"
+    )
+
+    result = build_extracted_callable_interface_descriptors(
+        {"pkg/mod.py": facts},
+        {"pkg.mod::run": "A1/1"},
+    )
+
+    assert result == {}
```

