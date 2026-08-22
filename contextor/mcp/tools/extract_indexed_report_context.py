import json
from pathlib import Path

from contextor.core import report_query
from contextor.mcp import query_helpers
from contextor.mcp import representation as mcp_rep
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import report_helpers


def extract_indexed_report_context(
    repo_path: str,
    query: str,
    report_path: str = "",
    resolve_indices: bool = True,
    public_api_only: bool = False,
    max_items: int | None = 20,
    fields: list[str] | None = None,
    evidence_limit: int | None = 3,
    representation: str | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        if representation is not None and not mcp_rep.is_supported_representation(representation):
            return json.dumps(
                {
                    "error": "Unsupported representation for extract_indexed_report_context",
                    "representation": representation,
                    "allowed_representations": sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
                },
                indent=2,
            )

        if report_path:
            selected_path = Path(report_path).expanduser()
            if not selected_path.is_absolute():
                selected_path = root / selected_path
            selected_path = selected_path.resolve()
        else:
            selected_path = report_helpers.get_canonical_report(
                root, f"{root.name}_artifacts_compact.json"
            )
        if not selected_path or not selected_path.is_file():
            return "Error: No indexed artifact report found. Run analysis or pass report_path."

        report = json.loads(selected_path.read_text(encoding="utf-8"))
        engine = mcp_runtime.get_or_init_engine(root)
        module_paths = None
        if engine:
            module_paths = {
                str(module_name): str(module.path)
                for module_name, module in engine.state.modules.items()
                if getattr(module, "path", None)
            }
        catalog = report_query.catalog_from_registry(str(root), module_paths=module_paths)
        if public_api_only:
            report = report_query.filter_public_artifact_report(report, catalog)

        # ------------------------------------------------------------------
        # LEGACY BRANCH: representation is None (100% legacy A12.3 behavior)
        # ------------------------------------------------------------------
        if representation is None:
            result = report_query.query_indexed_report(
                report,
                query,
                catalog,
                repo_root=str(root),
                resolve_indices=resolve_indices,
            )
            artifact_entries = sorted(result.get("artifacts", {}).items())
            selected_entries, total_artifacts, artifacts_truncated = query_helpers.bounded_items(
                artifact_entries, max_items
            )

            has_nested_truncation = False
            bounded_artifacts = {}
            for art_key, art_entry in selected_entries:
                entry = dict(art_entry)
                if resolve_indices:
                    raw_consumers = list(entry.get("consumer_modules", []))
                    c_total = entry.get("consumer_count", len(raw_consumers))
                    bounded_c, _, _ = query_helpers.bounded_items(raw_consumers, evidence_limit)
                    c_trunc = len(bounded_c) < c_total
                    entry["consumer_count"] = c_total
                    entry["consumer_modules"] = bounded_c
                    entry["consumer_modules_truncated"] = c_trunc
                    if c_trunc:
                        has_nested_truncation = True
                else:
                    raw_indices = list(entry.get("consumer_module_indices", []))
                    c_total = entry.get("consumer_count", len(raw_indices))
                    bounded_c, _, _ = query_helpers.bounded_items(raw_indices, evidence_limit)
                    c_trunc = len(bounded_c) < c_total
                    entry["consumer_count"] = c_total
                    entry["consumer_module_indices"] = bounded_c
                    entry["consumer_module_indices_truncated"] = c_trunc
                    if c_trunc:
                        has_nested_truncation = True
                bounded_artifacts[art_key] = entry

            result["artifacts"] = bounded_artifacts
            result["artifact_count"] = len(bounded_artifacts)
            result["total_artifact_count"] = total_artifacts
            result["truncated"] = artifacts_truncated
            result["data_source"] = str(selected_path)

            include_expand = has_nested_truncation and (fields is None or "artifacts" in fields)
            expand_descriptor = None
            if include_expand:
                expand_descriptor = {
                    "available": True,
                    "reason": "Nested consumer evidence truncated by evidence_limit.",
                    "retry_with_full_evidence": {
                        "query": query,
                        "report_path": report_path,
                        "resolve_indices": resolve_indices,
                        "public_api_only": public_api_only,
                        "max_items": max_items,
                        "fields": fields,
                        "evidence_limit": None,
                    },
                    "retry_fully_lossless": {
                        "query": query,
                        "report_path": report_path,
                        "resolve_indices": resolve_indices,
                        "public_api_only": public_api_only,
                        "max_items": None,
                        "fields": fields,
                        "evidence_limit": None,
                    },
                }

            if fields is not None:
                allowed_fields = set(result)
                unknown_fields = sorted(set(fields) - allowed_fields)
                if unknown_fields:
                    return json.dumps({
                        "error": "Unsupported fields for extract_indexed_report_context",
                        "unknown_fields": unknown_fields,
                        "allowed_fields": sorted(allowed_fields),
                    }, indent=2)
                result = {field: result[field] for field in fields}

            if expand_descriptor is not None:
                result["expand"] = expand_descriptor

            return json.dumps(result, indent=2, ensure_ascii=False)

        # ------------------------------------------------------------------
        # NON-NONE REPRESENTATION BRANCH: S2 Canonical Scope Selection
        # ------------------------------------------------------------------
        domain_allowed = {
            "resolution",
            "artifact_count",
            "artifacts",
            "selection",
            "diagnostics",
            "total_artifact_count",
            "truncated",
            "data_source",
        }
        if fields is not None:
            unknown_fields = sorted(set(fields) - domain_allowed)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for extract_indexed_report_context",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(domain_allowed),
                }, indent=2)

        res_base = report_query.query_indexed_report(
            report,
            query,
            catalog,
            repo_root=str(root),
            resolve_indices=False,
        )
        raw_blocks = res_base.get("artifacts", {})
        sorted_blocks = sorted(raw_blocks.items())
        selected_blocks_tuple, total_artifacts, artifacts_truncated = query_helpers.bounded_items(
            sorted_blocks, max_items
        )
        selected_blocks = dict(selected_blocks_tuple)

        def _build_candidate_response(target_rep: str, expand_rep: str) -> dict:
            resolve_names = (target_rep == "named")
            blocks_rewritten, diagnostics = report_query.rewrite_selected_indices(
                selected_blocks, catalog, resolve_names=resolve_names
            )
            has_nested_trunc = False
            bounded_artifacts = {}
            for art_key, art_entry in blocks_rewritten.items():
                entry = dict(art_entry)
                if resolve_names:
                    raw_c = list(entry.get("consumer_modules", []))
                    c_total = entry.get("consumer_count", len(raw_c))
                    bounded_c, _, _ = query_helpers.bounded_items(raw_c, evidence_limit)
                    c_trunc = len(bounded_c) < c_total
                    entry["consumer_count"] = c_total
                    entry["consumer_modules"] = bounded_c
                    entry["consumer_modules_truncated"] = c_trunc
                    if c_trunc:
                        has_nested_trunc = True
                else:
                    raw_c = list(entry.get("consumer_module_indices", []))
                    c_total = entry.get("consumer_count", len(raw_c))
                    bounded_c, _, _ = query_helpers.bounded_items(raw_c, evidence_limit)
                    c_trunc = len(bounded_c) < c_total
                    entry["consumer_count"] = c_total
                    entry["consumer_module_indices"] = bounded_c
                    entry["consumer_module_indices_truncated"] = c_trunc
                    if c_trunc:
                        has_nested_trunc = True
                bounded_artifacts[art_key] = entry

            merged_diagnostics = {
                "omitted_blocks": list(res_base.get("diagnostics", {}).get("omitted_blocks", [])),
                "dropped_references": list(res_base.get("diagnostics", {}).get("dropped_references", [])),
                "resolved_from_recovery": list(res_base.get("diagnostics", {}).get("resolved_from_recovery", [])),
            }
            for rec in diagnostics.get("resolved_from_recovery", []):
                if rec not in merged_diagnostics["resolved_from_recovery"]:
                    merged_diagnostics["resolved_from_recovery"].append(rec)

            cand_res = {
                "resolution": res_base.get("resolution", {}),
                "artifact_count": len(bounded_artifacts),
                "artifacts": bounded_artifacts,
                "selection": res_base.get("selection", []),
                "diagnostics": merged_diagnostics,
                "total_artifact_count": total_artifacts,
                "truncated": artifacts_truncated,
                "data_source": str(selected_path),
            }

            include_expand = has_nested_trunc and (fields is None or "artifacts" in fields)
            expand_descriptor = None
            if include_expand:
                expand_descriptor = {
                    "available": True,
                    "reason": "Nested consumer evidence truncated by evidence_limit.",
                    "retry_with_full_evidence": {
                        "query": query,
                        "report_path": report_path,
                        "resolve_indices": resolve_indices,
                        "public_api_only": public_api_only,
                        "max_items": max_items,
                        "fields": fields,
                        "evidence_limit": None,
                        "representation": expand_rep,
                    },
                    "retry_fully_lossless": {
                        "query": query,
                        "report_path": report_path,
                        "resolve_indices": resolve_indices,
                        "public_api_only": public_api_only,
                        "max_items": None,
                        "fields": fields,
                        "evidence_limit": None,
                        "representation": expand_rep,
                    },
                }

            if fields is not None:
                cand_res = {f: cand_res[f] for f in fields if f in cand_res}

            if expand_descriptor is not None:
                cand_res["expand"] = expand_descriptor

            if target_rep == "named":
                cand_res["representation"] = "named"
                if expand_rep == "auto":
                    cand_res["requested_representation"] = "auto"
            elif target_rep == "indexed":
                cand_res["representation"] = "indexed"
                cand_res["resolve_via"] = "lookup_index_entries"

            return cand_res

        if representation == "named":
            res = _build_candidate_response("named", "named")
            return json.dumps(res, indent=2, ensure_ascii=False)

        if representation == "indexed":
            res = _build_candidate_response("indexed", "indexed")
            return json.dumps(res, indent=2, ensure_ascii=False)

        # representation == "auto"
        if fields is not None and "artifacts" not in fields:
            res = _build_candidate_response("named", "auto")
            return json.dumps(res, indent=2, ensure_ascii=False)

        named_candidate = _build_candidate_response("named", "named")
        indexed_candidate = _build_candidate_response("indexed", "indexed")

        named_ids = [
            entry.get("artifact_id")
            for entry in named_candidate.get("artifacts", {}).values()
            if isinstance(entry, dict)
        ]
        indexed_ids = [
            entry.get("artifact_id")
            for entry in indexed_candidate.get("artifacts", {}).values()
            if isinstance(entry, dict)
        ]
        if named_ids != indexed_ids:
            # Failsafe: if candidate identity parity fails, return direct named
            res = _build_candidate_response("named", "auto")
            return json.dumps(res, indent=2, ensure_ascii=False)

        sizes = mcp_rep.representation_size_stats(named_candidate, indexed_candidate)
        if sizes["bytes_saved"] < mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED:
            res = _build_candidate_response("named", "auto")
            return json.dumps(res, indent=2, ensure_ascii=False)

        # Decision response required
        evidence = []
        for art_id, blk in selected_blocks_tuple[:3]:
            cat_name = (
                catalog.artifacts.get(art_id)
                or (catalog.recovered_artifacts or {}).get(art_id)
                or art_id
            )
            evidence.append({
                "artifact_id": str(art_id),
                "artifact": str(cat_name),
                "kind": blk.get("kind", "unknown"),
            })

        options = {
            "named": {
                "query": query,
                "report_path": report_path,
                "resolve_indices": resolve_indices,
                "public_api_only": public_api_only,
                "max_items": max_items,
                "fields": fields,
                "evidence_limit": evidence_limit,
                "representation": "named",
            },
            "indexed": {
                "query": query,
                "report_path": report_path,
                "resolve_indices": resolve_indices,
                "public_api_only": public_api_only,
                "max_items": max_items,
                "fields": fields,
                "evidence_limit": evidence_limit,
                "representation": "indexed",
            },
        }

        decision_res = {
            "status": "representation_decision_required",
            "requested_representation": "auto",
            "query": query,
            "total_artifact_count": total_artifacts,
            "artifact_count": len(selected_blocks),
            "truncated": artifacts_truncated,
            "sizes": sizes,
            "evidence": evidence,
            "options": options,
        }
        return json.dumps(decision_res, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error extracting indexed report context: {e}"
