# TASK
P15-D9

# PREFLIGHT

DIRECT_EVIDENCE: current HEAD ef326c4a657953860cb963cca45856e43f8b87f0 (newer than handoff); worktree clean before diagnostic. CPython 3.15.2 from repository .venv. R8 restrictions are present in current HEAD. No source/test edits, pytest, FULL analysis, update_file, restart, commit, or push.

# CURRENT_CANONICAL_AUTHORITY

DIRECT_EVIDENCE: MCP get_project_architecture: revision 1146, repo_id ctx_8efc50d8, canonical_state=fresh, resync_required=false, graph/cycles=fresh, cycle_semantics=stale, syntax errors=0, structural DFS cycles=16. Project-scope workspace_sync=unverified; target module contexts package_model, namespace_bound_model, domain.imports each workspace_sync=verified at revision 1146. One read-only LIVE snapshot at revision 1146; same-generation FileState revision 1146, state_id 20261108_172727, baseline=trusted. Hard edges=2509; indexed modules=627; SCC member lists:

```json

[
  [
    "contextor.core.analysis.full_analysis_coordinator",
    "contextor.core.analysis.incremental.engine",
    "contextor.core.analysis.incremental.materialization",
    "contextor.core.analysis.incremental.plan_executor",
    "contextor.core.analysis.incremental.preparation",
    "contextor.core.analysis.incremental_engine",
    "contextor.core.analysis.lineage_extraction",
    "contextor.core.analysis.refresh_planner",
    "contextor.core.analysis.state_manager",
    "contextor.core.api.facade",
    "contextor.core.cycle_semantics.cycle_warning_projection",
    "contextor.core.cycle_semantics.cycle_warning_transitions",
    "contextor.core.cycle_semantics.evidence",
    "contextor.core.cycle_semantics.generation_manifest",
    "contextor.core.cycle_semantics.live_cycle_warning_query",
    "contextor.core.cycle_semantics.live_installed_claims",
    "contextor.core.cycle_semantics.live_installed_optional_claims",
    "contextor.core.cycle_semantics.live_installed_partial_claims",
    "contextor.core.cycle_semantics.live_warning_diagnostics_summary",
    "contextor.core.cycle_semantics.live_warning_transition_checkpoint",
    "contextor.core.cycle_semantics.optional_generation_anchor",
    "contextor.core.cycle_semantics.optional_scc_publication",
    "contextor.core.cycle_semantics.original_worker_binding",
    "contextor.core.cycle_semantics.original_worker_preparation",
    "contextor.core.cycle_semantics.original_worker_reindex_planning",
    "contextor.core.cycle_semantics.partial_scc_claims",
    "contextor.core.cycle_semantics.partial_scc_publication",
    "contextor.core.cycle_semantics.partial_warning_eligibility",
    "contextor.core.cycle_semantics.publication_binding",
    "contextor.core.cycle_semantics.source_proof",
    "contextor.core.lineage_query.live_query",
    "contextor.core.live_state.__init__",
    "contextor.core.live_state.hydration",
    "contextor.core.live_state.ipc",
    "contextor.core.live_state.runtime",
    "contextor.core.live_state.store",
    "contextor.core.live_state.watcher",
    "contextor.core.reference.module_usage_reuse",
    "contextor.core.reporting_engine.pipeline",
    "contextor.core.single_file.builders.__init__",
    "contextor.core.single_file.builders.layer0_builders",
    "contextor.core.single_file.builders.layer2_builders",
    "contextor.core.single_file.single_file_analysis",
    "contextor.core.symbol_engine.indexer"
  ],
  [
    "contextor.repo_generator.__init__",
    "contextor.repo_generator.filters",
    "contextor.repo_generator.icons",
    "contextor.repo_generator.main",
    "contextor.ui.__init__",
    "contextor.ui.exclude_gui",
    "contextor.ui.gui",
    "contextor.ui.gui_parser",
    "contextor.ui.progress_widget"
  ]
]

```

# CURRENT_SOURCE_INVENTORY

DIRECT_EVIDENCE: OPTIONAL_NAMED_CHILDREN closure sizes [202, 222]; union=222; selected=222, bound=222. One source path and SourceSnapshot per indexed module; one SearchPortion('repo', files). Deterministic digest SHA256 of sorted JSON [module_id, root-relative POSIX path, raw SHA256] rows with compact separators: `e0ffebb74812258d68a3c32c5aef8fe4b6685e11094240d2b80846de83174d46`. This is current D9 evidence, distinct from D8 digest.

# FILESTATE_SHA_PARITY

DIRECT_EVIDENCE: same-generation FileState revision/state_id parity; raw-byte SHA256 mismatches=0, omitted selected sources=0. FileState baseline trusted. No fabricated source paths or bytes.

# FRESH_PROCESS_R8_ADOPTION

DIRECT_EVIDENCE: fresh CPython process imported on-disk namespace_bound_model and package_model from ['C:\\Temp\\Contextor_Repo\\contextor\\core\\cycle_semantics\\namespace_bound_model.py', 'C:\\Temp\\Contextor_Repo\\contextor\\core\\cycle_semantics\\package_model.py']; exact BitOr optional-union check, ast.Constant default check, and seen_default_field ordering check present=True. This proves this diagnostic process only.

# ENTRY_A

DIRECT_EVIDENCE: entry=contextor.repo_generator; outer=UNKNOWN/RESTRICTED_MODEL_UNKNOWN; authority=SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF; source_evidence_sha256=70c02e31a5b0b8f6d0280d19ecb36bba2ad89fbfd76f88c9fcaed67e2492cb2b; inner conditional=UNKNOWN/RESTRICTED_MODEL_UNKNOWN; inner model=UNKNOWN, evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF; external assumptions=47, dataclass assumptions=2, events=91; evaluation seconds=6.491351. First stopping module=contextor.core.source; reached_unmodeled_import=None; early-binding hazard observed=no; conditional evaluation completed=no.

External assumptions canonical JSON SHA256=4ae7ee3c957faee758f3643f78e16d1553c43a2c3c9a688491930c8bbfb51f4a; first 10:

```json

[
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 1,
    "operation": "IMPORT",
    "symbol": null,
    "target": "os"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 2,
    "operation": "IMPORT",
    "symbol": null,
    "target": "shutil"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 3,
    "operation": "IMPORT",
    "symbol": null,
    "target": "subprocess"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 4,
    "operation": "IMPORT",
    "symbol": null,
    "target": "tkinter"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 5,
    "operation": "PREPARE_FROM_MEMBER",
    "symbol": "filedialog",
    "target": "tkinter"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 5,
    "operation": "PREPARE_FROM_MEMBER",
    "symbol": "messagebox",
    "target": "tkinter"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 5,
    "operation": "PREPARE_FROM_MEMBER",
    "symbol": "ttk",
    "target": "tkinter"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 5,
    "operation": "FROM",
    "symbol": "filedialog",
    "target": "tkinter"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 5,
    "operation": "FROM",
    "symbol": "messagebox",
    "target": "tkinter"
  },
  {
    "column": 0,
    "importer": "contextor.repo_generator.main",
    "line": 5,
    "operation": "FROM",
    "symbol": "ttk",
    "target": "tkinter"
  }
]

```

Last 10 external assumptions:

```json

[
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 8,
    "operation": "FROM",
    "symbol": "lru_cache",
    "target": "functools"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 9,
    "operation": "FROM",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 3,
    "operation": "IMPORT",
    "symbol": null,
    "target": "ast"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 4,
    "operation": "IMPORT",
    "symbol": null,
    "target": "hashlib"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 5,
    "operation": "IMPORT",
    "symbol": null,
    "target": "io"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 6,
    "operation": "IMPORT",
    "symbol": null,
    "target": "tokenize"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 8,
    "operation": "FROM",
    "symbol": "Path",
    "target": "pathlib"
  }
]

```

All dataclass decoration records:

```json

[
  {
    "class_name": "ProjectGraph",
    "column": 1,
    "decorator": "dataclasses.dataclass(frozen=True)",
    "line": 10,
    "module": "contextor.core.domain.graph"
  },
  {
    "class_name": "ImportRef",
    "column": 1,
    "decorator": "dataclasses.dataclass(frozen=True)",
    "line": 11,
    "module": "contextor.core.domain.imports"
  }
]

```

First 15 model events:

```json

[
  {
    "module": "\u0000ENTRY",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor"
  },
  {
    "module": "contextor",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "\u0000ENTRY",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.repo_generator"
  },
  {
    "module": "contextor.repo_generator",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.repo_generator.main"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "os"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "shutil"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "subprocess"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "tkinter"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "filedialog",
    "target": "tkinter"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "messagebox",
    "target": "tkinter"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "ttk",
    "target": "tkinter"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "filedialog",
    "target": "tkinter"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "messagebox",
    "target": "tkinter"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "ttk",
    "target": "tkinter"
  },
  {
    "module": "contextor.repo_generator.main",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.repo_generator.config"
  }
]

```

Last 20 model events:

```json

[
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_FROZEN_DATACLASS_DECORATION",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "DEFINE_PASSIVE_CLASS",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core.domain",
    "operation": "BIND_CHILD",
    "symbol": "imports",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "FROM",
    "symbol": "ImportRef",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain.module"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "lru_cache",
    "target": "functools"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.source"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "ast"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "hashlib"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "io"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "tokenize"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "module": "contextor.core.source",
    "operation": "BIND",
    "symbol": "__all__",
    "target": null
  }
]

```

Bounded decisive trace around ImportRef (zero-based event index 71):

```json

[
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "is_local",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "type_only",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "is_lazy",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_FROZEN_DATACLASS_DECORATION",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "DEFINE_PASSIVE_CLASS",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core.domain",
    "operation": "BIND_CHILD",
    "symbol": "imports",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "FROM",
    "symbol": "ImportRef",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain.module"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  }
]

```

# ENTRY_B

DIRECT_EVIDENCE: entry=contextor.ui; outer=UNKNOWN/RESTRICTED_MODEL_UNKNOWN; authority=SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF; source_evidence_sha256=89bead172e7cf57abcf2e4581763281093856d3384e3fd24435a9b6b599ba36f; inner conditional=UNKNOWN/RESTRICTED_MODEL_UNKNOWN; inner model=UNKNOWN, evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF; external assumptions=32, dataclass assumptions=2, events=60; evaluation seconds=5.838771. First stopping module=contextor.core.source; reached_unmodeled_import=None; early-binding hazard observed=no; conditional evaluation completed=no.

External assumptions canonical JSON SHA256=1b8aa612f3b52a432f38cfb5d295144ce0ed56e8590fbf447baa1fb6a262869b; first 10:

```json

[
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 8,
    "operation": "IMPORT",
    "symbol": null,
    "target": "os"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 9,
    "operation": "IMPORT",
    "symbol": null,
    "target": "threading"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 10,
    "operation": "IMPORT",
    "symbol": null,
    "target": "time"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 11,
    "operation": "IMPORT",
    "symbol": null,
    "target": "tkinter"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 12,
    "operation": "IMPORT",
    "symbol": null,
    "target": "uuid"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 13,
    "operation": "FROM",
    "symbol": "datetime",
    "target": "datetime"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 14,
    "operation": "PREPARE_FROM_MEMBER",
    "symbol": "Empty",
    "target": "queue"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 14,
    "operation": "PREPARE_FROM_MEMBER",
    "symbol": "Queue",
    "target": "queue"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 14,
    "operation": "FROM",
    "symbol": "Empty",
    "target": "queue"
  },
  {
    "column": 0,
    "importer": "contextor.ui.gui",
    "line": 14,
    "operation": "FROM",
    "symbol": "Queue",
    "target": "queue"
  }
]

```

Last 10 external assumptions:

```json

[
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 8,
    "operation": "FROM",
    "symbol": "lru_cache",
    "target": "functools"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 9,
    "operation": "FROM",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 3,
    "operation": "IMPORT",
    "symbol": null,
    "target": "ast"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 4,
    "operation": "IMPORT",
    "symbol": null,
    "target": "hashlib"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 5,
    "operation": "IMPORT",
    "symbol": null,
    "target": "io"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 6,
    "operation": "IMPORT",
    "symbol": null,
    "target": "tokenize"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 8,
    "operation": "FROM",
    "symbol": "Path",
    "target": "pathlib"
  }
]

```

All dataclass decoration records:

```json

[
  {
    "class_name": "ProjectGraph",
    "column": 1,
    "decorator": "dataclasses.dataclass(frozen=True)",
    "line": 10,
    "module": "contextor.core.domain.graph"
  },
  {
    "class_name": "ImportRef",
    "column": 1,
    "decorator": "dataclasses.dataclass(frozen=True)",
    "line": 11,
    "module": "contextor.core.domain.imports"
  }
]

```

First 15 model events:

```json

[
  {
    "module": "\u0000ENTRY",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor"
  },
  {
    "module": "contextor",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "\u0000ENTRY",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.ui"
  },
  {
    "module": "contextor.ui",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.ui.gui"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "os"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "threading"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "time"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "tkinter"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "uuid"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "datetime",
    "target": "datetime"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Empty",
    "target": "queue"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Queue",
    "target": "queue"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Empty",
    "target": "queue"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Queue",
    "target": "queue"
  },
  {
    "module": "contextor.ui.gui",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Path",
    "target": "pathlib"
  }
]

```

Last 20 model events:

```json

[
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_FROZEN_DATACLASS_DECORATION",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "DEFINE_PASSIVE_CLASS",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core.domain",
    "operation": "BIND_CHILD",
    "symbol": "imports",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "FROM",
    "symbol": "ImportRef",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain.module"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "lru_cache",
    "target": "functools"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.source"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "ast"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "hashlib"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "io"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "tokenize"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "module": "contextor.core.source",
    "operation": "BIND",
    "symbol": "__all__",
    "target": null
  }
]

```

Bounded decisive trace around ImportRef (zero-based event index 40):

```json

[
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "is_local",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "type_only",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "is_lazy",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_FROZEN_DATACLASS_DECORATION",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "DEFINE_PASSIVE_CLASS",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core.domain",
    "operation": "BIND_CHILD",
    "symbol": "imports",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "FROM",
    "symbol": "ImportRef",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain.module"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  }
]

```

# ENTRY_C

DIRECT_EVIDENCE: entry=contextor.core.analysis.state_manager; outer=UNKNOWN/RESTRICTED_MODEL_UNKNOWN; authority=SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF; source_evidence_sha256=57c97fb9a8dde87c2770dcf7b1032e024b5048c8ff389185dadd05dd50eca003; inner conditional=UNKNOWN/RESTRICTED_MODEL_UNKNOWN; inner model=UNKNOWN, evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF; external assumptions=14, dataclass assumptions=2, events=40; evaluation seconds=4.177591. First stopping module=contextor.core.source; reached_unmodeled_import=None; early-binding hazard observed=no; conditional evaluation completed=no.

External assumptions canonical JSON SHA256=9e0ef35b266bc3060826e3884608dbb8f5ef43c49a2610aaf12f18d5e35e1b4f; first 10:

```json

[
  {
    "column": 0,
    "importer": "contextor.core.domain.graph",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.imports",
    "line": 8,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "PREPARE_FROM_MEMBER",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "PREPARE_FROM_MEMBER",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 8,
    "operation": "FROM",
    "symbol": "lru_cache",
    "target": "functools"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 9,
    "operation": "FROM",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 3,
    "operation": "IMPORT",
    "symbol": null,
    "target": "ast"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 4,
    "operation": "IMPORT",
    "symbol": null,
    "target": "hashlib"
  }
]

```

Last 10 external assumptions:

```json

[
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 7,
    "operation": "FROM",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 8,
    "operation": "FROM",
    "symbol": "lru_cache",
    "target": "functools"
  },
  {
    "column": 0,
    "importer": "contextor.core.domain.module",
    "line": 9,
    "operation": "FROM",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 3,
    "operation": "IMPORT",
    "symbol": null,
    "target": "ast"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 4,
    "operation": "IMPORT",
    "symbol": null,
    "target": "hashlib"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 5,
    "operation": "IMPORT",
    "symbol": null,
    "target": "io"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 6,
    "operation": "IMPORT",
    "symbol": null,
    "target": "tokenize"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 7,
    "operation": "FROM",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "column": 0,
    "importer": "contextor.core.source",
    "line": 8,
    "operation": "FROM",
    "symbol": "Path",
    "target": "pathlib"
  }
]

```

All dataclass decoration records:

```json

[
  {
    "class_name": "ProjectGraph",
    "column": 1,
    "decorator": "dataclasses.dataclass(frozen=True)",
    "line": 10,
    "module": "contextor.core.domain.graph"
  },
  {
    "class_name": "ImportRef",
    "column": 1,
    "decorator": "dataclasses.dataclass(frozen=True)",
    "line": 11,
    "module": "contextor.core.domain.imports"
  }
]

```

First 15 model events:

```json

[
  {
    "module": "\u0000ENTRY",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor"
  },
  {
    "module": "contextor",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "\u0000ENTRY",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core"
  },
  {
    "module": "contextor.core",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.graph"
  },
  {
    "module": "contextor.core.graph",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core",
    "operation": "BIND_CHILD",
    "symbol": "graph",
    "target": "contextor.core.graph"
  },
  {
    "module": "contextor.core",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.graph.graph"
  },
  {
    "module": "contextor.core.graph.graph",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain"
  },
  {
    "module": "contextor.core.domain",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain.graph"
  },
  {
    "module": "contextor.core.domain.graph",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.graph",
    "operation": "ASSUMED_FROZEN_DATACLASS_DECORATION",
    "symbol": "ProjectGraph",
    "target": null
  },
  {
    "module": "contextor.core.domain.graph",
    "operation": "DEFINE_PASSIVE_CLASS",
    "symbol": "ProjectGraph",
    "target": null
  },
  {
    "module": "contextor.core.domain.graph",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core.domain",
    "operation": "BIND_CHILD",
    "symbol": "graph",
    "target": "contextor.core.domain.graph"
  },
  {
    "module": "contextor.core.domain",
    "operation": "FROM",
    "symbol": "ProjectGraph",
    "target": "contextor.core.domain.graph"
  }
]

```

Last 20 model events:

```json

[
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_FROZEN_DATACLASS_DECORATION",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "DEFINE_PASSIVE_CLASS",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core.domain",
    "operation": "BIND_CHILD",
    "symbol": "imports",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "FROM",
    "symbol": "ImportRef",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain.module"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "field",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "lru_cache",
    "target": "functools"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.source"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "ast"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "hashlib"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "io"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": null,
    "target": "tokenize"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.source",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "Path",
    "target": "pathlib"
  },
  {
    "module": "contextor.core.source",
    "operation": "BIND",
    "symbol": "__all__",
    "target": null
  }
]

```

Bounded decisive trace around ImportRef (zero-based event index 20):

```json

[
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "is_local",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "type_only",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "CLASS_LOCAL_BIND",
    "symbol": "is_lazy",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "ASSUMED_FROZEN_DATACLASS_DECORATION",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "DEFINE_PASSIVE_CLASS",
    "symbol": "ImportRef",
    "target": null
  },
  {
    "module": "contextor.core.domain.imports",
    "operation": "READY",
    "symbol": null,
    "target": null
  },
  {
    "module": "contextor.core.domain",
    "operation": "BIND_CHILD",
    "symbol": "imports",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "FROM",
    "symbol": "ImportRef",
    "target": "contextor.core.domain.imports"
  },
  {
    "module": "contextor.core.domain",
    "operation": "START_IMPORT",
    "symbol": null,
    "target": "contextor.core.domain.module"
  },
  {
    "module": "contextor.core.domain.module",
    "operation": "ASSUMED_EXTERNAL_IMPORT",
    "symbol": "dataclass",
    "target": "dataclasses"
  }
]

```

# PROJECTGRAPH_EVIDENCE

DIRECT_EVIDENCE: all three records contain ProjectGraph frozen dataclass assumption before ImportRef. D8 had crossed ProjectGraph; D9 retains that observed progression.

# IMPORTREF_EVIDENCE

DIRECT_EVIDENCE: all three traces enter contextor.core.domain.imports, record ASSUMED_FROZEN_DATACLASS_DECORATION then DEFINE_PASSIVE_CLASS for ImportRef, then READY for imports, BIND_CHILD/FROM ImportRef, and START_IMPORT of contextor.core.domain.module. Decoration record source coordinates: contextor/core/domain/imports.py line 11, column 1 (model record uses one-based column). This crosses the D8 boundary; D8 ended after ASSUMED_EXTERNAL_IMPORT dataclasses.dataclass in imports.

# FIRST_NEW_EXECUTION_BOUNDARY

CODE_PATH_PROVED + DIRECT_EVIDENCE: all three stop in contextor.core.source (contextor/core/source.py), after BIND __all__. Next AST node is ClassDef SourceError(ValueError), line 22, AST column 0. package_model._compile calls _safe_passive_class_definition, which rejects nonempty class bases. This is an unsupported reached statement / restricted model limitation; no import-order hazard is demonstrated. The model exposes target module contextor.core.source but no source coordinate or explicit rejected-node field; node identification follows the current AST and ordered compile path.

# D8_VS_D9

- contextor.repo_generator: external 35->47; dataclass 1->2; events 68->91; ProjectGraph crossed yes->yes; ImportRef crossed no->yes; stop imports.py/ImportRef -> source.py/SourceError(ValueError); hazard observed no->no; conditional completion no->no.

- contextor.ui: external 20->32; dataclass 1->2; events 37->60; ProjectGraph crossed yes->yes; ImportRef crossed no->yes; stop imports.py/ImportRef -> source.py/SourceError(ValueError); hazard observed no->no; conditional completion no->no.

- contextor.core.analysis.state_manager: external 2->14; dataclass 1->2; events 17->40; ProjectGraph crossed yes->yes; ImportRef crossed no->yes; stop imports.py/ImportRef -> source.py/SourceError(ValueError); hazard observed no->no; conditional completion no->no.

# PERFORMANCE

D9 inventory=12.021249s; evaluations=6.491351s, 5.838771s, 4.177591s; total=28.528998s. D8 references: inventory=10.133585s, evaluations=4.064717/5.844797/5.067897s, total=25.113792s. Comparison only.

# AUTHORITY_LIMITATIONS

Current LIVE graph does not prove runtime execution. Source-bound model does not authenticate sys.path or finder behavior. Assumed external success and frozen dataclass decoration are conditional only. UNKNOWN is not harmlessness. No warning changes or promotion to runtime-safe cycle. Persistent MCP/LIVE interpreter adoption of R8 remains unknown; fresh diagnostic process adoption is separately proven.

# FILES_CHANGED
walkthrough.md only (diagnostic report).

# FULL_DIFFS
ACTUAL_DIFF=DIFFS=NONE for source/test/docs; D9 introduced no source/test changes. Existing R8 changes are preserved in current HEAD and are outside this diagnostic diff.

# FINAL_VERDICT

PASS for the completed and reproducible D9 diagnostic with 222/222 same-generation source SHA matches. ImportRef conditional-model progression is proven for all three entries. Outcomes remain UNKNOWN at SourceError(ValueError); runtime cycle safety remains UNKNOWN.
