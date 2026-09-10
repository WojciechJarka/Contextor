STATUS=FINAL_PASS

CONTEXTOR_EVIDENCE=Fresh pre-edit context: target at canonical revision 526, workspace_sync=verified, syntax checked_and_none, with three confirmed direct consumers. Active documentation/context and the deferred Contextor tool pool were inspected before capability selection. Post-edit analyze_single_file job 5792ea3a65c7459d97af182f21b01e8d for lineage_extraction_contracts.py completed successfully. Contextor reports fresh collision and cycle families with zero diagnostics; direct collision query for the new module returned total=0. Its state-file fingerprint is marked unverified by the single-file analysis, so that freshness limitation is recorded rather than inferred away. Textual verification confirms contracts has no facade import (its only lineage_extraction mention is the requested _PUBLIC_MODULE string).

BASELINE_ORACLE=Before the production move, created the test-only deterministic corpus/serializer and calculated immutable hashes on the untouched BASE_HEAD extraction implementation. Baseline oracle passed: 2 passed in 0.76s. EXPECTED_HASHES was then written once and was not regenerated or changed after the production move. The corpus separately covers signatures/defaults/local calls, imports/alias/wildcard invalidation, If/For merge, Try/Except/Finally/Match, comprehension/runtime/walrus, async/yield, relative import arithmetic and resource limits. Serialization uses dataclass field order, Enum values, ordered sequences, recursively canonicalized mappings, compact sorted-key JSON and SHA-256.

IMPLEMENTATION=Added contextor/core/analysis/lineage_extraction_contracts.py. It contains exactly the five moved constants, five public contracts and eight specified helpers. Bodies/signatures were copied mechanically. It imports only ast, re, dataclass, Final, Protocol, quote/unquote and the four required lineage-domain types; it does not import state_manager or the facade. The facade now imports/re-exports all moved public and private names it still uses, including _FINGERPRINT_RE, _index_ast_paths, _module_name_from_source_key, _resolve_import_module and _source_span. _AnchorExtractor, private state records, dispatch, visitors and the public extraction entry point remain physically in the facade.

PUBLIC_COMPAT=PASS. Existing __all__ remains unchanged with the same eight names in the same order. The compatibility test confirms all eight facade names and confirms __module__ == contextor.core.analysis.lineage_extraction for each moved public class/function. Metadata is set in contracts without wrappers.

NO_DUPLICATES=PASS. Textual verification finds each of the four moved class definitions and eight moved helper definitions exactly once, exclusively in lineage_extraction_contracts.py; none remains defined in the facade. There is one existing extractor/traversal path only.

FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; contextor/core/analysis/lineage_extraction_contracts.py; tests/analysis/test_lineage_extraction_equivalence.py; walkthrough.md.

TESTS_RUN=
1. .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py -q (baseline before move)
2. .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py -q (after move)
3. .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q
4. .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/analysis/test_lineage_extraction_equivalence.py tests/test_no_double_parse.py tests/test_index_fusion.py -q
5. git diff --check -- contextor/core/analysis/lineage_extraction.py contextor/core/analysis/lineage_extraction_contracts.py tests/analysis/test_lineage_extraction_equivalence.py

TEST_RESULTS=Baseline oracle: 2 passed in 0.76s. Post-move oracle/compatibility: 2 passed in 0.57s. Existing lineage suite: 97 passed in 1.75s. Combined requested suite: 110 passed in 4.42s (the original 108 plus the two new oracle/compatibility tests). Diff check passed with no errors.

FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 0a9254a..6227c9a 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -1,18 +1,28 @@
 from __future__ import annotations
 
 import ast
-import re
 from dataclasses import dataclass
-from typing import Final, Protocol
-from urllib.parse import quote, unquote
 
 from contextor.core.analysis.state_manager import canonical_python_source_path
+from contextor.core.analysis.lineage_extraction_contracts import (
+    DEFAULT_LINEAGE_EXTRACTION_LIMITS,
+    ExtractedLineageContribution,
+    ExtractedLineageProvider,
+    LineageExtractionLimits,
+    ParsedLineageSourceInput,
+    _FINGERPRINT_RE,
+    _index_ast_paths,
+    _module_name_from_source_key,
+    _resolve_import_module,
+    _source_span,
+    build_local_occurrence_id,
+    parse_local_occurrence_id,
+)
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
     ExtractedFlowFact,
     ExtractedLineageSourceFacts,
     ExtractedOccurrenceRef,
-    ExtractedSurfaceFact,
     ExtractedSymbolicKind,
     ExtractedSymbolicRef,
     LineageConfidence,
@@ -20,143 +30,8 @@ from contextor.core.domain.lineage_facts import (
     LineageRelation,
     ParameterKind,
     ResolutionKind,
-    SourceSpan,
 )
 
-_LOCAL_ID_VERSION: Final[str] = "v1"
-_ANCHOR_KINDS: Final[frozenset[str]] = frozenset({"module", "class", "function", "async_function", "lambda", "comprehension", "parameter", "binding", "import_binding", "global_declaration", "nonlocal_declaration"})
-_LOCAL_ID_KINDS: Final[frozenset[str]] = _ANCHOR_KINDS | frozenset({
-    "parameter_posonly",
-    "parameter_poskw",
-    "parameter_kwonly",
-    "parameter_vararg",
-    "parameter_varkw",
-    "expression_result",
-    "name_load",
-    "call_site",
-    "call_argument",
-    "call_result",
-    "runtime_bound_local",
-})
-_AST_PATH_RE: Final[re.Pattern[str]] = re.compile(r"^(?:root|(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*))*)$")
-_FINGERPRINT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
-
-
-@dataclass(frozen=True)
-class LineageExtractionLimits:
-    max_nodes: int = 100_000
-    max_ast_depth: int = 200
-
-    def __post_init__(self) -> None:
-        for label, value in (("max_nodes", self.max_nodes), ("max_ast_depth", self.max_ast_depth)):
-            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
-                raise ValueError(f"{label} must be a positive integer.")
-
-
-DEFAULT_LINEAGE_EXTRACTION_LIMITS: Final[LineageExtractionLimits] = LineageExtractionLimits()
-
-
-@dataclass(frozen=True)
-class ParsedLineageSourceInput:
-    source_key: str
-    source_fingerprint: str
-    tree: ast.AST
-
-
-@dataclass(frozen=True)
-class ExtractedLineageContribution:
-    anchors: tuple[ExtractedAnchorFact, ...] = ()
-    flows: tuple[ExtractedFlowFact, ...] = ()
-    surfaces: tuple[ExtractedSurfaceFact, ...] = ()
-
-
-class ExtractedLineageProvider(Protocol):
-    def extract(self, source: ParsedLineageSourceInput) -> ExtractedLineageContribution: ...
-
-
-def _validate_ast_path(ast_path: str) -> None:
-    if not isinstance(ast_path, str) or _AST_PATH_RE.fullmatch(ast_path) is None:
-        raise ValueError("ast_path is not canonical.")
-
-
-def _encode_name(name: str | None) -> str:
-    if name is None:
-        return "-"
-    if not isinstance(name, str) or not name:
-        raise ValueError("name must be a non-empty string or None.")
-    return quote(name, safe="").replace("-", "%2D")
-
-
-def build_local_occurrence_id(kind: str, ast_path: str, name: str | None = None, *, ordinal: int = 0) -> str:
-    if kind not in _LOCAL_ID_KINDS:
-        raise ValueError(f"Unknown lineage local-id kind: {kind}")
-    _validate_ast_path(ast_path)
-    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
-        raise ValueError("ordinal must be a non-negative integer.")
-    return f"occ:{_LOCAL_ID_VERSION}:{kind}:{ast_path}:i:{ordinal}:n:{_encode_name(name)}"
-
-
-def parse_local_occurrence_id(value: str) -> tuple[str, str, int, str | None]:
-    if not isinstance(value, str):
-        raise ValueError("local occurrence id must be a string.")
-    parts = value.split(":")
-    if len(parts) != 8 or parts[0] != "occ" or parts[1] != _LOCAL_ID_VERSION or parts[4] != "i" or parts[6] != "n":
-        raise ValueError("Invalid local occurrence id.")
-    kind, ast_path = parts[2], parts[3]
-    if kind not in _LOCAL_ID_KINDS:
-        raise ValueError("Invalid local occurrence kind.")
-    _validate_ast_path(ast_path)
-    try:
-        ordinal = int(parts[5])
-    except ValueError as exc:
-        raise ValueError("Invalid local occurrence ordinal.") from exc
-    if ordinal < 0:
-        raise ValueError("Invalid local occurrence ordinal.")
-    name = None if parts[7] == "-" else unquote(parts[7])
-    if build_local_occurrence_id(kind, ast_path, name, ordinal=ordinal) != value:
-        raise ValueError("Local occurrence id is not canonical.")
-    return kind, ast_path, ordinal, name
-
-
-def _source_span(node: ast.AST) -> SourceSpan:
-    start_line = int(getattr(node, "lineno", 0) or 0)
-    start_column = int(getattr(node, "col_offset", 0) or 0)
-    end_line = int(getattr(node, "end_lineno", start_line) or start_line)
-    end_column = int(getattr(node, "end_col_offset", start_column) or start_column)
-    return SourceSpan(start_line, start_column, end_line, end_column)
-
-
-def _index_ast_paths(tree: ast.AST, limits: LineageExtractionLimits) -> tuple[dict[int, str], str | None]:
-    paths: dict[int, str] = {}
-    stack: list[tuple[ast.AST, str, int]] = [(tree, "root", 0)]
-    node_count = 0
-    while stack:
-        node, ast_path, depth = stack.pop()
-        node_count += 1
-        if node_count > limits.max_nodes:
-            return {}, "node_limit"
-        if depth > limits.max_ast_depth:
-            return {}, "ast_depth_limit"
-        paths[id(node)] = ast_path
-        children = list(ast.iter_child_nodes(node))
-        for index in range(len(children) - 1, -1, -1):
-            child_path = str(index) if ast_path == "root" else f"{ast_path}.{index}"
-            stack.append((children[index], child_path, depth + 1))
-    return paths, None
-
-
-def _module_name_from_source_key(source_key: str) -> str:
-    module_name = source_key[:-3].replace("/", ".")
-    return module_name[: -len(".__init__")] if module_name.endswith(".__init__") else module_name
-
-def _resolve_import_module(source_key: str, module_name: str | None, level: int) -> str | None:
-    if level == 0: return module_name
-    package_parts = source_key.split("/")[:-1]
-    if not package_parts or level > len(package_parts): return None
-    target_parts = list(package_parts[:len(package_parts) - (level - 1)])
-    if module_name: target_parts.extend(module_name.split("."))
-    return ".".join(target_parts) if target_parts else None
-
 
 @dataclass(frozen=True)
 class _ParameterInfo:

diff --git a/contextor/core/analysis/lineage_extraction_contracts.py b/contextor/core/analysis/lineage_extraction_contracts.py
new file mode 100644
index 0000000..69f8908
--- /dev/null
+++ b/contextor/core/analysis/lineage_extraction_contracts.py
@@ -0,0 +1,157 @@
+from __future__ import annotations
+
+import ast
+import re
+from dataclasses import dataclass
+from typing import Final, Protocol
+from urllib.parse import quote, unquote
+
+from contextor.core.domain.lineage_facts import (
+    ExtractedAnchorFact,
+    ExtractedFlowFact,
+    ExtractedSurfaceFact,
+    SourceSpan,
+)
+
+_LOCAL_ID_VERSION: Final[str] = "v1"
+_ANCHOR_KINDS: Final[frozenset[str]] = frozenset({"module", "class", "function", "async_function", "lambda", "comprehension", "parameter", "binding", "import_binding", "global_declaration", "nonlocal_declaration"})
+_LOCAL_ID_KINDS: Final[frozenset[str]] = _ANCHOR_KINDS | frozenset({
+    "parameter_posonly",
+    "parameter_poskw",
+    "parameter_kwonly",
+    "parameter_vararg",
+    "parameter_varkw",
+    "expression_result",
+    "name_load",
+    "call_site",
+    "call_argument",
+    "call_result",
+    "runtime_bound_local",
+})
+_AST_PATH_RE: Final[re.Pattern[str]] = re.compile(r"^(?:root|(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*))*)$")
+_FINGERPRINT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
+
+
+@dataclass(frozen=True)
+class LineageExtractionLimits:
+    max_nodes: int = 100_000
+    max_ast_depth: int = 200
+
+    def __post_init__(self) -> None:
+        for label, value in (("max_nodes", self.max_nodes), ("max_ast_depth", self.max_ast_depth)):
+            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
+                raise ValueError(f"{label} must be a positive integer.")
+
+
+DEFAULT_LINEAGE_EXTRACTION_LIMITS: Final[LineageExtractionLimits] = LineageExtractionLimits()
+
+
+@dataclass(frozen=True)
+class ParsedLineageSourceInput:
+    source_key: str
+    source_fingerprint: str
+    tree: ast.AST
+
+
+@dataclass(frozen=True)
+class ExtractedLineageContribution:
+    anchors: tuple[ExtractedAnchorFact, ...] = ()
+    flows: tuple[ExtractedFlowFact, ...] = ()
+    surfaces: tuple[ExtractedSurfaceFact, ...] = ()
+
+
+class ExtractedLineageProvider(Protocol):
+    def extract(self, source: ParsedLineageSourceInput) -> ExtractedLineageContribution: ...
+
+
+def _validate_ast_path(ast_path: str) -> None:
+    if not isinstance(ast_path, str) or _AST_PATH_RE.fullmatch(ast_path) is None:
+        raise ValueError("ast_path is not canonical.")
+
+
+def _encode_name(name: str | None) -> str:
+    if name is None:
+        return "-"
+    if not isinstance(name, str) or not name:
+        raise ValueError("name must be a non-empty string or None.")
+    return quote(name, safe="").replace("-", "%2D")
+
+
+def build_local_occurrence_id(kind: str, ast_path: str, name: str | None = None, *, ordinal: int = 0) -> str:
+    if kind not in _LOCAL_ID_KINDS:
+        raise ValueError(f"Unknown lineage local-id kind: {kind}")
+    _validate_ast_path(ast_path)
+    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
+        raise ValueError("ordinal must be a non-negative integer.")
+    return f"occ:{_LOCAL_ID_VERSION}:{kind}:{ast_path}:i:{ordinal}:n:{_encode_name(name)}"
+
+
+def parse_local_occurrence_id(value: str) -> tuple[str, str, int, str | None]:
+    if not isinstance(value, str):
+        raise ValueError("local occurrence id must be a string.")
+    parts = value.split(":")
+    if len(parts) != 8 or parts[0] != "occ" or parts[1] != _LOCAL_ID_VERSION or parts[4] != "i" or parts[6] != "n":
+        raise ValueError("Invalid local occurrence id.")
+    kind, ast_path = parts[2], parts[3]
+    if kind not in _LOCAL_ID_KINDS:
+        raise ValueError("Invalid local occurrence kind.")
+    _validate_ast_path(ast_path)
+    try:
+        ordinal = int(parts[5])
+    except ValueError as exc:
+        raise ValueError("Invalid local occurrence ordinal.") from exc
+    if ordinal < 0:
+        raise ValueError("Invalid local occurrence ordinal.")
+    name = None if parts[7] == "-" else unquote(parts[7])
+    if build_local_occurrence_id(kind, ast_path, name, ordinal=ordinal) != value:
+        raise ValueError("Local occurrence id is not canonical.")
+    return kind, ast_path, ordinal, name
+
+
+def _source_span(node: ast.AST) -> SourceSpan:
+    start_line = int(getattr(node, "lineno", 0) or 0)
+    start_column = int(getattr(node, "col_offset", 0) or 0)
+    end_line = int(getattr(node, "end_lineno", start_line) or start_line)
+    end_column = int(getattr(node, "end_col_offset", start_column) or start_column)
+    return SourceSpan(start_line, start_column, end_line, end_column)
+
+
+def _index_ast_paths(tree: ast.AST, limits: LineageExtractionLimits) -> tuple[dict[int, str], str | None]:
+    paths: dict[int, str] = {}
+    stack: list[tuple[ast.AST, str, int]] = [(tree, "root", 0)]
+    node_count = 0
+    while stack:
+        node, ast_path, depth = stack.pop()
+        node_count += 1
+        if node_count > limits.max_nodes:
+            return {}, "node_limit"
+        if depth > limits.max_ast_depth:
+            return {}, "ast_depth_limit"
+        paths[id(node)] = ast_path
+        children = list(ast.iter_child_nodes(node))
+        for index in range(len(children) - 1, -1, -1):
+            child_path = str(index) if ast_path == "root" else f"{ast_path}.{index}"
+            stack.append((children[index], child_path, depth + 1))
+    return paths, None
+
+
+def _module_name_from_source_key(source_key: str) -> str:
+    module_name = source_key[:-3].replace("/", ".")
+    return module_name[: -len(".__init__")] if module_name.endswith(".__init__") else module_name
+
+def _resolve_import_module(source_key: str, module_name: str | None, level: int) -> str | None:
+    if level == 0: return module_name
+    package_parts = source_key.split("/")[:-1]
+    if not package_parts or level > len(package_parts): return None
+    target_parts = list(package_parts[:len(package_parts) - (level - 1)])
+    if module_name: target_parts.extend(module_name.split("."))
+    return ".".join(target_parts) if target_parts else None
+
+
+_PUBLIC_MODULE = "contextor.core.analysis.lineage_extraction"
+LineageExtractionLimits.__module__ = _PUBLIC_MODULE
+ParsedLineageSourceInput.__module__ = _PUBLIC_MODULE
+ExtractedLineageContribution.__module__ = _PUBLIC_MODULE
+ExtractedLineageProvider.__module__ = _PUBLIC_MODULE
+build_local_occurrence_id.__module__ = _PUBLIC_MODULE
+parse_local_occurrence_id.__module__ = _PUBLIC_MODULE

diff --git a/tests/analysis/test_lineage_extraction_equivalence.py b/tests/analysis/test_lineage_extraction_equivalence.py
new file mode 100644
index 0000000..6605ac7
--- /dev/null
+++ b/tests/analysis/test_lineage_extraction_equivalence.py
@@ -0,0 +1,171 @@
+from __future__ import annotations
+
+import ast
+import dataclasses
+import hashlib
+import json
+from enum import Enum
+
+from contextor.core.analysis import lineage_extraction
+
+
+def _canonical(value):
+    if dataclasses.is_dataclass(value) and not isinstance(value, type):
+        return {
+            field.name: _canonical(getattr(value, field.name))
+            for field in dataclasses.fields(value)
+        }
+    if isinstance(value, Enum):
+        return value.value
+    if isinstance(value, (tuple, list)):
+        return [_canonical(item) for item in value]
+    if isinstance(value, dict):
+        return {key: _canonical(item) for key, item in value.items()}
+    if isinstance(value, bytes):
+        raise TypeError("bytes are not supported by the lineage equivalence serializer.")
+    if value is None or isinstance(value, (bool, int, float, str)):
+        return value
+    raise TypeError(f"Unsupported lineage equivalence value: {type(value)!r}")
+
+
+def _hash_result(source: str, source_key: str, limits=None) -> str:
+    source_fingerprint = hashlib.sha256(source.encode("utf-8")).hexdigest()
+    result = lineage_extraction.extract_lineage_source_facts(
+        ast.parse(source),
+        source_key=source_key,
+        source_fingerprint=source_fingerprint,
+        **({} if limits is None else {"limits": limits}),
+    )
+    oracle_bytes = json.dumps(
+        _canonical(result),
+        ensure_ascii=False,
+        sort_keys=True,
+        separators=(",", ":"),
+    ).encode("utf-8")
+    return hashlib.sha256(oracle_bytes).hexdigest()
+
+
+_CORPUS = {
+    "signature_defaults_local_call": (
+        "def target(a, b=2, /, c=3, *args, d=4, **kwargs):\n"
+        "    return a\n"
+        "target(1, 2, 3, 4, d=5, extra=6)\n",
+        "pkg/mod.py",
+        None,
+    ),
+    "imports_alias_wildcard": (
+        "from services.api import target as alias\n"
+        "alias(1)\n"
+        "from services.other import *\n"
+        "alias(2)\n",
+        "pkg/mod.py",
+        None,
+    ),
+    "if_for_frame_merge": (
+        "if condition:\n"
+        "    value = source\n"
+        "else:\n"
+        "    value = other\n"
+        "for item in items:\n"
+        "    loop_value = item\n"
+        "value\n"
+        "loop_value\n",
+        "pkg/mod.py",
+        None,
+    ),
+    "try_except_finally_match": (
+        "try:\n"
+        "    value = source\n"
+        "except Error as error:\n"
+        "    value = error\n"
+        "finally:\n"
+        "    final = value\n"
+        "match subject:\n"
+        "    case {\"x\": captured}:\n"
+        "        result = captured\n"
+        "    case _:\n"
+        "        result = fallback\n",
+        "pkg/mod.py",
+        None,
+    ),
+    "comprehension_runtime_walrus": (
+        "[(outer := value) for value in items for inner in values if (flag := inner)]\n"
+        "outer\n"
+        "flag\n"
+        "with manager as resource:\n"
+        "    bound = resource\n",
+        "pkg/mod.py",
+        None,
+    ),
+    "async_yield": (
+        "async def worker(stream, manager):\n"
+        "    async for item in stream:\n"
+        "        async with manager as resource:\n"
+        "            yield item\n",
+        "pkg/mod.py",
+        None,
+    ),
+    "relative_import": (
+        "from ..services.api import target\n"
+        "target()\n",
+        "pkg/sub/mod.py",
+        None,
+    ),
+    "resource_limit": (
+        "first = 1\nsecond = 2\n",
+        "pkg/mod.py",
+        lineage_extraction.LineageExtractionLimits(max_nodes=1, max_ast_depth=100),
+    ),
+}
+
+
+EXPECTED_HASHES = {
+    "async_yield": "110cd0c1d520261bffe673d6e0f1df573b68ed4653be674bcb762faacdf27bf9",
+    "comprehension_runtime_walrus": "35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9",
+    "if_for_frame_merge": "f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a",
+    "imports_alias_wildcard": "7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8",
+    "relative_import": "44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95",
+    "resource_limit": "40c592a9bfb86c5f6d4fe747fa2714a92794dafbc204e601ea4b475c07e06adb",
+    "signature_defaults_local_call": "4d6984e8211918d2e84e976d5fda32f59aed9247d52821cafc688242c6f6533b",
+    "try_except_finally_match": "ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f",
+}
+
+
+def test_lineage_extraction_equivalence_oracle() -> None:
+    assert {
+        name: _hash_result(source, source_key, limits)
+        for name, (source, source_key, limits) in _CORPUS.items()
+    } == EXPECTED_HASHES
+
+
+def test_lineage_extraction_public_compatibility() -> None:
+    assert lineage_extraction.__all__ == [
+        "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
+        "ExtractedLineageContribution",
+        "ExtractedLineageProvider",
+        "LineageExtractionLimits",
+        "ParsedLineageSourceInput",
+        "build_local_occurrence_id",
+        "extract_lineage_source_facts",
+        "parse_local_occurrence_id",
+    ]
+    for name in (
+        "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
+        "ExtractedLineageContribution",
+        "ExtractedLineageProvider",
+        "LineageExtractionLimits",
+        "ParsedLineageSourceInput",
+        "build_local_occurrence_id",
+        "extract_lineage_source_facts",
+        "parse_local_occurrence_id",
+    ):
+        assert hasattr(lineage_extraction, name)
+    for value in (
+        lineage_extraction.LineageExtractionLimits,
+        lineage_extraction.ParsedLineageSourceInput,
+        lineage_extraction.ExtractedLineageContribution,
+        lineage_extraction.ExtractedLineageProvider,
+        lineage_extraction.build_local_occurrence_id,
+        lineage_extraction.parse_local_occurrence_id,
+    ):
+        assert value.__module__ == "contextor.core.analysis.lineage_extraction"
