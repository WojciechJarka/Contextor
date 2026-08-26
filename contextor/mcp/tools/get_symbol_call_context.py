import json
from pathlib import Path

from contextor.core.analysis.state_manager import (
    canonical_artifact_consumption_targets,
    module_current_truth,
)
from contextor.mcp import query_helpers
from contextor.mcp import representation as mcp_rep
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import (
    LARGE_OUTPUT_WARNING_BYTES,
    guard_large_output,
    largest_fitting_prefix,
)


LARGE_NAMED_GRAPH_BYTES = 50 * 1024
_DIRECTIONS = {"callers", "callees", "both"}


def _error(code: str, **details) -> str:
    return json.dumps({"status": "error", "error": code, **details}, indent=2)


def _textual_miss_response(symbol: str, resolution: dict) -> str:
    if resolution.get("status") == "ambiguous":
        return json.dumps(resolution, indent=2)
    return _error(
        "unknown_symbol",
        symbol=symbol,
        similar_candidates=resolution.get("similar_candidates", []),
    )


def _edge_key(edge: tuple[str, str, int, str]) -> tuple:
    return edge[0], edge[1], edge[2], edge[3]


def _walk(
    facts: tuple[tuple[str, str, int, str], ...],
    symbol: str,
    direction: str,
    max_depth: int,
) -> list[dict]:
    frontier = {symbol}
    seen_nodes = {symbol}
    seen_edges: set[tuple[str, str, int, str]] = set()
    result: list[dict] = []
    for current_depth in range(1, max_depth + 1):
        if direction == "callers":
            candidates = [edge for edge in facts if edge[1] in frontier]
            adjacent_index = 0
        else:
            candidates = [edge for edge in facts if edge[0] in frontier]
            adjacent_index = 1
        next_frontier: set[str] = set()
        for raw_edge in sorted(set(candidates), key=_edge_key):
            edge = (
                str(raw_edge[0]),
                str(raw_edge[1]),
                int(raw_edge[2]),
                str(raw_edge[3]),
            )
            if edge not in seen_edges:
                seen_edges.add(edge)
                result.append(
                    {
                        "caller": edge[0],
                        "callee": edge[1],
                        "line": edge[2],
                        "call_kind": edge[3],
                        "depth": current_depth,
                    }
                )
            adjacent = edge[adjacent_index]
            if adjacent not in seen_nodes:
                next_frontier.add(adjacent)
        seen_nodes.update(next_frontier)
        frontier = next_frontier
        if not frontier:
            break
    return result


def _identity(item: dict) -> tuple:
    return item["caller"], item["callee"], item["line"], item["call_kind"]


def _ordered_union(callers: list[dict], callees: list[dict]) -> list[dict]:
    by_identity: dict[tuple, dict] = {}
    for item in callers + callees:
        identity = _identity(item)
        previous = by_identity.get(identity)
        if previous is None or item["depth"] < previous["depth"]:
            by_identity[identity] = item
    return sorted(
        by_identity.values(),
        key=lambda item: (item["depth"], *_identity(item)),
    )


def _known_symbols_for_module(state, module: str) -> set[str]:
    usage = (getattr(state, "module_usages", {}) or {}).get(module)
    if usage is None:
        return set()
    facts = tuple(getattr(usage, "symbol_calls", ()) or ())
    known_symbols = {
        endpoint for edge in facts for endpoint in (str(edge[0]), str(edge[1]))
    }
    known_symbols.update(
        canonical_artifact_consumption_targets(
            {module: (getattr(state, "artifacts", {}) or {}).get(module, {})}
        )
    )
    return known_symbols


def _queryable_artifact_registry(
    state,
    artifact_path_to_id: dict[str, str],
    *,
    module: str | None,
) -> tuple[dict[str, str], dict[str, str]]:
    usages = getattr(state, "module_usages", {}) or {}
    modules = [module] if module in usages else sorted(usages)
    queryable: set[str] = set()
    for candidate_module in modules:
        truth = module_current_truth(state, candidate_module)
        usage = usages[candidate_module]
        if not truth["available"] or not usage.symbol_calls_materialized:
            continue
        queryable.update(_known_symbols_for_module(state, candidate_module))
    scoped_path_to_id = {
        identity: str(artifact_path_to_id[identity])
        for identity in sorted(queryable)
        if identity in artifact_path_to_id
    }
    return scoped_path_to_id, {
        artifact_id: identity
        for identity, artifact_id in scoped_path_to_id.items()
    }


def _shape(
    *,
    symbol: str,
    module: str,
    direction: str,
    depth: int,
    requested_representation: str,
    selected_representation: str,
    caller_items: list[dict],
    callee_items: list[dict],
    selected_identities: set[tuple],
    total_edges: int,
    max_items: int | None,
    artifact_ids: dict[str, str] | None,
) -> dict:
    def encode(items: list[dict]) -> list[dict]:
        selected = [item for item in items if _identity(item) in selected_identities]
        if selected_representation == "named":
            return selected
        assert artifact_ids is not None
        return [
            {
                **item,
                "caller": artifact_ids[item["caller"]],
                "callee": artifact_ids[item["callee"]],
            }
            for item in selected
        ]

    callers_encoded = encode(caller_items)
    callees_encoded = encode(callee_items)
    returned_edges = len(selected_identities)
    result = {
        "status": "ok",
        "symbol": symbol,
        "module": module,
        "direction": direction,
        "depth": depth,
        "representation": selected_representation,
        "requested_representation": requested_representation,
        "scope": "intra_module",
        "total_edges": total_edges,
        "returned_edges": returned_edges,
        "truncated": returned_edges < total_edges,
        "callers": {
            "total": len(caller_items),
            "truncated": len(callers_encoded) < len(caller_items),
            "items": callers_encoded,
        },
        "callees": {
            "total": len(callee_items),
            "truncated": len(callees_encoded) < len(callee_items),
            "items": callees_encoded,
        },
        "expand": {},
        "data_source": "live_canonical_module_usages_symbol_calls",
    }
    if returned_edges < total_edges:
        next_limit = total_edges if max_items is None else min(total_edges, max_items * 2)
        result["expand"] = {"same_query_with": {"max_items": next_limit}}
    if selected_representation == "indexed":
        result["resolver"] = {
            "index_kind": "artifact",
            "resolve_via": "lookup_index_entries",
        }
    return result


def get_symbol_call_context(
    repo_path: str,
    symbol: str,
    direction: str = "both",
    depth: int = 1,
    max_items: int | None = 20,
    representation: str = "auto",
    allow_large_output: bool = False,
) -> str:
    if not isinstance(symbol, str):
        return _error("exact_qualified_symbol_required", expected="module::symbol")
    artifact_id_input = query_helpers.is_artifact_id(symbol)
    if not artifact_id_input and symbol.count("::") != 1:
        return _error("exact_qualified_symbol_required", expected="module::symbol")
    if direction not in _DIRECTIONS:
        return _error("invalid_direction", allowed=sorted(_DIRECTIONS))
    if isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= 3:
        return _error("invalid_depth", minimum=1, maximum=3)
    if (
        isinstance(max_items, bool)
        or (max_items is not None and (not isinstance(max_items, int) or max_items <= 0))
    ):
        return _error("invalid_max_items", expected="positive integer or null")
    if not mcp_rep.is_supported_representation(representation):
        return _error(
            "invalid_representation",
            allowed=sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
        )
    if not isinstance(allow_large_output, bool):
        return _error("invalid_allow_large_output")

    root = Path(repo_path).expanduser().resolve()
    try:
        registry_snapshot: tuple[dict, dict, dict, dict] | None = None
        if artifact_id_input:
            registry_snapshot = query_helpers.read_registries(root)
            _, _, artifact_path_to_id, artifact_id_to_path = registry_snapshot
            resolution = query_helpers.resolve_artifact_identity(
                symbol,
                artifact_path_to_id,
                artifact_id_to_path,
            )
            if resolution.get("status") != "resolved":
                return json.dumps(resolution, indent=2)
            symbol = str(resolution["artifact"])

        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return _error("canonical_live_state_unavailable")
        state = engine.state
        usages = getattr(state, "module_usages", {}) or {}

        if symbol.count("::") != 1:
            return _error("exact_qualified_symbol_required", expected="module::symbol")
        module, local_symbol = symbol.split("::", 1)
        if not module or not local_symbol:
            return _error("exact_qualified_symbol_required", expected="module::symbol")
        if module not in usages:
            if artifact_id_input:
                return _error("unknown_symbol", symbol=symbol)
            if registry_snapshot is None:
                registry_snapshot = query_helpers.read_registries(root)
            _, _, artifact_path_to_id, _ = registry_snapshot
            scoped_path_to_id, scoped_id_to_path = _queryable_artifact_registry(
                state,
                artifact_path_to_id,
                module=None,
            )
            resolution = query_helpers.resolve_artifact_identity(
                symbol,
                scoped_path_to_id,
                scoped_id_to_path,
            )
            return _textual_miss_response(symbol, resolution)
        truth = module_current_truth(state, module)
        if not truth["available"]:
            return json.dumps(
                {
                    "status": "stale",
                    "available": False,
                    "symbol": symbol,
                    "module": module,
                    **{key: value for key, value in truth.items() if key != "available"},
                },
                indent=2,
            )
        usage = usages[module]
        if not usage.symbol_calls_materialized:
            return _error(
                "symbol_calls_unmaterialized",
                symbol=symbol,
                module=module,
                available=False,
            )
        facts = tuple(getattr(usage, "symbol_calls", ()) or ())
        known_symbols = _known_symbols_for_module(state, module)
        if symbol not in known_symbols:
            if artifact_id_input:
                return _error("unknown_symbol", symbol=symbol)
            if registry_snapshot is None:
                registry_snapshot = query_helpers.read_registries(root)
            _, _, artifact_path_to_id, _ = registry_snapshot
            scoped_path_to_id, scoped_id_to_path = _queryable_artifact_registry(
                state,
                artifact_path_to_id,
                module=module,
            )
            resolution = query_helpers.resolve_artifact_identity(
                symbol,
                scoped_path_to_id,
                scoped_id_to_path,
            )
            return _textual_miss_response(symbol, resolution)

        callers = _walk(facts, symbol, "callers", depth) if direction in {"callers", "both"} else []
        callees = _walk(facts, symbol, "callees", depth) if direction in {"callees", "both"} else []
        complete = _ordered_union(callers, callees)
        selected = complete if max_items is None else complete[:max_items]
        selected_identities = {_identity(item) for item in selected}

        if registry_snapshot is None:
            registry_snapshot = query_helpers.read_registries(root)
        _, _, artifact_path_to_id, _ = registry_snapshot
        needed_symbols = {
            endpoint
            for item in selected
            for endpoint in (item["caller"], item["callee"])
        }
        artifact_ids = {
            name: str(artifact_path_to_id[name])
            for name in needed_symbols
            if name in artifact_path_to_id
        }
        indexed_available = len(artifact_ids) == len(needed_symbols)

        named_candidate = _shape(
            symbol=symbol,
            module=module,
            direction=direction,
            depth=depth,
            requested_representation=representation,
            selected_representation="named",
            caller_items=callers,
            callee_items=callees,
            selected_identities=selected_identities,
            total_edges=len(complete),
            max_items=max_items,
            artifact_ids=None,
        )
        indexed_candidate = (
            _shape(
                symbol=symbol,
                module=module,
                direction=direction,
                depth=depth,
                requested_representation=representation,
                selected_representation="indexed",
                caller_items=callers,
                callee_items=callees,
                selected_identities=selected_identities,
                total_edges=len(complete),
                max_items=max_items,
                artifact_ids=artifact_ids,
            )
            if indexed_available
            else None
        )
        named_bytes = mcp_rep.serialized_json_bytes(named_candidate)
        indexed_bytes = (
            mcp_rep.serialized_json_bytes(indexed_candidate)
            if indexed_candidate is not None
            else None
        )
        bytes_saved = named_bytes - indexed_bytes if indexed_bytes is not None else None

        if representation == "indexed" and indexed_candidate is None:
            return _error(
                "indexed_identity_unavailable",
                missing_symbols=sorted(needed_symbols - set(artifact_ids)),
                suggested_action="Use representation='named' or refresh persistent identities.",
            )
        force_indexed = named_bytes > LARGE_NAMED_GRAPH_BYTES
        if force_indexed and indexed_candidate is None:
            return _error(
                "large_named_output_requires_indexed_identities",
                named_candidate_bytes=named_bytes,
            )
        if representation == "indexed" or force_indexed:
            result = indexed_candidate
            reason = (
                "named_candidate_exceeded_51200_bytes"
                if force_indexed
                else "explicit_indexed"
            )
        elif representation == "auto" and indexed_candidate is not None and bytes_saved is not None and bytes_saved >= mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED:
            result = indexed_candidate
            reason = "auto_indexed_material_saving"
        else:
            result = named_candidate
            reason = "explicit_named" if representation == "named" else "auto_named"
        assert result is not None
        result["representation_decision"] = {
            "selected": result["representation"],
            "named_candidate_bytes": named_bytes,
            "indexed_candidate_bytes": indexed_bytes,
            "bytes_saved": bytes_saved,
            "reason": reason,
        }
        serialized = json.dumps(result, indent=2, ensure_ascii=False)
        full_output_bytes = len(serialized.encode("utf-8"))

        if (
            full_output_bytes > LARGE_OUTPUT_WARNING_BYTES
            and not allow_large_output
            and result["returned_edges"] > 0
        ):
            selected_representation = result["representation"]
            requested_edge_count = result["returned_edges"]
            original_expand = result.get("expand", {})
            original_representation_decision = dict(result["representation_decision"])

            def _build_bounded(count: int) -> str:
                bounded_identities = {
                    _identity(item)
                    for item in selected[:count]
                }

                candidate = _shape(
                    symbol=symbol,
                    module=module,
                    direction=direction,
                    depth=depth,
                    requested_representation=representation,
                    selected_representation=selected_representation,
                    caller_items=callers,
                    callee_items=callees,
                    selected_identities=bounded_identities,
                    total_edges=len(complete),
                    max_items=max_items,
                    artifact_ids=(
                        artifact_ids
                        if selected_representation == "indexed"
                        else None
                    ),
                )

                # Auto-bounding is only an output-size projection.
                # Preserve the original caller max_items expansion contract and the
                # representation decision made for the originally requested candidate.
                candidate["expand"] = original_expand
                candidate["representation_decision"] = dict(
                    original_representation_decision
                )

                candidate["_output"] = {
                    "auto_bounded": True,
                    "full_output_bytes": full_output_bytes,
                    "warning_threshold_bytes": LARGE_OUTPUT_WARNING_BYTES,
                    "bounded_collection": "edges",
                    "requested_count": requested_edge_count,
                    "returned_count": candidate["returned_edges"],
                    "retry": {
                        "allow_large_output": True,
                    },
                }

                return json.dumps(
                    candidate,
                    indent=2,
                    ensure_ascii=False,
                )

            bounded = largest_fitting_prefix(
                requested_edge_count,
                _build_bounded,
                min_count=1,
            )

            if bounded is not None:
                return bounded[0]

        guarded = guard_large_output(
            serialized,
            allow_large_output=allow_large_output,
            requested_count=result["returned_edges"],
            reason="Selected symbol-call context exceeds the recommended context size.",
            retry_instruction=(
                "Reduce max_items/depth, narrow direction, select indexed representation, "
                "or repeat the identical get_symbol_call_context request with allow_large_output=true."
            ),
        )
        if guarded != serialized:
            warning = json.loads(guarded)
            warning.update(
                {
                    "threshold_bytes": LARGE_OUTPUT_WARNING_BYTES,
                    "total_edges": result["total_edges"],
                    "returned_edges": result["returned_edges"],
                    "selected_representation": result["representation"],
                    "named_candidate_bytes": named_bytes,
                    "indexed_candidate_bytes": indexed_bytes,
                }
            )
            return json.dumps(warning, indent=2)
        return serialized
    except Exception as exc:
        return _error("symbol_call_context_failed", detail=str(exc))
