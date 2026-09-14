from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from enum import Enum

from contextor.core.analysis import lineage_extraction


def _canonical(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, bytes):
        raise TypeError("bytes are not supported by the lineage equivalence serializer.")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"Unsupported lineage equivalence value: {type(value)!r}")


def _hash_value(value) -> str:
    oracle_bytes = json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(oracle_bytes).hexdigest()


def _result(source: str, source_key: str, limits=None):
    source_fingerprint = hashlib.sha256(source.encode("utf-8")).hexdigest()
    result = lineage_extraction.extract_lineage_source_facts(
        ast.parse(source),
        source_key=source_key,
        source_fingerprint=source_fingerprint,
        **({} if limits is None else {"limits": limits}),
    )
    return result


def _hash_result(source: str, source_key: str, limits=None) -> str:
    return _hash_value(_result(source, source_key, limits))


_CORPUS = {
    "signature_defaults_local_call": (
        "def target(a, b=2, /, c=3, *args, d=4, **kwargs):\n"
        "    return a\n"
        "target(1, 2, 3, 4, d=5, extra=6)\n",
        "pkg/mod.py",
        None,
    ),
    "imports_alias_wildcard": (
        "from services.api import target as alias\n"
        "alias(1)\n"
        "from services.other import *\n"
        "alias(2)\n",
        "pkg/mod.py",
        None,
    ),
    "if_for_frame_merge": (
        "if condition:\n"
        "    value = source\n"
        "else:\n"
        "    value = other\n"
        "for item in items:\n"
        "    loop_value = item\n"
        "value\n"
        "loop_value\n",
        "pkg/mod.py",
        None,
    ),
    "try_except_finally_match": (
        "try:\n"
        "    value = source\n"
        "except Error as error:\n"
        "    value = error\n"
        "finally:\n"
        "    final = value\n"
        "match subject:\n"
        "    case {\"x\": captured}:\n"
        "        result = captured\n"
        "    case _:\n"
        "        result = fallback\n",
        "pkg/mod.py",
        None,
    ),
    "comprehension_runtime_walrus": (
        "[(outer := value) for value in items for inner in values if (flag := inner)]\n"
        "outer\n"
        "flag\n"
        "with manager as resource:\n"
        "    bound = resource\n",
        "pkg/mod.py",
        None,
    ),
    "async_yield": (
        "async def worker(stream, manager):\n"
        "    async for item in stream:\n"
        "        async with manager as resource:\n"
        "            yield item\n",
        "pkg/mod.py",
        None,
    ),
    "relative_import": (
        "from ..services.api import target\n"
        "target()\n",
        "pkg/sub/mod.py",
        None,
    ),
    "resource_limit": (
        "first = 1\nsecond = 2\n",
        "pkg/mod.py",
        lineage_extraction.LineageExtractionLimits(max_nodes=1, max_ast_depth=100),
    ),
}


EXPECTED_HASHES = {
    "async_yield": "e6c709d1a5ef347b04ed888dd9fa055dbc5a24c33eb14ea1a489b60a15c7d731",
    "comprehension_runtime_walrus": "efbd682411093e174775282b2ce9d7012106d09c5180d73f5fbdd54ec45a2a6e",
    "if_for_frame_merge": "b12603da08418eef897fe090bc05a7783fd877ed6c2bfb5a1bfdcd20c7cdc305",
    "imports_alias_wildcard": "ad52d65bb4140b3e8ea6f21781c68e749f240358b5683e8648199972db597682",
    "relative_import": "10ee12f15c6cfc5ecb82511e18081534eb68b9e647ae0ec3d71f3611e510fb2e",
    "resource_limit": "40c592a9bfb86c5f6d4fe747fa2714a92794dafbc204e601ea4b475c07e06adb",
    "signature_defaults_local_call": "514593c03cb9b3dda00b0e2289a15781b7a7b2e131a89cb6e2f3e2fb2ad09d3c",
    "try_except_finally_match": "a1384557b901a8f8634f06da6e36c4df91007699f69b24a71d59c1b81da00299",
}


LEGACY_ANCHOR_FLOW_HASHES = {
    **EXPECTED_HASHES,
    "async_yield": "49eaf024dbbea341d333f1e705037be68c0fce45c6acaed23ad93a850d381016",
    "signature_defaults_local_call": "c7ff95a059aeeb7c5a3dc978f6a982fda491029286e0eeb8abe937fea4a2dfb5",
}


def test_lineage_extraction_equivalence_oracle() -> None:
    assert {
        name: _hash_result(source, source_key, limits)
        for name, (source, source_key, limits) in _CORPUS.items()
    } == EXPECTED_HASHES


def test_lineage_extraction_surface_delta_preserves_legacy_anchors_and_flows() -> None:
    assert {
        name: _hash_value(dataclasses.replace(_result(source, source_key, limits), surfaces=()))
        for name, (source, source_key, limits) in _CORPUS.items()
    } == LEGACY_ANCHOR_FLOW_HASHES


def test_lineage_extraction_public_compatibility() -> None:
    assert lineage_extraction.__all__ == [
        "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
        "ExtractedLineageContribution",
        "ExtractedLineageProvider",
        "LineageExtractionLimits",
        "ParsedLineageSourceInput",
        "build_local_occurrence_id",
        "extract_lineage_source_facts",
        "parse_local_occurrence_id",
    ]
    for name in (
        "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
        "ExtractedLineageContribution",
        "ExtractedLineageProvider",
        "LineageExtractionLimits",
        "ParsedLineageSourceInput",
        "build_local_occurrence_id",
        "extract_lineage_source_facts",
        "parse_local_occurrence_id",
    ):
        assert hasattr(lineage_extraction, name)
    for value in (
        lineage_extraction.LineageExtractionLimits,
        lineage_extraction.ParsedLineageSourceInput,
        lineage_extraction.ExtractedLineageContribution,
        lineage_extraction.ExtractedLineageProvider,
        lineage_extraction.build_local_occurrence_id,
        lineage_extraction.parse_local_occurrence_id,
    ):
        assert value.__module__ == "contextor.core.analysis.lineage_extraction"
