import json
from pathlib import Path

from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers
from contextor.mcp import representation as mcp_rep


_COMPACT_ARTIFACT_LIMIT = 10
_COMPACT_CONSUMER_EVIDENCE_LIMIT = 3
_DOMAIN_FIELDS = {
    "module",
    "module_id",
    "artifact_count",
    "total_artifact_count",
    "truncated",
    "symbol_filter",
    "data_sources",
    "complete_symbol_catalog",
    "artifacts",
}


def get_artifacts_for_module(
    repo_path: str,
    module_name: str = "",
    include_consumers: bool = True,
    symbol_filter: str = "",
    limit: int | None = 50,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
    representation: str = "named",
    module: str | None = None,
) -> str:
    if not mcp_rep.is_supported_representation(representation):
        return json.dumps(
            {
                "error": "Unsupported representation for get_artifacts_for_module",
                "representation": representation,
                "allowed_representations": sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
            },
            indent=2,
        )

    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    normalized_module_name = module_name.strip()
    normalized_module = module.strip() if module is not None else ""

    if (
        normalized_module_name
        and normalized_module
        and normalized_module_name != normalized_module
    ):
        return json.dumps(
            {
                "status": "error",
                "error": "module_name and module must match when both are provided.",
            },
            indent=2,
        )

    module_name = normalized_module or normalized_module_name
    if not module_name:
        return json.dumps(
            {
                "status": "error",
                "error": "module_name or module is required.",
            },
            indent=2,
        )

    # Normalise file-path input to dotted module name.
    target_path = Path(module_name)
    if target_path.is_absolute() or module_name.endswith(".py") or "/" in module_name or "\\" in module_name:
        if target_path.is_absolute():
            try:
                rel_path = target_path.relative_to(root)
            except ValueError:
                rel_path = target_path
        else:
            rel_path = target_path

        parts = list(rel_path.parts)
        if parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
            if parts[-1] == "__init__":
                parts.pop()

        module_name = ".".join(parts)

    try:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."
        state = engine.state
        unavailable = query_helpers.module_truth_unavailable(state, module_name)
        if unavailable:
            return json.dumps(unavailable, indent=2)
        live_modules = getattr(state, "modules", {}) or {}
        live_artifact_catalog = getattr(state, "artifacts", {}) or {}
        live_artifacts = live_artifact_catalog.get(module_name, {})
        mod_compact_id = mod_path_to_id.get(module_name)
        live_module = live_modules.get(module_name)
        if not mod_compact_id and live_module is not None:
            mod_compact_id = getattr(live_module, "module_id", None)
            if mod_compact_id is None and isinstance(live_module, dict):
                mod_compact_id = live_module.get("module_id")
        if not mod_compact_id and live_module is None and not live_artifacts:
            return (
                f"Module '{module_name}' not found in registry or canonical LIVE state. "
                "Check the module name or run an analysis."
            )

        if fields is not None:
            unknown_fields = sorted(set(fields) - _DOMAIN_FIELDS)
            if unknown_fields:
                return json.dumps(
                    {
                        "error": "Unsupported fields for get_artifacts_for_module",
                        "unknown_fields": unknown_fields,
                        "allowed_fields": sorted(_DOMAIN_FIELDS),
                    },
                    indent=2,
                )

        canonical_catalog = query_helpers.canonical_symbol_catalog(live_artifacts)
        if symbol_filter:
            term = symbol_filter.lower()
            candidate_symbols = [
                (s, kind)
                for s, kind in canonical_catalog.items()
                if term in s.lower()
            ]
        else:
            candidate_symbols = list(canonical_catalog.items())

        total_artifact_count = len(candidate_symbols)
        requested_scope_count = (
            total_artifact_count
            if limit is None
            else min(total_artifact_count, max(0, int(limit)))
        )
        artifact_count = (
            min(requested_scope_count, _COMPACT_ARTIFACT_LIMIT)
            if compact
            else requested_scope_count
        )
        truncated = artifact_count < total_artifact_count
        presentation_truncated = compact and (artifact_count < requested_scope_count)

        # Fields gating: if "artifacts" is excluded by fields projection
        if fields is not None and "artifacts" not in fields:
            res = {
                "module": module_name,
                "module_id": mod_compact_id,
                "artifact_count": artifact_count,
                "total_artifact_count": total_artifact_count,
                "truncated": truncated,
                "symbol_filter": symbol_filter or None,
                "data_sources": ["live_symbol_state"],
                "complete_symbol_catalog": True,
                "artifacts": {},
            }
            if presentation_truncated:
                exp = {
                    "compact": False,
                    "limit": limit,
                    "evidence_limit": evidence_limit,
                    "include_consumers": include_consumers,
                    "symbol_filter": symbol_filter,
                    "representation": representation,
                    "fields": list(fields),
                }
                res["expand"] = exp
            res = {f: res[f] for f in fields if f in res}
            return json.dumps(res, indent=2)

        # Build and rank candidate entries
        candidate_data = []
        if include_consumers:
            if compact:
                for symbol, kind in candidate_symbols:
                    full_name = f"{module_name}::{symbol}"
                    art_id = art_path_to_id.get(full_name)
                    key = art_id or full_name
                    cons_list = query_helpers.canonical_symbol_consumers(
                        state, module_name, symbol
                    )
                    candidate_data.append(
                        {
                            "symbol": symbol,
                            "kind": kind,
                            "full_name": full_name,
                            "artifact_id": art_id,
                            "key": key,
                            "raw_consumers": cons_list,
                            "consumers_total": len(cons_list),
                        }
                    )
                candidate_data.sort(
                    key=lambda item: (
                        -item["consumers_total"],
                        item["symbol"].lower(),
                        item["key"],
                    )
                )
            else:
                for symbol, kind in candidate_symbols:
                    full_name = f"{module_name}::{symbol}"
                    art_id = art_path_to_id.get(full_name)
                    key = art_id or full_name
                    candidate_data.append(
                        {
                            "symbol": symbol,
                            "kind": kind,
                            "full_name": full_name,
                            "artifact_id": art_id,
                            "key": key,
                            "raw_consumers": None,
                            "consumers_total": None,
                        }
                    )
                candidate_data.sort(
                    key=lambda item: (item["symbol"].lower(), item["key"])
                )
        else:
            for symbol, kind in candidate_symbols:
                full_name = f"{module_name}::{symbol}"
                art_id = art_path_to_id.get(full_name)
                key = art_id or full_name
                candidate_data.append(
                    {
                        "symbol": symbol,
                        "kind": kind,
                        "full_name": full_name,
                        "artifact_id": art_id,
                        "key": key,
                        "raw_consumers": [],
                        "consumers_total": 0,
                    }
                )
            candidate_data.sort(
                key=lambda item: (item["symbol"].lower(), item["key"])
            )

        selected_candidates = candidate_data[:artifact_count]

        if not compact and include_consumers:
            for item in selected_candidates:
                if item["raw_consumers"] is None:
                    c_list = query_helpers.canonical_symbol_consumers(
                        state, module_name, item["symbol"]
                    )
                    item["raw_consumers"] = c_list
                    item["consumers_total"] = len(c_list)

        def _build_artifacts_dict(target_rep: str) -> tuple[dict, list[str], int]:
            res_artifacts = {}
            missing_mods = []
            encoded_identities_count = 0

            live_symbols = live_artifacts.get("symbols", {})
            signatures = live_symbols.get("signatures", {}) or {}

            for item in selected_candidates:
                symbol = item["symbol"]
                entry = {
                    "artifact_id": item["artifact_id"],
                    "symbol": symbol,
                    "full_name": item["full_name"],
                    "kind": item["kind"],
                    "signature": signatures.get(symbol),
                }
                if include_consumers:
                    c_total = item["consumers_total"]
                    raw_c = item["raw_consumers"]
                    if compact:
                        if evidence_limit is None:
                            c_limit = _COMPACT_CONSUMER_EVIDENCE_LIMIT
                        else:
                            c_limit = min(
                                _COMPACT_CONSUMER_EVIDENCE_LIMIT,
                                max(0, int(evidence_limit)),
                            )
                        ev_items = raw_c[:c_limit]
                        c_trunc = c_total > len(ev_items)

                        if target_rep == "indexed":
                            for m in ev_items:
                                if m not in mod_path_to_id:
                                    missing_mods.append(m)
                            mapped_ev = [
                                str(mod_path_to_id[m])
                                for m in ev_items
                                if m in mod_path_to_id
                            ]
                            entry["consumers"] = {
                                "total": c_total,
                                "truncated": c_trunc,
                                "evidence": mapped_ev,
                            }
                            encoded_identities_count += len(mapped_ev)
                        else:
                            entry["consumers"] = {
                                "total": c_total,
                                "truncated": c_trunc,
                                "evidence": list(ev_items),
                            }
                            encoded_identities_count += len(ev_items)
                    else:
                        if evidence_limit is None:
                            items_list = raw_c
                        else:
                            items_list = raw_c[: max(0, int(evidence_limit))]
                        c_trunc = c_total > len(items_list)

                        if target_rep == "indexed":
                            for m in items_list:
                                if m not in mod_path_to_id:
                                    missing_mods.append(m)
                            mapped_items = [
                                str(mod_path_to_id[m])
                                for m in items_list
                                if m in mod_path_to_id
                            ]
                            entry["consumers"] = {
                                "total": c_total,
                                "truncated": c_trunc,
                                "items": mapped_items,
                            }
                            encoded_identities_count += len(mapped_items)
                        else:
                            entry["consumers"] = {
                                "total": c_total,
                                "truncated": c_trunc,
                                "items": list(items_list),
                            }
                            encoded_identities_count += len(items_list)
                res_artifacts[item["key"]] = entry

            return res_artifacts, sorted(set(missing_mods)), encoded_identities_count

        def _make_expand(rep: str) -> dict:
            exp = {
                "compact": False,
                "limit": limit,
                "evidence_limit": evidence_limit,
                "include_consumers": include_consumers,
                "symbol_filter": symbol_filter,
                "representation": rep,
            }
            if fields is not None:
                exp["fields"] = list(fields)
            return exp

        def _assemble_normal_response(
            artifacts_dict: dict,
            rep: str,
            encoded_count: int,
            fallback_missing: bool = False,
        ) -> dict:
            res = {
                "module": module_name,
                "module_id": mod_compact_id,
                "artifact_count": len(artifacts_dict),
                "total_artifact_count": total_artifact_count,
                "truncated": truncated,
                "symbol_filter": symbol_filter or None,
                "data_sources": ["live_symbol_state"],
                "complete_symbol_catalog": True,
                "artifacts": artifacts_dict,
            }
            if fields is not None:
                res = {f: res[f] for f in fields if f in res}

            if presentation_truncated:
                res["expand"] = _make_expand(rep)

            if rep == "indexed" and encoded_count > 0:
                res["consumer_representation"] = {
                    "representation": "indexed",
                    "index_kind": "module",
                    "resolve_via": "lookup_index_entries",
                }
            elif rep == "auto" and fallback_missing:
                res["consumer_representation"] = {
                    "representation": "named",
                    "requested_representation": "auto",
                    "indexed_representation_available": False,
                    "reason": "missing_module_ids",
                }
            elif rep == "auto" and encoded_count > 0:
                res["consumer_representation"] = {
                    "representation": "named",
                    "requested_representation": "auto",
                }

            return res

        if representation == "named":
            named_artifacts, _, enc_count = _build_artifacts_dict("named")
            res = _assemble_normal_response(named_artifacts, "named", enc_count)
            return json.dumps(res, indent=2)

        if representation == "indexed":
            indexed_artifacts, missing_mods, enc_count = _build_artifacts_dict("indexed")
            if missing_mods:
                return json.dumps(
                    {
                        "error": "Cannot fulfill indexed representation for get_artifacts_for_module",
                        "reason": "missing_module_ids",
                        "missing_module_names": missing_mods,
                        "representation": "indexed",
                    },
                    indent=2,
                )
            res = _assemble_normal_response(indexed_artifacts, "indexed", enc_count)
            return json.dumps(res, indent=2)

        # representation == "auto"
        if compact:
            named_artifacts, _, enc_count = _build_artifacts_dict("named")
            res = _assemble_normal_response(named_artifacts, "auto", enc_count)
            return json.dumps(res, indent=2)

        # compact is False and representation == "auto"
        if not include_consumers:
            named_artifacts, _, enc_count = _build_artifacts_dict("named")
            res = _assemble_normal_response(named_artifacts, "named", 0)
            return json.dumps(res, indent=2)

        named_artifacts, _, named_enc_count = _build_artifacts_dict("named")
        if named_enc_count == 0:
            res = _assemble_normal_response(named_artifacts, "named", 0)
            return json.dumps(res, indent=2)

        indexed_artifacts, missing_mods, indexed_enc_count = _build_artifacts_dict("indexed")
        if missing_mods:
            res = _assemble_normal_response(
                named_artifacts, "auto", named_enc_count, fallback_missing=True
            )
            return json.dumps(res, indent=2)

        named_candidate = _assemble_normal_response(named_artifacts, "named", named_enc_count)
        indexed_candidate = _assemble_normal_response(indexed_artifacts, "indexed", indexed_enc_count)

        sizes = mcp_rep.representation_size_stats(named_candidate, indexed_candidate)

        if sizes["bytes_saved"] < mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED:
            res = _assemble_normal_response(named_artifacts, "auto", named_enc_count)
            return json.dumps(res, indent=2)

        # Decision required
        salience_view = sorted(
            selected_candidates,
            key=lambda item: (
                -(item["consumers_total"] or 0),
                item["symbol"].lower(),
                item["key"],
            ),
        )
        decision_evidence = []
        for item in salience_view[:3]:
            decision_evidence.append(
                {
                    "artifact_id": item["artifact_id"],
                    "symbol": item["symbol"],
                    "consumers_total": item["consumers_total"],
                }
            )

        options = {
            "named": {
                "representation": "named",
                "compact": False,
                "limit": limit,
                "evidence_limit": evidence_limit,
                "include_consumers": include_consumers,
                "symbol_filter": symbol_filter,
            },
            "indexed": {
                "representation": "indexed",
                "compact": False,
                "limit": limit,
                "evidence_limit": evidence_limit,
                "include_consumers": include_consumers,
                "symbol_filter": symbol_filter,
            },
        }
        if fields is not None:
            options["named"]["fields"] = list(fields)
            options["indexed"]["fields"] = list(fields)

        if len(selected_candidates) > 10:
            b_evidence_limit = (
                min(5, evidence_limit) if evidence_limit is not None else 5
            )
            options["bounded_named"] = {
                "representation": "named",
                "compact": False,
                "limit": min(10, len(selected_candidates)),
                "evidence_limit": b_evidence_limit,
                "include_consumers": include_consumers,
                "symbol_filter": symbol_filter,
            }
            if fields is not None:
                options["bounded_named"]["fields"] = list(fields)

        decision_res = {
            "status": "representation_decision_required",
            "requested_representation": "auto",
            "module": module_name,
            "module_id": mod_compact_id,
            "total_artifact_count": total_artifact_count,
            "truncated": total_artifact_count > len(decision_evidence),
            "decision_scope_count": len(selected_candidates),
            "scope_truncated": total_artifact_count > len(selected_candidates),
            "evidence": decision_evidence,
            "sizes": sizes,
            "options": options,
        }
        return json.dumps(decision_res, indent=2)
    except Exception as e:
        return f"Error reading artifacts for module: {e}"
