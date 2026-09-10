STATUS=BLOCKED

CANONICAL_STATE=
\`\`\`text
Error calling tool 'describe_canonical_state': 1 validation error for call[describe_canonical_state]
repo_path
  Unexpected keyword argument [type=unexpected_keyword_argument, input_value='C:\\Temp\\Contextor_Repo', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/unexpected_keyword_argument

{
  "job_id": "780102abf11e4849a7de243db02a46ee",
  "operation": "single_file",
  "repo_path": "C:\\Temp\\Contextor_Repo",
  "target": "C:\\Temp\\Contextor_Repo\\contextor\\core\\analysis\\lineage_extraction_state.py",
  "status": "completed",
  "created_at": "2026-09-10T07:29:28.344763+00:00",
  "started_at": "2026-09-10T07:29:28.353764+00:00",
  "completed_at": "2026-09-10T07:29:41.806699+00:00",
  "updated_at": "2026-09-10T07:29:41.807701+00:00",
  "message": "Analysis completed successfully.",
  "error": null,
  "live_publish_status": "not_applicable",
  "live_publish_revision": null,
  "live_publish_warning": null,
  "reused": false,
  "diagnostics_summary": {
    "syntax_errors": {
      "count": null,
      "availability": "unavailable"
    },
    "name_collisions": {
      "count": null,
      "critical": null,
      "warning": null,
      "info": null,
      "availability": "unavailable"
    },
    "cycles": {
      "count": null,
      "availability": "unavailable"
    },
    "attention_required": false,
    "availability": {
      "syntax_errors": "unavailable",
      "name_collisions": "unavailable",
      "cycles": "unavailable"
    }
  },
  "diagnostics_attention_required": false
}
\`\`\`

EDIT_CONTEXT_FACADE=
\`\`\`text
{
  "file": "contextor/core/analysis/lineage_extraction.py",
  "file_exists": true,
  "target": "contextor/core/analysis/lineage_extraction.py",
  "target_kind": "module",
  "status": "available",
  "module": "contextor.core.analysis.lineage_extraction",
  "module_id": "351/1",
  "layer": "runtime",
  "entrypoint": false,
  "risk_score": 0.1074,
  "syntax_diagnostics": {
    "status": "checked_and_none",
    "availability": "fresh",
    "materialized": true,
    "source_path": "contextor/core/analysis/lineage_extraction.py",
    "errors": [],
    "total": 0,
    "truncated": false
  },
  "dependency_data_source": "live_canonical_graph",
  "artifact_data_source": "live_registry_and_symbol_state",
  "state_freshness": {
    "canonical_state": "fresh",
    "workspace_sync": "verified",
    "canonical_revision": 547,
    "provenance": "live",
    "families": {
      "module": "fresh",
      "graph": "fresh",
      "topology": "fresh",
      "artifact_consumption": "fresh",
      "cycles": "fresh",
      "collisions": "fresh"
    },
    "advisory_warning": null
  },
  "warnings": [],
  "public_api": {
    "total": 4,
    "truncated": true,
    "unresolved_total": 0,
    "evidence": {
      "A3910/1": "contextor.core.analysis.lineage_extraction::__all__",
      "A3924/1": "contextor.core.analysis.lineage_extraction::extract_lineage_source_facts",
      "A3928/1": "contextor.core.analysis.lineage_extraction::_AnchorExtractor.__init__"
    },
    "expand": {
      "compact": false,
      "max_items": null
    }
  },
  "imports": {
    "total": 9,
    "truncated": true,
    "evidence": [
      {
        "module_id": "283/1",
        "module": "contextor.core.analysis.state_manager"
      },
      {
        "module_id": "339/3",
        "module": "contextor.core.domain.lineage_facts"
      },
      {
        "module_id": "354/1",
        "module": "contextor.core.analysis.lineage_extraction_contracts"
      }
    ],
    "expand": {
      "compact": false,
      "max_items": null
    }
  },
  "consumers": {
    "total": 4,
    "truncated": true,
    "evidence": [
      {
        "module_id": "241/1",
        "module": "contextor.core.analysis.incremental.preparation"
      },
      {
        "module_id": "30/1",
        "module": "contextor.core.symbol_engine.indexer"
      },
      {
        "module_id": "352/1",
        "module": "tests.analysis.test_lineage_extraction"
      }
    ],
    "expand": {
      "compact": false,
      "max_items": null
    }
  },
  "tests_covering": {
    "available": true,
    "total": 105,
    "truncated": true,
    "evidence_scope": "static_dependency_reachability",
    "max_depth": 6,
    "evidence": [
      {
        "module_id": "352/1",
        "module": "tests.analysis.test_lineage_extraction",
        "distance": 1,
        "evidence_path": [
          "tests.analysis.test_lineage_extraction",
          "contextor.core.analysis.lineage_extraction"
        ],
        "evidence_scope": "static_dependency_reachability"
      },
      {
        "module_id": "353/1",
        "module": "tests.analysis.test_lineage_extraction_equivalence",
        "distance": 1,
        "evidence_path": [
          "tests.analysis.test_lineage_extraction_equivalence",
          "contextor.core.analysis.lineage_extraction"
        ],
        "evidence_scope": "static_dependency_reachability"
      },
      {
        "module_id": "250/1",
        "module": "tests.mcp.tools.test_analysis_status_concurrency",
        "distance": 4,
        "evidence_path": [
          "tests.mcp.tools.test_analysis_status_concurrency",
          "contextor.mcp.analysis_jobs",
          "contextor.core.api.facade",
          "contextor.core.symbol_engine.indexer",
          "contextor.core.analysis.lineage_extraction"
        ],
        "evidence_scope": "static_dependency_reachability"
      }
    ],
    "expand": {
      "compact": false,
      "max_items": null
    }
  },
  "diagnostics_summary": {
    "syntax_errors": {
      "count": 0,
      "availability": "fresh"
    },
    "name_collisions": {
      "count": 0,
      "critical": null,
      "warning": null,
      "info": null,
      "availability": "fresh"
    },
    "cycles": {
      "count": 0,
      "availability": "fresh"
    },
    "attention_required": false,
    "availability": {
      "syntax_errors": "fresh",
      "name_collisions": "fresh",
      "cycles": "fresh"
    }
  },
  "diagnostics_attention_required": false
}
\`\`\`

EDIT_CONTEXT_BINDINGS=
\`\`\`text
{
  "file": "contextor/core/analysis/lineage_extraction_bindings.py",
  "file_exists": true,
  "target": "contextor/core/analysis/lineage_extraction_bindings.py",
  "target_kind": "module",
  "status": "available",
  "module": "contextor.core.analysis.lineage_extraction_bindings",
  "module_id": "360/1",
  "layer": "runtime",
  "entrypoint": false,
  "risk_score": 0.0358,
  "syntax_diagnostics": {
    "status": "checked_and_none",
    "availability": "fresh",
    "materialized": true,
    "source_path": "contextor/core/analysis/lineage_extraction_bindings.py",
    "errors": [],
    "total": 0,
    "truncated": false
  },
  "dependency_data_source": "live_canonical_graph",
  "artifact_data_source": "live_registry_and_symbol_state",
  "state_freshness": {
    "canonical_state": "fresh",
    "workspace_sync": "verified",
    "canonical_revision": 547,
    "provenance": "live",
    "families": {
      "module": "fresh",
      "graph": "fresh",
      "topology": "fresh",
      "artifact_consumption": "fresh",
      "cycles": "fresh",
      "collisions": "fresh"
    },
    "advisory_warning": null
  },
  "warnings": [],
  "public_api": {
    "total": 12,
    "truncated": true,
    "unresolved_total": 0,
    "evidence": {
      "A3899/2": "contextor.core.analysis.lineage_extraction_bindings::VisitFn",
      "A4003/2": "contextor.core.analysis.lineage_extraction_bindings::visit_name",
      "A4064/2": "contextor.core.analysis.lineage_extraction_bindings::ValueFn"
    },
    "expand": {
      "compact": false,
      "max_items": null
    }
  },
  "imports": {
    "total": 3,
    "truncated": false,
    "evidence": [
      {
        "module_id": "339/3",
        "module": "contextor.core.domain.lineage_facts"
      },
      {
        "module_id": "355/1",
        "module": "contextor.core.analysis.lineage_extraction_state"
      },
      {
        "module_id": "356/1",
        "module": "contextor.core.analysis.lineage_extraction_emit"
      }
    ]
  },
  "consumers": {
    "total": 1,
    "truncated": false,
    "evidence": [
      {
        "module_id": "351/1",
        "module": "contextor.core.analysis.lineage_extraction"
      }
    ]
  },
  "tests_covering": {
    "available": true,
    "total": 94,
    "truncated": true,
    "evidence_scope": "static_dependency_reachability",
    "max_depth": 6,
    "evidence": [
      {
        "module_id": "352/1",
        "module": "tests.analysis.test_lineage_extraction",
        "distance": 2,
        "evidence_path": [
          "tests.analysis.test_lineage_extraction",
          "contextor.core.analysis.lineage_extraction",
          "contextor.core.analysis.lineage_extraction_bindings"
        ],
        "evidence_scope": "static_dependency_reachability"
      },
      {
        "module_id": "353/1",
        "module": "tests.analysis.test_lineage_extraction_equivalence",
        "distance": 2,
        "evidence_path": [
          "tests.analysis.test_lineage_extraction_equivalence",
          "contextor.core.analysis.lineage_extraction",
          "contextor.core.analysis.lineage_extraction_bindings"
        ],
        "evidence_scope": "static_dependency_reachability"
      },
      {
        "module_id": "250/1",
        "module": "tests.mcp.tools.test_analysis_status_concurrency",
        "distance": 5,
        "evidence_path": [
          "tests.mcp.tools.test_analysis_status_concurrency",
          "contextor.mcp.analysis_jobs",
          "contextor.core.api.facade",
          "contextor.core.symbol_engine.indexer",
          "contextor.core.analysis.lineage_extraction",
          "contextor.core.analysis.lineage_extraction_bindings"
        ],
        "evidence_scope": "static_dependency_reachability"
      }
    ],
    "expand": {
      "compact": false,
      "max_items": null
    }
  },
  "diagnostics_summary": {
    "syntax_errors": {
      "count": 0,
      "availability": "fresh"
    },
    "name_collisions": {
      "count": 0,
      "critical": null,
      "warning": null,
      "info": null,
      "availability": "fresh"
    },
    "cycles": {
      "count": 0,
      "availability": "fresh"
    },
    "attention_required": false,
    "availability": {
      "syntax_errors": "fresh",
      "name_collisions": "fresh",
      "cycles": "fresh"
    }
  },
  "diagnostics_attention_required": false
}
\`\`\`

COLLISION_EVIDENCE=
\`\`\`text
{
  "total": 0,
  "matched": 0,
  "offset": 0,
  "returned": 0,
  "has_more": false,
  "next_offset": null,
  "severity_counts": {
    "critical": 0,
    "warning": 0,
    "info": 0
  },
  "conflicting": 0,
  "identical": 0,
  "representation": "named",
  "truncated": false,
  "estimated_full_bytes": null,
  "context_budget_bytes": 15360,
  "attention_required": false,
  "availability": "fresh",
  "details": [],
  "diagnostics_summary": {
    "syntax_errors": {
      "count": 0,
      "availability": "fresh"
    },
    "name_collisions": {
      "count": 0,
      "critical": null,
      "warning": null,
      "info": null,
      "availability": "fresh"
    },
    "cycles": {
      "count": 0,
      "availability": "fresh"
    },
    "attention_required": false,
    "availability": {
      "syntax_errors": "fresh",
      "name_collisions": "fresh",
      "cycles": "fresh"
    }
  }
}
\`\`\`

CYCLE_AND_DEPENDENCY_EVIDENCE=
\`\`\`text
{
  "action_items": {
    "available": false,
    "state": "deferred",
    "reason": "No fresh canonical LIVE producer is available for this analytics family."
  },
  "top_global_hotspots": {
    "available": false,
    "state": "deferred",
    "reason": "No fresh canonical LIVE producer is available for this analytics family."
  },
  "layer_index": {
    "available": true,
    "distribution": {
      "adapter": 80,
      "cli": 1,
      "contract": 13,
      "engine": 27,
      "runtime": 83,
      "tests": 145,
      "ui": 11
    },
    "total": 7,
    "truncated": false
  },
  "debt_summary": {
    "available": false,
    "state": "deferred",
    "reason": "No fresh canonical LIVE producer is available for this analytics family."
  },
  "module_count": 360,
  "data_source": "live_canonical_state",
  "diagnostics_summary": {
    "syntax_errors": {
      "count": 0,
      "availability": "fresh"
    },
    "name_collisions": {
      "count": 0,
      "critical": null,
      "warning": null,
      "info": null,
      "availability": "fresh"
    },
    "cycles": {
      "count": 0,
      "availability": "fresh"
    },
    "attention_required": false,
    "availability": {
      "syntax_errors": "fresh",
      "name_collisions": "fresh",
      "cycles": "fresh"
    }
  },
  "diagnostics_attention_required": false
}
\`\`\`

LIVE_EVENTS_ADVISORY=
\`\`\`text
{
  "status": "ok",
  "activity_epoch": "b3235bf1904e4b5b9aa7393da102fb76",
  "revision": 547,
  "latest_revision": 547,
  "latest_seq": 250,
  "earliest_retained_revision": 525,
  "earliest_retained_seq": 1,
  "continuity": "not_requested",
  "resync_required": false,
  "resync_reason": null,
  "activity_continuity": "not_requested",
  "activity_resync_required": false,
  "events": [
    {
      "event_id": "d790c27e0c034cf686868399fc41d7a7",
      "timestamp": "2026-09-10T06:20:43.332+00:00",
      "sequence": 579,
      "event_type": "RUNTIME_AUTHORITY_START",
      "repo_id": "ctx_8efc50d8",
      "runtime_domain_id": "rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654",
      "service_instance_id": null,
      "lease_generation": null,
      "process_id": 4808,
      "operation_id": null,
      "request_type": null,
      "source": "runtime_startup_coordinator",
      "queue_order": null,
      "base_revision": null,
      "candidate_revision": null,
      "final_revision": null,
      "state_id": null,
      "decision": "START",
      "status": "STARTING",
      "reason": "authority service process spawn admitted",
      "error": null,
      "seq": 1,
      "category": "AUTHORITY",
      "operation": "RUNTIME_AUTHORITY_START",
      "origin": "runtime_startup_coordinator",
      "canonical_revision": null,
      "revision": 524
    },
    {
      "event_id": "4b4145d4313e4a6ea35f469ae245cba9",
      "timestamp": "2026-09-10T06:20:44.271+00:00",
      "sequence": 580,
      "event_type": "RUNTIME_LEASE_ACQUIRE",
      "repo_id": "ctx_8efc50d8",
      "runtime_domain_id": "rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654",
      "service_instance_id": null,
      "lease_generation": null,
      "process_id": 8980,
      "operation_id": null,
      "request_type": null,
      "source": "runtime_lease",
      "queue_order": null,
      "base_revision": null,
      "candidate_revision": null,
      "final_revision": null,
      "state_id": null,
      "decision": "REQUEST",
      "status": "REQUESTED",
      "reason": "authority lease acquisition requested",
      "error": null,
      "seq": 2,
      "category": "AUTHORITY",
      "operation": "RUNTIME_LEASE_ACQUIRE",
      "origin": "runtime_lease",
      "canonical_revision": null,
      "revision": 524
    },
    {
      "event_id": "f6e3f37ac4ff4ba9be79cc37e3505ec3",
      "timestamp": "2026-09-10T06:20:46.744+00:00",
      "sequence": 581,
      "event_type": "RUNTIME_LEASE_FENCE",
      "repo_id": "ctx_8efc50d8",
      "runtime_domain_id": "rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654",
      "service_instance_id": "15c07efce03640a687b830f7f1910f70",
      "lease_generation": 16,
      "process_id": 8980,
      "operation_id": null,
      "request_type": null,
      "source": "runtime_lease",
      "queue_order": null,
      "base_revision": null,
      "candidate_revision": null,
      "final_revision": null,
      "state_id": null,
      "decision": "FENCE_STALE",
      "status": "FENCED",
      "reason": "confirmed_stale_authority",
      "error": null,
      "seq": 3,
      "category": "AUTHORITY",
      "operation": "RUNTIME_LEASE_FENCE",
      "origin": "runtime_lease",
      "canonical_revision": null,
      "revision": 524
    },
    {
      "event_id": "8d4368b812f147429dd900322994695d",
      "timestamp": "2026-09-10T06:20:47.044+00:00",
      "sequence": 582,
      "event_type": "RUNTIME_LEASE_RESERVATION",
      "repo_id": "ctx_8efc50d8",
      "runtime_domain_id": "rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654",
      "service_instance_id": "65c9913c38d445d78131f9a4c7743df5",
      "lease_generation": 17,
      "process_id": 8980,
      "operation_id": null,
      "request_type": null,
      "source": "runtime_lease",
      "queue_order": null,
      "base_revision": null,
      "candidate_revision": null,
      "final_revision": null,
      "state_id": null,
      "decision": "ALLOCATE",
      "status": "RESERVED",
      "reason": "durable_generation_reserved",
      "error": null,
      "seq": 4,
      "category": "AUTHORITY",
      "operation": "RUNTIME_LEASE_RESERVATION",
      "origin": "runtime_lease",
      "canonical_revision": null,
      "revision": 524
    },
    {
      "event_id": "edb202842e394b00ba00e3854f15d062",
      "timestamp": "2026-09-10T06:20:47.245+00:00",
      "sequence": 583,
      "event_type": "RUNTIME_LEASE_ACTIVATION",
      "repo_id": "ctx_8efc50d8",
      "runtime_domain_id": "rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654",
      "service_instance_id": "65c9913c38d445d78131f9a4c7743df5",
      "lease_generation": 17,
      "process_id": 8980,
      "operation_id": null,
      "request_type": null,
      "source": "runtime_lease",
      "queue_order": null,
      "base_revision": null,
      "candidate_revision": null,
      "final_revision": null,
      "state_id": null,
      "decision": "ACTIVATE",
      "status": "ACTIVE",
      "reason": "durable_generation_active",
      "error": null,
      "seq": 5,
      "category": "AUTHORITY",
      "operation": "RUNTIME_LEASE_ACTIVATION",
      "origin": "runtime_lease",
      "canonical_revision": null,
      "revision": 524
    }
  ],
  "total": 250,
  "truncated": true,
  "diagnostics_summary": {
    "syntax_errors": {
      "count": 0,
      "availability": "fresh"
    },
    "name_collisions": {
      "count": 0,
      "critical": null,
      "warning": null,
      "info": null,
      "availability": "fresh"
    },
    "cycles": {
      "count": 0,
      "availability": "fresh"
    },
    "attention_required": false,
    "availability": {
      "syntax_errors": "fresh",
      "name_collisions": "fresh",
      "cycles": "fresh"
    }
  },
  "diagnostics_attention_required": false
}
\`\`\`

BINDING_OWNERSHIP=Accepted textual evidence reused: the nine binding implementations are only in lineage_extraction_bindings.py; corresponding facade methods are forwarding-only; all other visitors remain facade-owned.

DISPATCH_INVARIANT=Accepted textual evidence reused: exactly one dynamic _AnchorExtractor._visit; bindings has no ast.walk, NodeVisitor, dynamic visitor dispatch, or LineageExtractionState() construction.

TEST_RESULTS=110 PASS reused.

DIFF_CHECK=PASS reused.

FILES_CHANGED=
\`\`\`text
warning: in the working copy of 'contextor/core/analysis/lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'walkthrough.md', LF will be replaced by CRLF the next time Git touches it
contextor/core/analysis/lineage_extraction.py
walkthrough.md
contextor/core/analysis/lineage_extraction_bindings.py
\`\`\`

FULL_DIFFS=

\`\`\`diff
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index f9a6f05..df81ff9 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -27,6 +27,17 @@ from contextor.core.analysis.lineage_extraction_comprehensions import (
     visit_comprehension_expression,
 )
 from contextor.core.analysis.lineage_extraction_control import visit_block_from_frame
+from contextor.core.analysis.lineage_extraction_bindings import (
+    assign_target,
+    runtime_bind_target,
+    visit_ann_assign,
+    visit_assign,
+    visit_aug_assign,
+    visit_global,
+    visit_name,
+    visit_named_expr,
+    visit_nonlocal,
+)
 from contextor.core.analysis.lineage_extraction_state import _ActiveComprehension, _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
@@ -309,17 +320,7 @@ class _AnchorExtractor:
         self._visit_comprehension_expression(node, node.generators, (node.key, node.value), owner, walrus_owner)

     def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
-        if isinstance(node.ctx, ast.Store):
-            self._add("binding", node, node.id, owner)
-            return
-        if isinstance(node.ctx, ast.Load):
-            load = self._occurrence("name_load", node, node.id)
-            if node.id in self._blocked_names(owner):
-                return
-            source = self._frame(owner).get(node.id)
-            if source is None:
-                return
-            self._flow(source=source, target=load, relation=LineageRelation.BINDS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+        visit_name(self.state, self.paths, node, owner)

     def _assign_target(
         self,
@@ -328,18 +329,7 @@ class _AnchorExtractor:
         owner: str | None,
         walrus_owner: str | None,
     ) -> ExtractedOccurrenceRef | None:
-        if not isinstance(target, ast.Name):
-            self._visit(target, owner, walrus_owner)
-            return None
-        binding = ExtractedOccurrenceRef(self._add("binding", target, target.id, owner))
-        if target.id in self._blocked_names(owner):
-            return None
-        self._frame(owner)[target.id] = binding
-        callable_info = self.state._callable_values.get(source.local_id)
-        if callable_info is not None:
-            self.state._callables_by_binding[binding.local_id] = callable_info
-        self._flow(source=source, target=binding, relation=LineageRelation.ASSIGNS, node=target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
-        return binding
+        return assign_target(self.state, self.paths, target, source, owner, walrus_owner, visit=self._visit)

     def _runtime_bind_target(
         self,
@@ -347,101 +337,19 @@ class _AnchorExtractor:
         owner: str | None,
         walrus_owner: str | None,
     ) -> None:
-        if isinstance(target, ast.Name):
-            binding = ExtractedOccurrenceRef(
-                self._add("binding", target, target.id, owner)
-            )
-            if target.id in self._blocked_names(owner):
-                return
-            source = self._occurrence(
-                "runtime_bound_local",
-                target,
-                target.id,
-            )
-            self._frame(owner)[target.id] = binding
-            self._flow(
-                source=source,
-                target=binding,
-                relation=LineageRelation.ASSIGNS,
-                node=target,
-                resolution_kind=ResolutionKind.LEXICAL_EXACT,
-                confidence=LineageConfidence.CONFIRMED,
-            )
-            return
-        if isinstance(target, (ast.Tuple, ast.List)):
-            for item in target.elts:
-                self._runtime_bind_target(
-                    item,
-                    owner,
-                    walrus_owner,
-                )
-            return
-        if isinstance(target, ast.Starred):
-            self._runtime_bind_target(
-                target.value,
-                owner,
-                walrus_owner,
-            )
-            return
-        self._visit(target, owner, walrus_owner)
+        runtime_bind_target(self.state, self.paths, target, owner, walrus_owner, visit=self._visit)

     def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
-        source = self._value(node.value, owner, walrus_owner)
-        for target in node.targets:
-            self._assign_target(target, source, owner, walrus_owner)
+        visit_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

     def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
-        if node.value is None:
-            self._visit(node.target, owner, walrus_owner)
-            self._visit(node.annotation, owner, walrus_owner)
-            return
-        source = self._value(node.value, owner, walrus_owner)
-        self._assign_target(node.target, source, owner, walrus_owner)
-        self._visit(node.annotation, owner, walrus_owner)
+        visit_ann_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

     def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
-        target_owner = walrus_owner or owner
-        source = self._value(node.value, owner, walrus_owner)
-        binding = self._assign_target(
-            node.target,
-            source,
-            target_owner,
-            walrus_owner,
-        )
-        if (
-            binding is not None
-            and isinstance(node.target, ast.Name)
-        ):
-            self._publish_executed_walrus(
-                node.target.id,
-                binding,
-                target_owner,
-            )
+        visit_named_expr(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit, publish_walrus=self._publish_executed_walrus)

     def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
-        if not isinstance(node.target, ast.Name):
-            self._visit(node.target, owner, walrus_owner)
-            self._value(node.value, owner, walrus_owner)
-            return
-        blocked = node.target.id in self._blocked_names(owner)
-        prior = None if blocked else self._frame(owner).get(node.target.id)
-        if prior is not None:
-            prior_load = self._occurrence("name_load", node.target, node.target.id)
-            self._flow(
-                source=prior,
-                target=prior_load,
-                relation=LineageRelation.BINDS,
-                node=node.target,
-                resolution_kind=ResolutionKind.LEXICAL_EXACT,
-                confidence=LineageConfidence.CONFIRMED,
-            )
-        self._value(node.value, owner, walrus_owner)
-        binding = ExtractedOccurrenceRef(
-            self._add("binding", node.target, node.target.id, owner)
-        )
-        if blocked or prior is None:
-            return
-        self._frame(owner)[node.target.id] = binding
+        visit_aug_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

     def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
         self._visit(node.test, owner, walrus_owner)
@@ -597,16 +505,10 @@ class _AnchorExtractor:
             self._register_import_binding(alias, owner, local_name, module_name, alias.name)

     def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
-        for ordinal, name in enumerate(node.names):
-            self._add("global_declaration", node, name, owner, ordinal=ordinal)
-            self._blocked_names(owner).add(name)
-            self._frame(owner).pop(name, None)
+        visit_global(self.state, self.paths, node, owner)

     def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
-        for ordinal, name in enumerate(node.names):
-            self._add("nonlocal_declaration", node, name, owner, ordinal=ordinal)
-            self._blocked_names(owner).add(name)
-            self._frame(owner).pop(name, None)
+        visit_nonlocal(self.state, self.paths, node, owner)

     def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
         entry_frame = self._clone_frame(owner)
diff --git "a/contextor\\core\\analysis\\lineage_extraction_bindings.py" "b/contextor\\core\\analysis\\lineage_extraction_bindings.py"
new file mode 100644
index 0000000..2c55dae
--- /dev/null
+++ "b/contextor\\core\\analysis\\lineage_extraction_bindings.py"
@@ -0,0 +1,309 @@
+from __future__ import annotations
+
+import ast
+from collections.abc import Callable
+
+from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence
+from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
+from contextor.core.domain.lineage_facts import (
+    ExtractedOccurrenceRef,
+    LineageConfidence,
+    LineageRelation,
+    ResolutionKind,
+)
+
+
+VisitFn = Callable[[ast.AST, str | None, str | None], None]
+ValueFn = Callable[[ast.AST, str | None, str | None], ExtractedOccurrenceRef]
+PublishWalrusFn = Callable[[str, ExtractedOccurrenceRef, str | None], None]
+
+
+def visit_name(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.Name,
+    owner: str | None,
+) -> None:
+    if isinstance(node.ctx, ast.Store):
+        add_anchor(state, paths, "binding", node, node.id, owner)
+        return
+    if isinstance(node.ctx, ast.Load):
+        load = occurrence(state, paths, "name_load", node, node.id)
+        if node.id in state.blocked_names(owner):
+            return
+        source = state.frame(owner).get(node.id)
+        if source is None:
+            return
+        emit_flow(
+            state,
+            paths,
+            source=source,
+            target=load,
+            relation=LineageRelation.BINDS,
+            node=node,
+            resolution_kind=ResolutionKind.LEXICAL_EXACT,
+            confidence=LineageConfidence.CONFIRMED,
+        )
+
+
+def assign_target(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    target: ast.AST,
+    source: ExtractedOccurrenceRef,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+) -> ExtractedOccurrenceRef | None:
+    if not isinstance(target, ast.Name):
+        visit(target, owner, walrus_owner)
+        return None
+    binding = ExtractedOccurrenceRef(
+        add_anchor(state, paths, "binding", target, target.id, owner)
+    )
+    if target.id in state.blocked_names(owner):
+        return None
+    state.frame(owner)[target.id] = binding
+    callable_info = state._callable_values.get(source.local_id)
+    if callable_info is not None:
+        state._callables_by_binding[binding.local_id] = callable_info
+    emit_flow(
+        state,
+        paths,
+        source=source,
+        target=binding,
+        relation=LineageRelation.ASSIGNS,
+        node=target,
+        resolution_kind=ResolutionKind.LEXICAL_EXACT,
+        confidence=LineageConfidence.CONFIRMED,
+    )
+    return binding
+
+
+def runtime_bind_target(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    target: ast.AST,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+) -> None:
+    if isinstance(target, ast.Name):
+        binding = ExtractedOccurrenceRef(
+            add_anchor(state, paths, "binding", target, target.id, owner)
+        )
+        if target.id in state.blocked_names(owner):
+            return
+        source = occurrence(
+            state,
+            paths,
+            "runtime_bound_local",
+            target,
+            target.id,
+        )
+        state.frame(owner)[target.id] = binding
+        emit_flow(
+            state,
+            paths,
+            source=source,
+            target=binding,
+            relation=LineageRelation.ASSIGNS,
+            node=target,
+            resolution_kind=ResolutionKind.LEXICAL_EXACT,
+            confidence=LineageConfidence.CONFIRMED,
+        )
+        return
+    if isinstance(target, (ast.Tuple, ast.List)):
+        for item in target.elts:
+            runtime_bind_target(
+                state,
+                paths,
+                item,
+                owner,
+                walrus_owner,
+                visit=visit,
+            )
+        return
+    if isinstance(target, ast.Starred):
+        runtime_bind_target(
+            state,
+            paths,
+            target.value,
+            owner,
+            walrus_owner,
+            visit=visit,
+        )
+        return
+    visit(target, owner, walrus_owner)
+
+
+def visit_assign(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.Assign,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    value: ValueFn,
+    visit: VisitFn,
+) -> None:
+    source = value(node.value, owner, walrus_owner)
+    for target in node.targets:
+        assign_target(
+            state,
+            paths,
+            target,
+            source,
+            owner,
+            walrus_owner,
+            visit=visit,
+        )
+
+
+def visit_ann_assign(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.AnnAssign,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    value: ValueFn,
+    visit: VisitFn,
+) -> None:
+    if node.value is None:
+        visit(node.target, owner, walrus_owner)
+        visit(node.annotation, owner, walrus_owner)
+        return
+    source = value(node.value, owner, walrus_owner)
+    assign_target(
+        state,
+        paths,
+        node.target,
+        source,
+        owner,
+        walrus_owner,
+        visit=visit,
+    )
+    visit(node.annotation, owner, walrus_owner)
+
+
+def visit_named_expr(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.NamedExpr,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    value: ValueFn,
+    visit: VisitFn,
+    publish_walrus: PublishWalrusFn,
+) -> None:
+    target_owner = walrus_owner or owner
+    source = value(node.value, owner, walrus_owner)
+    binding = assign_target(
+        state,
+        paths,
+        node.target,
+        source,
+        target_owner,
+        walrus_owner,
+        visit=visit,
+    )
+    if binding is not None and isinstance(node.target, ast.Name):
+        publish_walrus(
+            node.target.id,
+            binding,
+            target_owner,
+        )
+
+
+def visit_aug_assign(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.AugAssign,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    value: ValueFn,
+    visit: VisitFn,
+) -> None:
+    if not isinstance(node.target, ast.Name):
+        visit(node.target, owner, walrus_owner)
+        value(node.value, owner, walrus_owner)
+        return
+    blocked = node.target.id in state.blocked_names(owner)
+    prior = None if blocked else state.frame(owner).get(node.target.id)
+    if prior is not None:
+        prior_load = occurrence(
+            state,
+            paths,
+            "name_load",
+            node.target,
+            node.target.id,
+        )
+        emit_flow(
+            state,
+            paths,
+            source=prior,
+            target=prior_load,
+            relation=LineageRelation.BINDS,
+            node=node.target,
+            resolution_kind=ResolutionKind.LEXICAL_EXACT,
+            confidence=LineageConfidence.CONFIRMED,
+        )
+    value(node.value, owner, walrus_owner)
+    binding = ExtractedOccurrenceRef(
+        add_anchor(
+            state,
+            paths,
+            "binding",
+            node.target,
+            node.target.id,
+            owner,
+        )
+    )
+    if blocked or prior is None:
+        return
+    state.frame(owner)[node.target.id] = binding
+
+
+def visit_global(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.Global,
+    owner: str | None,
+) -> None:
+    for ordinal, name in enumerate(node.names):
+        add_anchor(
+            state,
+            paths,
+            "global_declaration",
+            node,
+            name,
+            owner,
+            ordinal=ordinal,
+        )
+        state.blocked_names(owner).add(name)
+        state.frame(owner).pop(name, None)
+
+
+def visit_nonlocal(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.Nonlocal,
+    owner: str | None,
+) -> None:
+    for ordinal, name in enumerate(node.names):
+        add_anchor(
+            state,
+            paths,
+            "nonlocal_declaration",
+            node,
+            name,
+            owner,
+            ordinal=ordinal,
+        )
+        state.blocked_names(owner).add(name)
+        state.frame(owner).pop(name, None)
\`\`\`

