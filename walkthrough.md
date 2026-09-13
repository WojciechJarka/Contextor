# F2L D1N3a Walkthrough

## STATUS

PASS

## FILES_CHANGED

- `contextor/mcp/lineage_response.py`
- `tests/mcp/test_lineage_response.py`

## AUTO_CONTRACT_PROOF

Auto plans every canonical section, includes a candidate payload, and delegates size decision.

## PREVIEW_CONTRACT_PROOF

Preview plans every canonical section without heavy payload.

## FETCH_CONTRACT_PROOF

Fetch requires explicit non-empty selection and includes selected payload.

## CANONICAL_ORDER_PROOF

Fetch canonicalizes selection independently of request order.

## NO_QUERY_PROOF

The planner accepts only request values and contains no service, backend, or facts input.

## VALIDATION_PROOF

Tests cover invalid modes, selection types, empty values, duplicates, unknown sections, and prohibited auto/preview selection.

## TESTS_RUN

```text
python -m py_compile contextor/mcp/lineage_response.py: PASS
python -m pytest -q tests/mcp/test_lineage_response.py tests/analysis/test_lineage_query_service.py tests/analysis/test_lineage_query_backend.py: 94 passed in 2.35s
git diff --check -- contextor/mcp/lineage_response.py tests/mcp/test_lineage_response.py: PASS
```

## ACTUAL_DIFF

```diff
warning: in the working copy of 'contextor/mcp/lineage_response.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/lineage_response.py b/contextor/mcp/lineage_response.py
new file mode 100644
index 0000000..88901b7
--- /dev/null
+++ b/contextor/mcp/lineage_response.py
@@ -0,0 +1,51 @@
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from contextor.core.lineage_query.service import (
+    SYMBOL_LINEAGE_SECTION_ORDER,
+)
+
+
+SYMBOL_LINEAGE_MODES = ("auto", "preview", "fetch")
+
+
+@dataclass(frozen=True)
+class SymbolLineageResponsePlan:
+    mode: str
+    candidate_sections: tuple[str, ...]
+    include_payload: bool
+    requires_size_decision: bool
+
+
+def plan_symbol_lineage_response(*, mode: str = "auto", sections: tuple[str, ...] | None = None) -> SymbolLineageResponsePlan:
+    if not isinstance(mode, str):
+        raise TypeError("mode must be a string.")
+    normalized_mode = mode.strip().lower()
+    if normalized_mode not in SYMBOL_LINEAGE_MODES:
+        raise ValueError("mode must be 'auto', 'preview', or 'fetch'.")
+    if sections is not None:
+        if not isinstance(sections, tuple):
+            raise TypeError("sections must be a tuple of section names.")
+        if any(not isinstance(section, str) or not section for section in sections):
+            raise ValueError("sections must contain non-empty strings.")
+        if len(set(sections)) != len(sections):
+            raise ValueError("sections must not contain duplicates.")
+        unknown = tuple(sorted(set(sections) - set(SYMBOL_LINEAGE_SECTION_ORDER)))
+        if unknown:
+            raise ValueError("Unknown symbol lineage sections: " + ", ".join(unknown))
+    if normalized_mode in {"auto", "preview"}:
+        if sections is not None:
+            raise ValueError(f"{normalized_mode} mode does not accept an explicit section selection.")
+        return SymbolLineageResponsePlan(
+            normalized_mode, SYMBOL_LINEAGE_SECTION_ORDER,
+            normalized_mode == "auto", normalized_mode == "auto",
+        )
+    if not sections:
+        raise ValueError("fetch mode requires at least one section.")
+    requested = set(sections)
+    return SymbolLineageResponsePlan(
+        "fetch",
+        tuple(s for s in SYMBOL_LINEAGE_SECTION_ORDER if s in requested),
+        True, False,
+    )
warning: in the working copy of 'tests/mcp/test_lineage_response.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/mcp/test_lineage_response.py b/tests/mcp/test_lineage_response.py
new file mode 100644
index 0000000..225c5f0
--- /dev/null
+++ b/tests/mcp/test_lineage_response.py
@@ -0,0 +1,43 @@
+import pytest
+
+from contextor.core.lineage_query.service import SYMBOL_LINEAGE_SECTION_ORDER
+from contextor.mcp.lineage_response import SymbolLineageResponsePlan, plan_symbol_lineage_response
+
+
+def test_auto_plans_complete_symbol_candidate_for_size_decision():
+    assert plan_symbol_lineage_response(mode=" AUTO ") == SymbolLineageResponsePlan("auto", SYMBOL_LINEAGE_SECTION_ORDER, True, True)
+
+
+def test_preview_plans_all_sections_without_payload():
+    assert plan_symbol_lineage_response(mode="preview") == SymbolLineageResponsePlan("preview", SYMBOL_LINEAGE_SECTION_ORDER, False, False)
+
+
+def test_fetch_requires_explicit_sections_and_canonicalizes_order():
+    assert plan_symbol_lineage_response(mode="fetch", sections=("state", "interface", "connections")) == SymbolLineageResponsePlan("fetch", ("interface", "connections", "state"), True, False)
+
+
+@pytest.mark.parametrize("mode", ("auto", "preview"))
+def test_auto_and_preview_reject_explicit_sections(mode):
+    with pytest.raises(ValueError, match=f"{mode} mode does not accept an explicit section selection."):
+        plan_symbol_lineage_response(mode=mode, sections=("interface",))
+
+
+@pytest.mark.parametrize("sections", (None, ()))
+def test_fetch_requires_non_empty_selection(sections):
+    with pytest.raises(ValueError, match="fetch mode requires at least one section."):
+        plan_symbol_lineage_response(mode="fetch", sections=sections)
+
+
+def test_response_plan_rejects_invalid_contract():
+    with pytest.raises(TypeError, match="mode must be a string."):
+        plan_symbol_lineage_response(mode=object())
+    with pytest.raises(ValueError, match="mode must be 'auto', 'preview', or 'fetch'."):
+        plan_symbol_lineage_response(mode="other")
+    with pytest.raises(TypeError, match="sections must be a tuple of section names."):
+        plan_symbol_lineage_response(mode="fetch", sections=["interface"])
+    with pytest.raises(ValueError, match="sections must contain non-empty strings."):
+        plan_symbol_lineage_response(mode="fetch", sections=("",))
+    with pytest.raises(ValueError, match="sections must not contain duplicates."):
+        plan_symbol_lineage_response(mode="fetch", sections=("state", "state"))
+    with pytest.raises(ValueError, match="Unknown symbol lineage sections: mystery"):
+        plan_symbol_lineage_response(mode="fetch", sections=("mystery",))
```
