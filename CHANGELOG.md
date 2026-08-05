# Changelog

All notable changes to Contextor are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-01

A correctness, packaging and performance release. Contextor is now an
installable package, no longer writes into the repositories it analyzes,
and its artifact consumption report — previously empty on every run —
actually produces data.

### Added

#### Smart Clipboard Path Extraction

Implemented a robust text parser for the builder window. Users can now paste unstructured, messy text directly from chats or documents. The parser automatically detects and extracts valid, existing file paths while safely ignoring numbered lists, inline comments, surrounding text, and non-existent files.

#### Unselected Files Safeguard on Generation

Added a safety check before generating the repository. If there are files present in the list that have not been explicitly selected (highlighted), a prompt will now appear. It lists the unselected files and asks the user whether to include them, skip them, or cancel the generation, preventing accidental omissions.

#### Enhanced GUI Test Suite Installer & Fallback Messaging

Upgraded the `GUI_test_suite_installer.bat` to properly detect its own location, automatically install the editable development environment (`pip install -e .[dev]`), and safely check for `pytest` presence without forcing specific versions. This installer script serves as a dedicated rescue/fallback option if the automatic installation of test suite packages via a virtual environment (venv) fails for any reason. The GUI test runner now provides a descriptive fallback error log advising the user exactly which dependencies are missing and pointing them to the installer script, instead of throwing raw Python tracebacks.

### Fixed

#### Artifact consumption report produced no data at all

`generate_artifact_usage_report()` returned an empty artifact index on
every run. The module view passed to `build_symbol_references()` was
missing its `imports` attribute, so each module raised `AttributeError`
inside its worker process, and a bare `except Exception: pass` discarded
the failure. The report was silently empty and no error was ever shown.

Analyzing Contextor's own source now yields 414 artifacts and 106 shared
artifacts, where it previously yielded none.

#### Dependency installation was impossible

`Requirements.txt` contained English prose rather than a dependency
specification, so `pip install -r` — which both the README and the
Windows launcher instructed users to run — failed with a parse error.
The file is now a real requirements file named `requirements.txt`.

#### Analysis wrote into the repository under inspection

The per-file cache created a `.contextor_cache` directory inside the
analyzed project, one entry per source file, contradicting the read-only
guarantee stated in the README and the GUI. Caches now live in the user
cache directory, namespaced by a hash of the repository's absolute path.

#### Cache entries could collide between different source files

Cache file names were derived by replacing path separators, so
`core/graph.py` and `core_graph.py` mapped to the same entry. Names are
now derived from a hash of the relative path, and each entry records its
source path for verification.

#### Cycle detection crashed on large repositories

The depth-first search was recursive and exceeded the interpreter
recursion limit on dependency chains longer than roughly 1000 modules —
precisely the repositories Contextor targets. It is now iterative.
Verified against the previous implementation on 300 randomly generated
graphs with identical results, and on a 20,000-module chain that the
recursive version could not process.

#### Reports were written relative to the working directory

Report and cache paths were resolved against the process working
directory, so output landed wherever the user happened to launch from,
while the GUI looked for it next to the installation. All paths are now
resolved centrally and independently of the working directory.

#### Process pool only worked when launched through `main.py`

On spawn platforms, worker processes could not resolve the package and
failed with `ModuleNotFoundError`. This went unnoticed because
multiprocessing re-executed `main.py` in the child, which happened to
perform the necessary setup. Any other entry point was unusable. Fixed
by making Contextor a real package.

#### Circular import between the domain and graph layers

`contextor.core.domain` imported `ProjectGraph` from
`contextor.core.graph.graph`, which merely re-exports it, creating a
cycle that only resolved because of the order in which modules happened
to be imported. It now imports from `contextor.core.domain.graph`, where
the class is defined. A regression test imports each layer first in a
fresh interpreter.

#### Module semantics were computed and discarded

`collect_semantic_context()` ran module semantics, effect and import
usage analysis whose output never reached the report — the
`semantic_analysis` key was built from unrelated data. The results are
now emitted under `module_semantics`.

#### Non-Python files entered the dependency graph as modules

Any path ending in `.py` became a module, whether or not it was Python.
Binaries, JSON and text files were indexed as modules with no
dependencies, and a *directory* named `foo.py` became a module of its
own. The reports then drew conclusions from them — advising that
`assets.blob` was an "isolated module" to "remove or integrate".

Nothing ever raised, which is why the GUI's red banner ("ADD ALL
NON-PYTHON STRUCTURES TO THE EXCLUDE LIST … OTHERWISE ERRORS WILL
OCCUR") described the wrong symptom. The actual behaviour was worse
than an error: confident architectural advice derived from junk.

Directories are no longer matched, a file that cannot be parsed is no
longer treated as a module with zero imports, and every skipped file is
reported with a reason — in the log and under `skipped_files` in the
summary. The banner is replaced by a statement of what actually
happens; excluding non-Python content is now an optimization rather
than a prerequisite.

#### Valid Python was rejected for its encoding

Source was read as strict UTF-8, so two kinds of file CPython accepts
were treated as unreadable: those beginning with a UTF-8 BOM, and those
declaring another encoding through a PEP 263 header
(`# -*- coding: cp1250 -*-`). Reading now goes through `tokenize.open()`,
which applies CPython's own rules, so Contextor and Python agree on what
counts as readable Python. All source reading is consolidated in
`contextor/core/source.py`; it was previously reimplemented at nine call
sites with four different error-handling policies.

#### Cancelling validation reported the run as clean

Four checkpoints in the validator were written against the older
convention and returned the errors collected so far. Aborting an
analysis therefore produced a truncated but well-formed result, which
the GUI presented as "No issues found. Repository is healthy!".
Cancellation now goes through a single `checkpoint()` primitive that
raises, so a partial result cannot be mistaken for a complete one.

#### Windows launcher silently ignored the virtual environment

`run_contextor.bat` enabled delayed expansion, which makes `cmd` treat
`!` as a variable delimiter. Any project path containing one — for
example `C:\!Projects\Contextor` — was stripped to
`C:\Projects\Contextor`, so the directory change failed, the
virtual environment was never activated, and Contextor ran on whatever
Python happened to be on `PATH`. The only visible symptom was a single
`The system cannot find the path specified.` line, after which the
launcher reported dependencies as fine and carried on.

The launcher no longer enables delayed expansion, invokes the virtual
environment's interpreter directly instead of relying on `activate.bat`
succeeding, and stops with a specific message at every failure point
rather than falling through.

#### Markdown export created a stray directory in the working directory

`generate_llm_markdown()` called `makedirs()` on the caller-supplied
path before that path was resolved, recreating the working-directory
dependence that the rest of the release removes.

#### Other fixes

- `Module` declared itself hashable but raised `TypeError`, because
  `frozen=True` generated a hash over a `list` field.
- The AST cache was keyed on file path alone and served stale trees
  after a file changed; the key now includes modification time and size.
- Cancelling an analysis raised a bare `Exception`, so the GUI reported
  a crash. Cancellation now uses a dedicated `AnalysisCancelled` type,
  and partial results are no longer written to disk as if complete.
- `detect_cycles()` and the metrics pipeline returned empty results on
  cancellation, which then flowed onward into saved reports.
- The import resolver stripped a hardcoded `repo_guardian.` prefix from
  imports in every analyzed repository. The prefix is now inferred from
  the repository's own import statements.
- `core.__all__` advertised two names the module does not define, so
  `from contextor.core import *` raised `AttributeError`.
- Single-file reports were named after the bare file stem, so two files
  with the same name in different packages overwrote each other.
- Report writes are now atomic, so an interrupted run cannot leave a
  truncated JSON file behind.
- Exclude configuration was keyed by folder name, so two repositories
  named `api` in different locations shared one configuration.

### Added

- **Dark mode**, with a toggle button in the top-right corner of the
  main window. Light remains the default; the choice is remembered
  between sessions. Switching repaints every open window, including the
  Exclude, Repo Builder and JSON Parser dialogs, and the classic Tk
  widgets (log console, list boxes, scrollbars) that do not follow ttk
  styles on their own.

  The palette moved into `Palette` dataclasses with `LIGHT` and `DARK`
  instances. Colour names are now read through the module
  (`theme.BG`) rather than imported by value, because `from theme import
  BG` binds at import time and would pin whichever palette was active
  when the module first loaded. Progress readouts and the CPU indicator
  became ttk styles instead of inline colours.

- **"Test suite" button in the GUI header**, beside the CMD log toggle.
  Runs the whole suite in sequence, streaming each test into the log box
  with a live progress bar, and reports passed/failed/skipped counts plus
  the names of any failing tests. Honours the Stop button, and explains
  what to install if pytest is missing. Tests run in a separate
  interpreter: pytest mutates global interpreter state and several tests
  spawn process pools, neither of which is safe inside a running Tk
  application.

- **Test suite.** The project previously had none. 91 tests now cover
  cycle detection, import resolution, the end-to-end pipeline, path and
  cache behaviour, the artifact report, test discovery, cancellation
  semantics, parallel/sequential equivalence, import hygiene, and the
  test-runner output parsing, and both appearance modes.
- **`pyproject.toml`.** Package metadata, dependencies, and
  configuration for pytest and ruff. `pip install -e .` provides a
  `contextor` command usable from any directory.
- **Command-line interface.** `--layer`, `--file`, `--output`,
  `--quiet`, `--version` and `--help`, via `argparse`. Exit codes: `0`
  no issues, `1` validation errors, `2` invalid arguments, `130`
  cancelled.
- **`python -m contextor`** as an entry point.
- **Skipped-module reporting.** Modules that fail analysis are listed in
  the report under `skipped_modules` instead of disappearing.
- **Environment overrides.** `CONTEXTOR_OUTPUT_DIR`,
  `CONTEXTOR_CACHE_DIR` and `CONTEXTOR_STATE_DIR`.

### Changed

- **Renamed the package from `repo_guardian` to `contextor`.** The code
  addressed itself by a package name that did not exist, resolved at
  runtime by a custom `sys.meta_path` finder. `core`, `ui`,
  `repo_generator` and `cli` now live inside a real `contextor` package,
  and the import machinery hack is gone. `GuardianFacade` and
  `GuardianGUI` became `ContextorFacade` and `ContextorGUI`.

  A side effect: because module identifiers and import statements now
  agree, self-analysis no longer needs any package-prefix stripping and
  every dependency edge resolves by exact match.

- **User state moved out of the installation directory.** GUI state and
  exclude configuration are written to the user configuration
  directory, since an installed package directory is normally not
  writable. Previous locations are still read for backwards
  compatibility.

- **Formatted the entire codebase with ruff** and enabled linting.
  Roughly 1,900 lines of whitespace padding were removed without any
  behavioural change.

- **Consolidated duplicated infrastructure.** Atomic file writing, report
  path resolution, content hashing, the cancellation checkpoint and the
  set of never-indexed directories each existed in several near-identical
  copies. The ignored-directory sets had already drifted apart, so which
  directories were skipped depended on which entry point was used. Each
  now has a single definition in `contextor/core/paths.py` or
  `contextor/core/errors.py`.

- **Report writers import their path helper normally.** Three of them
  used function-local imports to dodge a cycle introduced by the
  reporting package's `__init__`; the helper moved to a leaf module
  instead.

- **The GUI reports absolute output paths.** Completion dialogs showed
  `output/…`, a relative path that no longer names a real directory.

### Performance

- **Symbol reference resolution no longer re-parses the repository for
  every module.** `build_symbol_references()` is invoked once per
  defining module and considers every other module as a potential
  consumer, which meant O(N²) AST parses — four million parses for a
  2,000-file repository. A textual prefilter now skips modules that
  cannot reference the target symbols, backed by a per-process
  identifier cache and a bounded AST cache. The filter is a strict
  superset of the matcher, so results are unchanged.

- **Test traceability mapping** rescanned the full artifact index for
  every module and performed a full recursive filesystem walk per module
  to locate test directories. Both are now computed once.

- **The module index is sent to each worker once instead of once per
  task.** It was embedded in every work item, so a repository with N
  modules pickled and unpickled the entire index N times, and each
  worker rebuilt its view of every module on every task. It is now
  passed through a pool initializer, and the domain objects travel
  directly rather than being converted to dictionaries and reconstructed
  by a hand-written shadow class.

- **One AST cache instead of two.** The reference engine kept its own
  parsed-tree cache alongside the one behind `Module.ast_tree`, so the
  same tree could be retained twice.

- **File fingerprints are resolved once per analysis** rather than once
  per file per defining module, removing an O(N²) pattern of `stat()`
  calls.

- **Test discovery walks the repository once**, collecting directory
  listings in the same pass, instead of two recursive walks plus two
  `exists()` probes per directory per module.

- **`CacheManager`** was constructed per source file, checking and
  creating its directory each time; it is now created once per worker
  process with lazy directory creation.

### Removed

- `restore.py` and `scratch/`, one-off development scripts containing
  hardcoded absolute paths.
- Committed runtime artifacts: a cycle cache file and reports from an
  unrelated project.
- `bootstrap.py` and the `sys.meta_path` import alias, made unnecessary
  by proper packaging.
- Two unreferenced report writers that bypassed path resolution,
  deterministic key ordering and atomic writes.
- The `PACKAGE_ROOT` fallback constant. It was the hardcoded prefix that
  `detect_package_root()` replaced, left behind as a default argument
  where it would have reintroduced the same defect; the parameter is now
  required.

### Security

- Replaced MD5 with BLAKE2b for content hashing. MD5 is unavailable in
  FIPS-restricted environments, where it raises `ValueError`. Neither
  use is security-sensitive; BLAKE2b is also faster.

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

- **Git & Diff Engine Integration**: Contextor now deeply integrates with Git context. Added a dedicated epo_state module and diff_engine to automatically identify previously generated reports, compute deltas across runs (hotspots, cycles, layers, and debt score), and accurately evaluate technical regression or improvements across the repository.
- **Granular Git Impact Reports**: Single-file reports now feature a dedicated git section containing recent commits, authors, and truncated file patches, allowing the LLM to understand immediate local file changes alongside architectural implications.

- **Model Context Protocol (MCP) Server**: Introduced a native FastMCP server allowing LLMs (like Claude) to directly invoke Contextor. The server exposes tools for global analysis (nalyze_project), layered analysis (nalyze_layer), single-file insights (nalyze_single_file), artifact filtering (ilter_artifacts), and reading raw JSON reports.
- **MCP Environment Installer**: Added MCP_installer.bat to safely handle environment detection and installation of MCP dependencies alongside Contextor.

