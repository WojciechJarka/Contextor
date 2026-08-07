## [1.2.0-beta] - 2026-08-06

### Added

#### Model Context Protocol (MCP)

- Introduced a native FastMCP server, transforming Contextor into an LLM-oriented query engine.
- Added `MCP_installer.bat` for automated MCP environment setup.
- Added Level-3 `get_file_edit_context` providing a complete single-shot editing context.
- Added `get_report_diff` for architectural regression analysis between runs.
- Added architectural boundary validation in `get_layer_isolation`.
- Added secure sandbox execution for `query_json_data`.

#### Graph Analytics

- Added `graph_analytics.json` report.
- Added fan-in, fan-out and export-degree metrics.
- Added PageRank, Betweenness, Hub, Authority and Bridge centrality scores.
- Added module visibility classification (`public`, `internal`, `private`).
- Added weighted dependency matrix with dependency type classification.
- Added Jaccard complete-linkage clustering.
- Added dependency type breakdown statistics.

#### Reporting

- Added strict separation between global, layer and single-file reports.
- Added dedicated layer index dictionaries.
- Added Git-aware report diff engine.
- Added Git metadata to single-file reports.
- Added independent metrics and hotspots for the `tests` layer.
- Added automatic timestamp-based report versioning.

---

### Changed

#### Reporting Engine

- Replaced raw JSON reading with synthesized MCP query endpoints.
- Replaced GUI parser string search with indexed lookup.
- Replaced connected-component clustering with complete-linkage clustering.
- Optimized report routing and index dictionary management.
- Optimized LLM context generation using compact indexed structures.

#### Architecture

- Split `engine.py` into `generators.py` and `io_manager.py`.
- Split `generators.py` into dedicated generator modules.
- Retained backward-compatible facades after refactoring.
- Eliminated oversized architectural hotspots.

#### Performance

- Removed generation of `artifacts.json` and `artifacts_usage.json`.
- Standardized on compact indexed artifact reports.
- Added extraction limits for clusters and usage details.
- Reduced disk I/O and report size significantly.

---

### Fixed

#### MCP

- Fixed Windows multiprocessing initialization (`freeze_support()`).
- Fixed stdout corruption breaking JSON-RPC communication.
- Fixed argument ordering in `analyze_single_file`.
- Fixed layer normalization in `get_layer_isolation`.
- Fixed incorrect `module_count` returned by `get_project_architecture`.
- Fixed incorrect `risk_score` calculation in `get_file_edit_context`.

#### Reporting

- Fixed missing layer index dictionaries.
- Fixed global index overwrite detection.
- Fixed Rewrite Index fallback logic.
- Removed thread-unsafe Rewrite button from the JSON Parser window.

---

### Security

- Replaced unrestricted `eval()` in `query_json_data` with a sandboxed execution environment.

---

### Developer Experience

- Improved MCP support for LLM workflows.
- Added architectural context pills for AI-assisted refactoring.
- Improved report discoverability and automatic report resolution.

---

### Validation

- Verified all MCP tools in a full end-to-end test.
- Cross-validated generated reports against the analyzed source code.
- Confirmed correct isolation of global, layer and single-file report scopes.
- Verified zero cross-scope index overwrites.
### Known limitations

- The graph cache in `core/graph/incremental.py` remains in-memory only,
  so it never hits in a single CLI run.
- Comments and docstrings mix English and Polish.

## [Patch] - 2026-08-05

### Added & Improved

- **Global & Layered Reporting Separation**: Global reports are now robust and logically separated into distinct layers (e.g., `contextor` vs `tests`). Each layer receives its own specific metrics, structure, artifacts, and summary without mixing contexts.
- **Comprehensive Metrics**: Added complete global metrics (e.g., `density_hard`, `edges_hard`) and detailed per-layer `per_module` metrics (`in/out degree`, `internal_in/out`) to accurately evaluate hotspots and isolated code.
- **Hotspots, Technical Debt & Action Items**: Outbound hotspots and structural bottlenecks are now directly linked with actionable items (e.g., `WARNING: Refactor '...' (out_degree=X, type=OUTBOUND_HOTSPOT)`). Technical debt is synthesized in a normalized `debt_summary`.
- **Zero-Collision Validations**: Namespace collisions and dependency cycles are properly monitored. Stable analysis explicitly validates and reports `total_collisions: 0` and `cycle_count: 0`, guaranteeing analysis fidelity.
- **Tests Layer Observability**: `tests` is now treated as an independent architectural boundary with its own structural filtered metrics and hotspots, enabling analysis of test impact on the production architecture without noise.
- **Robust Strict String-Based GUI Parser**: Replaced the deep-search algorithm with a highly performant, short-circuiting strict string parser to definitively prevent false-positive matches of modules vs symbols.
- **Automated Output Routing & Timestamps**: All generated reports are now safely tagged with a `datestamp` to track history. High-risk layer reports are safely isolated into `[repo]_high_risk_layers_[datestamp]` subfolders.
- **Test Suite Enhancements**: Expanded the test suite coverage to accurately test the updated parsing mechanisms and architectural isolation logic.

- **Git & Diff Engine Integration**: Contextor now deeply integrates with Git context. Added a dedicated 
epo_state module and diff_engine to automatically identify previously generated reports, compute deltas across runs (hotspots, cycles, layers, and debt score), and accurately evaluate technical regression or improvements across the repository.
- **Granular Git Impact Reports**: Single-file reports now feature a dedicated git section containing recent commits, authors, and truncated file patches, allowing the LLM to understand immediate local file changes alongside architectural implications.

- **Model Context Protocol (MCP) Server**: Introduced a native FastMCP server allowing LLMs (like Claude) to directly invoke Contextor. The server exposes tools for global analysis (nalyze_project), layered analysis (nalyze_layer), single-file insights (nalyze_single_file), artifact filtering (ilter_artifacts), and reading raw JSON reports.
- **MCP Environment Installer**: Added MCP_installer.bat to safely handle environment detection and installation of MCP dependencies alongside Contextor.

- **Engine Refactoring**: Split the oversized `contextor.core.reporting_engine.engine` module (SRP violation) into `generators.py` (business logic) and `io_manager.py` (I/O operations). This decoupling significantly improves maintainability and testability. Updated `facade.py` imports and completely refactored the test suite to include robust integration tests. The old engine module has been safely backed up to `legacy/engine.py`.
- **I/O Optimization & Bloatware Removal**: Completely eliminated the generation and disk-writing of massive `artifacts.json` (70 MB) and `artifacts_usage.json` (140+ MB) reports. Contextor now generates and relies exclusively on a highly optimized, index-based `artifacts_compact.json`, reducing disk I/O latency and saving hundreds of megabytes per run.
- **Strict Indexed Extraction Engine**: Rewrote the core search/filtering engine in `gui_parser.py`. Replaced the slow, raw string-matching algorithm (based on `json.dumps` serialization) with a blazing-fast index-based traversal, resolving definitions and consumers against the compact modules array.
- **LLM Token Efficiency Maximization**: The output "single LLM context" subsets generated by the GUI parser now natively retain the `compact` integer-indexed format. This drastically minimizes the input token cost while supplying LLMs with a perfect structural "blast-radius" map.
- **Cluster & Detail Saturation Limiting**: Introduced strict safeguards (`MAX_CLUSTERS = 30` and `MAX_USAGE_DETAILS = 15`) in `artifact_usage_report.py` to truncate long-tail extraction candidates and AST detail bloat, preventing infinite context scaling on massive codebases.

## [Patch] - 2026-08-06

### Added

- **Graph Analytics Report** (`graph_analytics.py`): A new dedicated report generated alongside existing reports for all three reporting levels — full repository, per-layer, and single-file. Addresses the following gaps missing from previous reports:
  - `fan_in` (consumer count), `fan_out` (provider count), `export_degree` (number of artifacts exported by a module)
  - `visibility` classification per module: `public` (consumers outside its own layer), `internal` (consumers only within the same layer), `private` (no consumers)
  - Architectural `layer` classification: `runtime`, `contract`, `engine`, `ui`, `cli`, `adapter`, `tests`
  - Graph-centrality scores: `betweenness`, `pagerank`, `hub_score`, `authority_score`, `bridge_score` — all computed in pure Python without external dependencies
  - **Module Dependency Matrix**: weighted, indexed module-to-module dependency map with `weight` (shared artifact count) and `dep_types` (`call`, `inheritance`, `import`) for each directed edge
  - **Jaccard-similarity clusters** using complete-linkage algorithm (threshold ≥ 0.30): replaces the previous connected-components approach that produced a single cluster containing the entire repository (`size=102`); new clusters are semantically tight (`size=2–15`)
  - `dependency_type_breakdown`: global aggregation of edge types across the entire dependency matrix
  - Report is fully indexed (compact integer IDs via `IndexDictionary`) consistent with all other Contextor reports; human-readable form available via the GUI "Rewrite Index" button

- **Index Dictionary Deduplication**: When saving a new `index_dictionary.json`, the engine now checks for an existing dictionary with the same base name:
  - Identical content → old file is silently removed and replaced by the new one
  - Different content → old file is renamed with an `_outdated` suffix before writing the new one
  - Applies to all three reporting paths: full project (`save_all_reports`), layer, and single-file (`analyze_single_file`)

- **Contextor Query Layer (MCP Server)**: Completely refactored `mcp_server.py` to serve as a specialized query layer optimized for Large Language Models.
  - Replaced raw JSON file-reading tools with dynamic endpoints: `get_project_architecture`, `get_module_context`, `get_artifact_blast_radius`, and `get_layer_isolation`.
  - Added automatic path resolution (`_find_latest_report`) so LLMs no longer need to know the exact timestamped filenames of reports.
  - LLMs now receive perfectly sized, synthesized insights (including reverse-mapped string dependencies) instead of massive arrays of integer indices.

### Fixed

- **MCP Server on Windows** (`mcp_server.py`): Added `multiprocessing.freeze_support()` call in the `__main__` block. Without it, `ProcessPoolExecutor` inside `ContextorFacade.analyze_project()` caused a `RuntimeError` during subprocess bootstrapping on Windows, making every MCP `analyze_*` tool call fail silently.
- **MCP Stream Corruption**: Forced all internal Contextor progress logs to be routed to `sys.stderr`, preventing stdout pollution from breaking the JSON-RPC communication stream used by MCP.
- **MCP Tool `analyze_single_file`**: Fixed an argument ordering bug where `repo_root` and `file_path` were swapped when calling the facade.
- **MCP Tool `get_layer_isolation`**: Fixed a bug where passing a full path (e.g., `contextor/core`) would fail to match the layer index; it now normalizes the input automatically.

### Architecture Refactoring
- **Generators Hotspot Elimination**: Split the massive `contextor.core.reporting_engine.generators` module (674 lines) into four domain-specific components: `summary_generator.py`, `structure_generator.py`, `collisions_generator.py`, and `layer_slicer.py`. The original `generators.py` was retained as a backward-compatible re-exporting facade. This refactoring completely eliminated the module from the top 5 global architectural hotspots (score dropped from 0.84 to unlisted), drastically reducing project technical debt.
- **MCP Context Pill**: Added a new Level-3 MCP tool `get_file_edit_context`. It provides LLMs with a specialized, single-shot context pill prior to editing a file, combining module metrics, API signature blast radius, and dependency trees into one response.

### Bug Fixes & UI Enhancements
- **Layer Report Index Dictionary Omission**: Fixed a bug where isolated layer reports failed to save their own `index_dictionary.json` file. `layer_slicer.py` now correctly surfaces the layer-specific index, and `io_manager.py` saves it with the correct layer prefix (e.g., `Contextor_Repo_core_index_dictionary_[datestamp].json`).
- **Global Index Overwrite Prevention**: Fixed an aggressive wildcard glob in `_save_index_dictionary_with_dedup` that was incorrectly flagging layer-specific index dictionaries as "outdated" versions of the global repository index and renaming them. The pattern matcher now strictly verifies segment length.
- **Smart Rewrite Fallback**: Upgraded the GUI "Rewrite Index -> Txt" tool to reliably locate the global repository index. It now searches for an exact datestamp match (even if outdated), explicitly ignores layer-specific or single-file dictionaries (by preferring the shortest filename), and surfaces a robust UI `MessageBox` fallback confirmation if it needs to use the latest available global index.
- **Parser GUI Cleanup**: Removed the redundant, thread-unsafe "Rewrite Index" button from the JSON Parser window, consolidating this capability exclusively to the main application window which properly supports native file dialogs and prompts.
- **MCP `get_project_architecture` — wrong `module_count` field**: Fixed a wrong key lookup (`metrics.global_module_count` → `metrics.nodes`). The tool was returning `module_count: 0` on every call despite the summary report containing the correct value.
- **MCP `get_file_edit_context` — `risk_score` always zero**: Fixed by replacing the non-existent `hotspot_score` key lookup (which lives in `summary.json`, not in `graph_analytics.json`) with a computed proxy based on `(betweenness + hub_score) / 2`, sourced correctly from `graph_analytics.json`.

### Production Test — 2026-08-06
Full end-to-end production test covering all 10 MCP tools and all three report types (full project, layer, single-file). All tools passed. Report data cross-validated against actual source code — data found to accurately reflect the real state of the codebase. Index dictionary separation between global, layer, and single-file scopes confirmed working with no cross-scope overwrites.

### MCP Refinements & Security Updates
- **Secure Sandbox for `query_json_data`**: Replaced the unrestricted `eval()` call with a strictly sandboxed execution environment (whitelisted built-ins only) to prevent arbitrary code execution vulnerabilities.
- **Accurate `risk_score` for Edit Context**: Fixed `get_file_edit_context` to correctly extract the true `hotspot_score` from `summary.json`, using the centrality metrics from `graph_analytics.json` only as a secondary fallback.
- **Test Coverage Context**: Enhanced `get_file_edit_context` to expose `tests_covering` by identifying modules from the `tests.*` layer that depend on the target module, giving LLMs immediate visibility into available test coverage.
- **Layer Boundary Violations**: Upgraded `get_layer_isolation` to detect and report architectural boundary violations (e.g., when a lower-tier layer like `ui` directly imports a higher-tier layer like `runtime`), enforcing strict layer hierarchy (`tests > ui/cli > contract > engine > runtime > adapter`).
- **Regression Analysis Tool (`get_report_diff`)**: Added a new MCP tool to expose the `report_diff` functionality. It computes the delta between the last two analysis runs, surfacing newly introduced hotspots, resolved debt, and cycle changes directly to the LLM.
