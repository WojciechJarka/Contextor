# CONTEXTOR P1D3-WARN-4I — implementer report

## PREFLIGHT

- DIRECT_EVIDENCE: Initial/final HEAD `cdd67d308570848d1684f737d90ba1dcab067ebe`; initial worktree clean.
- DIRECT_EVIDENCE: Contextor MCP pre-edit resolved `contextor.mcp.tools.get_live_events` at revision 877 and reported 16 fresh structural DFS cycles.
- DIRECT_EVIDENCE: The new test was absent. SEARCH 1, SEARCH 2 and the documentation SEARCH each occurred exactly once. MCP `get_file_edit_context` does not resolve JSON docs as a Python module; the docs file was inspected literally.

## SEARCH / REPLACE RESULT

- DIRECT_EVIDENCE: Applied the two exact architect-authored replacements in `get_live_events.py` and the exact replacement in `get_live_events.json`. Added the supplied test file with exact content.
- CODE_PATH_PROVED: The successful MCP response now adds `cycle_warning_transitions` after the existing `cycle_warning_view`, leaving the event journal response intact.

## REAL INSTALLED TRANSITION CHECKPOINT

- CONTRACT_PROVED: T01 exercises real owner-installed latest-commit reactivation transitions. T02 distinguishes `MODEL_ACCEPTED` from structural removal.
- CODE_PATH_PROVED: The projection queries `get_installed_cycle_warning_transitions` only for a fresh current warning view and validates checkpoint shape, authority, generation, identity, path shape, uniqueness, action, and current partition before returning `fresh`.

## CURRENT WARNING GENERATION GATE

- CONTRACT_PROVED: T03–T06 cover identity/generation mismatch, invalid transition content, absent checkpoint, and unavailable current view. These paths produce `unavailable` rather than fabricated zero transitions.
- CODE_PATH_PROVED: A transition checkpoint must match both events and current warning view revision/activity epoch.

## HISTORICAL EVENT PRESERVATION

- CONTRACT_PROVED: T07 checks transport failure does not remove retained history.
- CODE_PATH_PROVED: The new projection reads the checkpoint and adds a separate response field; it does not rewrite `diagnostic_changes` or the event journal.

## DOC CONTRACT

- DIRECT_EVIDENCE: Updated `contextor/mcp/docs/get_live_events.json` with current warning view, latest installed transition, historical structural event, and unavailable semantics. `get_mcp_documentation({tool:"get_live_events"})` returned the new transition wording.
- CONTRACT_PROVED: T08 validates the documentation terms.

## NEW TEST RESULTS

- `& .\.venv\Scripts\python.exe -m py_compile contextor/mcp/tools/get_live_events.py tests/test_cycle_semantics_mcp_warning_transitions.py` — PASS.
- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_mcp_warning_transitions.py` — 17 passed.

## FOCUSED REGRESSIONS

- `& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_mcp_live_warning_view.py tests/test_cycle_semantics_live_warning_transition_checkpoint.py tests/test_cycle_semantics_cycle_warning_transitions.py tests/test_mcp_documentation.py` — 69 passed; one third-party Authlib deprecation warning.
- `git diff --check` and new-file `git diff --no-index --check` — no whitespace errors.

## POST-CHANGE MCP AUDIT

- DIRECT_EVIDENCE: Contextor MCP `get_module_context` at revision 879 reported `canonical_state=fresh`, `workspace_sync=verified` for source and test. Graph and cycles were fresh; structural DFS cycle count remained 16.
- DIRECT_EVIDENCE: `cycle_semantics=stale`. Workspace synchronization does not prove active backend loaded-code adoption.

## FILES_CHANGED

- `contextor/mcp/tools/get_live_events.py`
- `contextor/mcp/docs/get_live_events.json`
- `tests/test_cycle_semantics_mcp_warning_transitions.py`

`walkthrough.md` overwritten as report only.

## FULL_DIFFS

### contextor/mcp/tools/get_live_events.py

```diff
diff --git a/contextor/mcp/tools/get_live_events.py b/contextor/mcp/tools/get_live_events.py
index b30170a..9906480 100644
--- a/contextor/mcp/tools/get_live_events.py
+++ b/contextor/mcp/tools/get_live_events.py
@@ -79,6 +79,159 @@ def _current_cycle_warning_view(client, events):
     }
 
 
+def _current_cycle_warning_transitions(client, events, view):
+    """Expose only the latest owner-verified warning transition checkpoint."""
+
+    def unavailable(reason):
+        return {"status": "unavailable", "reason": reason}
+
+    if type(view) is not dict or view.get("status") != "fresh":
+        return unavailable("CURRENT_WARNING_VIEW_UNAVAILABLE")
+
+    try:
+        checkpoint = client.request(
+            "get_installed_cycle_warning_transitions",
+            timeout=2.0,
+        )
+    except (
+        OSError, EOFError, ConnectionError, TimeoutError,
+        RuntimeError, AttributeError, TypeError, ValueError,
+    ):
+        return unavailable("WARNING_TRANSITION_QUERY_FAILED")
+
+    if type(checkpoint) is not dict or checkpoint.get("status") != "ok":
+        return unavailable("WARNING_TRANSITION_CHECKPOINT_UNAVAILABLE")
+
+    required = {
+        "status",
+        "binding_state",
+        "from_revision",
+        "to_revision",
+        "activity_epoch",
+        "repo_id",
+        "root_path",
+        "service_instance_id",
+        "process_start_identity",
+        "transitions",
+        "authority",
+    }
+
+    if set(checkpoint) != required:
+        return unavailable("WARNING_TRANSITION_CHECKPOINT_INVALID")
+
+    if (
+        checkpoint["binding_state"]
+        != "INSTALLED_WARNING_TRANSITION_CHECKPOINT"
+        or checkpoint["authority"] != (
+            "LIVE_OWNER_COMMIT_SCOPED_WARNING_TRANSITIONS"
+            "_NOT_STRUCTURAL_REMOVAL_FOR_MODEL_ACCEPTANCE"
+            "_NOT_RUNTIME_SAFETY"
+        )
+        or type(checkpoint["from_revision"]) is not int
+        or type(checkpoint["to_revision"]) is not int
+        or checkpoint["from_revision"] < 1
+        or checkpoint["to_revision"] <= checkpoint["from_revision"]
+        or checkpoint["to_revision"] != events.get("revision")
+        or checkpoint["to_revision"] != view.get("revision")
+        or checkpoint["activity_epoch"] != events.get("activity_epoch")
+        or checkpoint["activity_epoch"] != view.get("activity_epoch")
+        or type(checkpoint["activity_epoch"]) is not str
+        or not checkpoint["activity_epoch"]
+    ):
+        return unavailable("WARNING_TRANSITION_GENERATION_MISMATCH")
+
+    for key in (
+        "repo_id",
+        "root_path",
+        "service_instance_id",
+        "process_start_identity",
+    ):
+        if type(checkpoint[key]) is not str or not checkpoint[key]:
+            return unavailable("WARNING_TRANSITION_IDENTITY_INVALID")
+
+    transitions = checkpoint["transitions"]
+
+    if type(transitions) is not tuple:
+        return unavailable("WARNING_TRANSITION_CONTENT_INVALID")
+
+    accepted = set(view["model_pass_paths"])
+    active = set(view["active_warning_paths"])
+    structural = set(view["structural_paths"])
+    seen = set()
+
+    for transition in transitions:
+        if (
+            type(transition) is not dict
+            or set(transition) != {
+                "path", "action", "previous_state", "current_state",
+            }
+        ):
+            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")
+
+        path = transition["path"]
+        action = transition["action"]
+        before = transition["previous_state"]
+        after = transition["current_state"]
+
+        if (
+            type(path) is not tuple
+            or len(path) < 2
+            or any(type(node) is not str or not node for node in path)
+            or path[0] != path[-1]
+            or len(set(path[:-1])) != len(path) - 1
+            or path in seen
+        ):
+            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")
+
+        seen.add(path)
+
+        if action == "STRUCTURAL_ADDED":
+            valid = (
+                before is None
+                and after in {"MODEL_PASS", "ACTIVE"}
+                and path in structural
+            )
+        elif action == "STRUCTURAL_REMOVED":
+            valid = (
+                before in {"MODEL_PASS", "ACTIVE"}
+                and after is None
+                and path not in structural
+            )
+        elif action == "MODEL_ACCEPTED":
+            valid = (
+                before == "ACTIVE"
+                and after == "MODEL_PASS"
+                and path in accepted
+            )
+        elif action == "WARNING_REACTIVATED":
+            valid = (
+                before == "MODEL_PASS"
+                and after == "ACTIVE"
+                and path in active
+            )
+        else:
+            valid = False
+
+        if not valid:
+            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")
+
+        if after == "MODEL_PASS" and path not in accepted:
+            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")
+
+        if after == "ACTIVE" and path not in active:
+            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")
+
+    return {
+        "status": "fresh",
+        "scope": "LATEST_INSTALLED_COMMIT_ONLY_NOT_RETAINED_EVENT_HISTORY",
+        "from_revision": checkpoint["from_revision"],
+        "to_revision": checkpoint["to_revision"],
+        "activity_epoch": checkpoint["activity_epoch"],
+        "transition_count": len(transitions),
+        "transitions": transitions,
+    }
+
+
 def get_live_events(
     repo_path: str,
     after_revision: int | None = None,
@@ -145,6 +298,13 @@ def get_live_events(
         response["cycle_warning_view"] = _current_cycle_warning_view(
             client, events,
         )
+        response["cycle_warning_transitions"] = (
+            _current_cycle_warning_transitions(
+                client,
+                events,
+                response["cycle_warning_view"],
+            )
+        )
         return json.dumps(response, indent=2)
 
     except (OSError, EOFError, RuntimeError) as exc:
```

### contextor/mcp/docs/get_live_events.json

```diff
diff --git a/contextor/mcp/docs/get_live_events.json b/contextor/mcp/docs/get_live_events.json
index f04cff8..c095a8b 100644
--- a/contextor/mcp/docs/get_live_events.json
+++ b/contextor/mcp/docs/get_live_events.json
@@ -14,6 +14,10 @@
     "Committed incremental ``update_file`` events may include optional post-commit ``diagnostic_changes`` evidence with exact bounded shape ``{total, truncated, items}``; ``items`` contains at most three deterministic details.",
     "Each diagnostic item exposes ``action`` (``ADDED`` or ``RESOLVED``), ``diagnostic_kind`` (``syntax``, ``collision``, or ``cycle``), and a stable JSON-safe ``diagnostic_key``. Syntax items include ``source_path`` and ``line_number``/``column_number`` when attributable; collision items expose canonical structured collision fields; cycle items expose ``cycle_nodes``.",
     "Diagnostic changes are emitted only when both before and after canonical diagnostic-family states are fresh. Their absence is not proof of zero diagnostics when a family is stale or deferred. Canonical state remains authoritative; the runtime JSONL trace carries the full committed diagnostic delta for operational evidence.",
+    "When the LIVE owner can verify the current installed cycle warning partition, successful responses expose ``cycle_warning_view`` with structural, MODEL_PASS and active-warning counts and paths. Structural cycle count remains unchanged. This is static-model acceptance evidence, not runtime execution safety.",
+    "Successful responses also expose ``cycle_warning_transitions`` for the latest installed commit only. Valid transitions distinguish ``STRUCTURAL_ADDED``, ``STRUCTURAL_REMOVED``, ``MODEL_ACCEPTED`` and ``WARNING_REACTIVATED``. Their absence or an unavailable result is not evidence of zero transitions. The checkpoint is not a reconstruction of the retained event history.",
+    "``diagnostic_changes`` in the journal describe historical structural changes, not current active cycle warnings. The journal is preserved without deleting or rewriting its events. Current active warnings must be read from a fresh ``cycle_warning_view``.",
+    "Warning projections require matching LIVE revision and activity epoch. If the owner, projection or checkpoint is unavailable or inconsistent, the warning view or transitions are marked ``unavailable`` without fabricated active-warning counts.",
     "Existing syntax failure fields ``error``, ``line_number``, and ``column_number`` remain unchanged."
   ],
   "freshness": [],
```

### tests/test_cycle_semantics_mcp_warning_transitions.py

```diff
diff --git a/tests/test_cycle_semantics_mcp_warning_transitions.py b/tests/test_cycle_semantics_mcp_warning_transitions.py
new file mode 100644
index 0000000..e0a7dfe
--- /dev/null
+++ b/tests/test_cycle_semantics_mcp_warning_transitions.py
@@ -0,0 +1,320 @@
+"""WARN-4I: MCP projects current commit warning transitions separately."""
+
+from __future__ import annotations
+
+import copy
+import json
+
+import pytest
+
+from contextor.mcp.tools.get_live_events import get_live_events
+from tests.test_cycle_semantics_live_installed_partial_claims import (
+    _fixture, _owner,
+)
+from tests.test_cycle_semantics_live_warning_transition_checkpoint import (
+    _installed_next,
+)
+from tests.test_original_worker_partial_scc_preparation import TWO_PASS
+from tests.test_cycle_semantics_mcp_live_warning_view import _fake_reports
+
+
+@pytest.fixture(autouse=True)
+def _inline_worker(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _connect(monkeypatch, client):
+    monkeypatch.setattr(
+        "contextor.core.live_state.runtime.connect_existing_with_status",
+        lambda _root: (client, "ok"),
+    )
+
+
+def _checkpoint():
+    return {
+        "status": "ok",
+        "binding_state": "INSTALLED_WARNING_TRANSITION_CHECKPOINT",
+        "from_revision": 11,
+        "to_revision": 12,
+        "activity_epoch": "epoch-1",
+        "repo_id": "synthetic-repo",
+        "root_path": "/synthetic",
+        "service_instance_id": "synthetic-service",
+        "process_start_identity": "synthetic-process",
+        "transitions": (
+            {
+                "path": ("a", "b", "a"),
+                "action": "MODEL_ACCEPTED",
+                "previous_state": "ACTIVE",
+                "current_state": "MODEL_PASS",
+            },
+            {
+                "path": ("x", "y", "x"),
+                "action": "STRUCTURAL_ADDED",
+                "previous_state": None,
+                "current_state": "ACTIVE",
+            },
+        ),
+        "authority": (
+            "LIVE_OWNER_COMMIT_SCOPED_WARNING_TRANSITIONS"
+            "_NOT_STRUCTURAL_REMOVAL_FOR_MODEL_ACCEPTANCE"
+            "_NOT_RUNTIME_SAFETY"
+        ),
+    }
+
+
+class _Client:
+    def __init__(self, events, projection, checkpoint):
+        self.events = events
+        self.projection = projection
+        self.checkpoint = checkpoint
+        self.checkpoint_calls = 0
+
+    def get_events(self, **_kwargs):
+        return self.events
+
+    def get_installed_cycle_warning_projection(self):
+        return self.projection
+
+    def request(self, operation, **kwargs):
+        assert operation == "get_installed_cycle_warning_transitions"
+        assert kwargs == {"timeout": 2.0}
+        self.checkpoint_calls += 1
+        if isinstance(self.checkpoint, Exception):
+            raise self.checkpoint
+        return self.checkpoint
+
+
+def test_t01_latest_installed_commit_reports_real_reactivations(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root, state, metadata = _fixture(tmp_path, TWO_PASS)
+
+    with _owner(state, metadata) as (server, client):
+        _connect(monkeypatch, client)
+
+        before = json.loads(get_live_events(str(root)))
+
+        assert before["status"] == "ok"
+        assert before["cycle_warning_view"]["status"] == "fresh"
+        assert before["cycle_warning_transitions"]["status"] == "unavailable"
+
+        _installed_next(root, server, partial=False)
+
+        journal_before = copy.deepcopy(
+            (server._events, server._activity_seq)
+        )
+
+        result = json.loads(get_live_events(str(root)))
+
+        view = result["cycle_warning_view"]
+        delta = result["cycle_warning_transitions"]
+
+        assert result["status"] == "ok"
+        assert view["status"] == "fresh"
+        assert view["structural_count"] == 2
+        assert view["model_pass_count"] == 0
+        assert view["active_warning_count"] == 2
+
+        assert delta["status"] == "fresh"
+        assert delta["scope"] == (
+            "LATEST_INSTALLED_COMMIT_ONLY_NOT_RETAINED_EVENT_HISTORY"
+        )
+        assert delta["from_revision"] == metadata.revision
+        assert delta["to_revision"] == result["revision"]
+        assert delta["activity_epoch"] == result["activity_epoch"]
+        assert delta["transition_count"] == 2
+        assert [item["action"] for item in delta["transitions"]] == [
+            "WARNING_REACTIVATED", "WARNING_REACTIVATED",
+        ]
+
+        assert (
+            server._events, server._activity_seq
+        ) == journal_before
+
+
+def test_t02_model_acceptance_is_not_structural_removal(
+    tmp_path, monkeypatch,
+):
+    events, projection = _fake_reports()
+    checkpoint = _checkpoint()
+    client = _Client(events, projection, checkpoint)
+    _connect(monkeypatch, client)
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    delta = result["cycle_warning_transitions"]
+
+    assert delta["status"] == "fresh"
+    assert delta["transition_count"] == 2
+    assert [item["action"] for item in delta["transitions"]] == [
+        "MODEL_ACCEPTED", "STRUCTURAL_ADDED",
+    ]
+    assert result["cycle_warning_view"]["structural_count"] == 2
+    assert client.checkpoint_calls == 1
+
+
+@pytest.mark.parametrize("change", [
+    {"to_revision": 13},
+    {"activity_epoch": "wrong-epoch"},
+    {"from_revision": 12},
+    {"binding_state": "FORGED"},
+    {"authority": "FORGED"},
+    {"service_instance_id": ""},
+])
+def test_t03_checkpoint_identity_and_generation_mismatch_fails_closed(
+    tmp_path, monkeypatch, change,
+):
+    events, projection = _fake_reports()
+    checkpoint = {**_checkpoint(), **change}
+    _connect(monkeypatch, _Client(events, projection, checkpoint))
+
+    response = json.loads(get_live_events(str(tmp_path)))
+    delta = response["cycle_warning_transitions"]
+
+    assert delta["status"] == "unavailable"
+    assert "transition_count" not in delta
+    assert response["cycle_warning_view"]["status"] == "fresh"
+
+
+@pytest.mark.parametrize("item", [
+    {
+        "path": ("a", "b", "a"),
+        "action": "STRUCTURAL_REMOVED",
+        "previous_state": "ACTIVE",
+        "current_state": None,
+    },
+    {
+        "path": ("a", "b", "a"),
+        "action": "WARNING_REACTIVATED",
+        "previous_state": "MODEL_PASS",
+        "current_state": "ACTIVE",
+    },
+    {
+        "path": ("a", "b", "a"),
+        "action": "MODEL_ACCEPTED",
+        "previous_state": "ACTIVE",
+        "current_state": "ACTIVE",
+    },
+    {
+        "path": ("a", "b", "a"),
+        "action": "UNKNOWN",
+        "previous_state": "ACTIVE",
+        "current_state": "MODEL_PASS",
+    },
+    {
+        "path": ("a", "b", "x"),
+        "action": "MODEL_ACCEPTED",
+        "previous_state": "ACTIVE",
+        "current_state": "MODEL_PASS",
+    },
+])
+def test_t04_invalid_transition_never_becomes_fresh(
+    tmp_path, monkeypatch, item,
+):
+    events, projection = _fake_reports()
+    checkpoint = _checkpoint()
+    checkpoint["transitions"] = (item,)
+    _connect(monkeypatch, _Client(events, projection, checkpoint))
+
+    delta = json.loads(get_live_events(str(tmp_path)))[
+        "cycle_warning_transitions"
+    ]
+
+    assert delta["status"] == "unavailable"
+    assert "transitions" not in delta
+
+
+def test_t05_missing_checkpoint_does_not_claim_zero(
+    tmp_path, monkeypatch,
+):
+    events, projection = _fake_reports()
+    client = _Client(
+        events,
+        projection,
+        {
+            "status": "unavailable",
+            "reason": "NO_COMMITTED_WARNING_TRANSITION",
+        },
+    )
+    _connect(monkeypatch, client)
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    assert result["cycle_warning_transitions"]["status"] == "unavailable"
+    assert "transition_count" not in result["cycle_warning_transitions"]
+
+
+def test_t06_unavailable_current_view_skips_transition_query(
+    tmp_path, monkeypatch,
+):
+    events, projection = _fake_reports()
+    projection["revision"] = 13
+    client = _Client(events, projection, _checkpoint())
+    _connect(monkeypatch, client)
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    assert result["cycle_warning_view"]["status"] == "unavailable"
+    assert result["cycle_warning_transitions"]["status"] == "unavailable"
+    assert client.checkpoint_calls == 0
+
+
+def test_t07_transport_failure_does_not_remove_history(
+    tmp_path, monkeypatch,
+):
+    events, projection = _fake_reports()
+    events["events"] = [{
+        "canonical_revision": 12,
+        "diagnostic_changes": {
+            "total": 1,
+            "truncated": False,
+            "items": [{
+                "diagnostic_kind": "cycle",
+                "action": "ADDED",
+                "cycle_nodes": ["a", "b", "a"],
+            }],
+        },
+    }]
+    original = copy.deepcopy(events)
+
+    client = _Client(
+        events, projection, TimeoutError("synthetic timeout"),
+    )
+    _connect(monkeypatch, client)
+
+    result = json.loads(get_live_events(str(tmp_path)))
+
+    assert result["status"] == "ok"
+    assert result["events"] == original["events"]
+    assert result["cycle_warning_transitions"]["status"] == "unavailable"
+    assert "transition_count" not in result["cycle_warning_transitions"]
+    assert events == original
+
+
+def test_t08_documentation_describes_current_warning_semantics():
+    from pathlib import Path
+
+    docs = (
+        Path(__file__).resolve().parents[1]
+        / "contextor" / "mcp" / "docs" / "get_live_events.json"
+    )
+
+    data = json.loads(docs.read_text(encoding="utf-8"))
+
+    assert data["version"] == "1.0.0"
+    assert data["tool"] == "get_live_events"
+
+    behavior = " ".join(data["behavior"])
+
+    for term in (
+        "cycle_warning_view",
+        "cycle_warning_transitions",
+        "MODEL_ACCEPTED",
+        "WARNING_REACTIVATED",
+        "STRUCTURAL_ADDED",
+        "STRUCTURAL_REMOVED",
+        "historical structural changes",
+        "unavailable",
+    ):
+        assert term in behavior
```

## CONTRACT_CONFLICTS

None observed in the exact anchors, compilation, or focused tests.

## REMAINING UNKNOWN

- UNKNOWN: Active MCP backend loaded-code adoption; no restart was performed.
- UNKNOWN: Global pytest outcome; prohibited in this stage.
- UNKNOWN: Semantic cycle family remains stale in MCP.

## FINAL IMPLEMENTER OBSERVATION

The literal WARN-4I change passed new and specified focused tests. Structural DFS cycle count remained 16. Architectural acceptance remains with ChatGPT. STOP after WARN-4I.
