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


def _hash_result(source: str, source_key: str, limits=None) -> str:
    source_fingerprint = hashlib.sha256(source.encode("utf-8")).hexdigest()
    result = lineage_extraction.extract_lineage_source_facts(
        ast.parse(source),
        source_key=source_key,
        source_fingerprint=source_fingerprint,
        **({} if limits is None else {"limits": limits}),
    )
    oracle_bytes = json.dumps(
        _canonical(result),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(oracle_bytes).hexdigest()


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
    "async_yield": "110cd0c1d520261bffe673d6e0f1df573b68ed4653be674bcb762faacdf27bf9",
    "comprehension_runtime_walrus": "35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9",
    "if_for_frame_merge": "f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a",
    "imports_alias_wildcard": "7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8",
    "relative_import": "44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95",
    "resource_limit": "40c592a9bfb86c5f6d4fe747fa2714a92794dafbc204e601ea4b475c07e06adb",
    "signature_defaults_local_call": "4d6984e8211918d2e84e976d5fda32f59aed9247d52821cafc688242c6f6533b",
    "try_except_finally_match": "ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f",
}


def test_lineage_extraction_equivalence_oracle() -> None:
    assert {
        name: _hash_result(source, source_key, limits)
        for name, (source, source_key, limits) in _CORPUS.items()
    } == EXPECTED_HASHES


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
