# Contextor

Contextor

Contextor MCP is an architectural intelligence layer that allows Large Language Models (LLMs) to autonomously explore, understand, and reason about complex Python repositories through the Model Context Protocol (MCP).

Instead of sending entire codebases into an AI context window, Contextor automatically builds a persistent architectural map of the repository and provides the LLM with only the precise context required for the current task — dramatically reducing token usage, inference cost, and unnecessary code scanning.

Through static analysis, Contextor discovers project structure, dependencies, symbol ownership, artifact relationships, architectural risks, and technical debt without ever executing the analyzed code.

Contextor acts as a bridge between software repositories and AI agents, giving LLMs architectural awareness similar to having an always-updated technical map of the entire codebase.

---

## What Contextor MCP Does

- **Semantic & Architectural Diffing:**  
  Unlike Git, which tracks character-by-character textual changes, Contextor tracks *structural health*. It detects if a new commit accidentally introduced a circular dependency, inflated technical debt, or violated layer boundaries (e.g., Core layer calling UI).
- **Dependency Graph Building:**  
  Extracts module dependencies, including hard imports and soft textual references, to construct a complete architectural graph of the project.
- **Architectural Debt Calculation:**  
  Calculates structural risk indicators by detecting isolated modules, namespace collisions, dependency hotspots, and architectural inconsistencies.
- **Artifact Consumption Tracking (Blast Radius):**  
  Analyzes how symbols (classes, functions) are consumed throughout the repository. Reports evidence-backed direct static consumers from calls, API imports, and detectable reflection patterns. Dynamic Python behavior can make this radius incomplete, so it is presented with its evidence scope rather than as mathematically exact.
- **Context Generation for LLMs:**  
  Generates ultra-compact, indexed JSON matrices and Markdown reports designed specifically for Large Language Models. It acts as a structural "GPS" for AI, saving thousands of tokens by delivering precise architectural context instead of raw, concatenated source files.

---

## What Contextor MCP Does NOT Do

- **Textual Code Diffing (Like Git):**  
  Contextor MCP is not a version control system. It will not show you that line 42 changed `foo` to `bar` or track whitespace changes. For exact textual "search & replace" diffs, use Git. Contextor focuses exclusively on the *architectural consequences* of those changes.
- **Dynamic Analysis:**  
  Contextor MCP does not execute analyzed code. All analysis is performed through rapid static repository inspection.
- **Deep Runtime Type Inference & Reflection Frameworks:**  
  Contextor MCP relies on AST parsing and deterministic symbol analysis rather than runtime execution. Dynamic dispatch patterns (e.g., `getattr()`, `__import__`, dependency injection) and heavy reflection used by frameworks like Django or FastAPI cannot be perfectly resolved through static analysis alone. For "pure" Python code, accuracy is extremely high, but for heavily dynamic framework "magic", the structural graph may be incomplete. Contextor partially addresses this through *soft reference* detection (pattern-based textual matching).
- **Automated Code Modification:**  
  Contextor MCP does not rewrite code, fix bugs, or format files. It provides the map and the metrics; you (or your LLM) perform the surgery.
- **Security Auditing:**  
  Contextor MCP identifies structural risks and technical debt, but it is not a dedicated SAST security vulnerability scanner.

---

## Model Context Protocol (MCP) Integration

Contextor natively supports the **Model Context Protocol**, allowing Large Language Models (like Claude) to autonomously explore your repository's architecture without flooding their context window.

- **Contextor Query Layer:** Instead of serving raw, massive JSON files, the server exposes highly targeted endpoints (e.g., `get_project_architecture`, `get_module_context`, `get_artifact_blast_radius`).
- **Non-blocking Analysis Jobs:** Repository, layer, and single-file analyses return durable job IDs with progress status, so long report runs do not time out the MCP client.
- **Shared Canonical LIVE:** One authenticated localhost owner keeps the current repository state in RAM for both desktop and MCP. The desktop watcher publishes file changes automatically after the initial full analysis; revisioned disk snapshots are used only for recovery.
- **LIVE-first Context:** Project architecture, file-edit safety, artifact blast radius and layer isolation use current LIVE state first. Saved reports enrich expensive metrics and historical evidence but are not required for structural answers.
- **Bounded Context:** By merging data from multiple reports, the server delivers compact synthesized insights, resolves requested registry IDs, and exposes limits plus truncation counters for larger collections.
- **Architectural Regression Analysis:** `get_report_diff` compares consecutive canonical runs—including working-tree states on the same commit—and surfaces changes in structural metrics, layers and technical debt.
- **Focused Refactor Evidence:** Nested-layer isolation and static test-reachability paths through aliases, re-exports and facades give the LLM compact evidence without claiming runtime coverage.
- **Versioned LIVE Queries:** `describe_canonical_state` publishes the safe schema and operator contract, while `query_canonical_projection` performs bounded JSON queries over normalized modules, artifacts, and dependencies without evaluating Python expressions. The older `query_canonical_state` tools remain temporarily available for migration only.
- **MCP Server Restart Boundary:** `update_file` synchronizes code on disk with Contextor's canonical state, but it cannot reload Python code already executing inside the MCP process. When the edited target is `contextor/mcp_server.py`, the response sets `runtime_restart_required: true`; restart the MCP server and verify the changed endpoint live before treating runtime behavior as current.

---

# Features

- Static Python repository analysis
- AST-based source inspection
- Dependency graph generation
- Hard import and soft reference analysis
- Symbol ownership tracking
- Artifact consumption mapping
- Circular dependency detection
- Namespace collision detection
- Architectural hotspot identification
- Technical debt scoring
- LLM-ready context generation
- JSON reporting
- Single-file architectural analysis
- Separation of logical layers (e.g. core vs tests) for distinct, isolated architectural reports
- Comprehensive global and per-layer metrics (density, in/out degree, internal vs external connections)
- Hotspot classification and technical debt scoring directly linked to architectural action items
- Dedicated name collision reporting with zero-conflict validation
- json parsing engine (for extraction of info about single file or single symbol from full artifacts report)
- Stable canonical report names plus immutable timestamped snapshot subfolders for repository, layer, and single-file runs; high-risk layer packages use the same history model
- Git integration for commit and branch tracking
- Automated JSON report diffing engine detecting regressions in technical debt, hotspots, and architectural bottlenecks
- Detailed single-file Git patches bridging the gap between local changes and architectural impact
- **Model Context Protocol (MCP) Server** enabling direct, autonomous integration with LLMs (e.g. Claude Desktop, Antigravity)
- **Graph Analytics Report** — per-module `fan_in`, `fan_out`, `export_degree`, `visibility`, architectural `layer`, graph-centrality scores (`betweenness`, `pagerank`, `hub_score`, `bridge_score`), Jaccard-similarity clusters, and a weighted Module Dependency Matrix; generated for all three report levels (full repo, layer, single file)
- **Persistent Identity Registry** — a transactional, atomic indexing layer that maintains globally stable, generation-based string identifiers (e.g. 17/4, A5/2) for modules and artifacts across runs. It isolates repository identity state inside .contextor/ (automatically gitignored), providing consistent identity resolution, recovery of removed objects, and collision-free identifier reuse without polluting generated reports or repository history.

---

# Prerequisites

- **Python 3.10 or newer.** Contextor uses `X | Y` type annotations,
  which are evaluated at import time and are a syntax error on 3.9.
- **Tkinter**, for the graphical interface. Bundled with Python on
  Windows and macOS; on Debian/Ubuntu install `python3-tk`. Not needed
  for the CLI.
- Git (optional, required for repository context information). Must be
  installed and available in your system's `PATH`.

The only third-party runtime dependency is `orjson`.

---

# Installation

Unpack the ZIP of the last release.

To ensure your system's Python environment remains clean and stable, Contextor relies on isolated virtual environments. 

Simply double-click **`run_contextor.bat`**. 

This script will automatically create an isolated Python virtual environment (`venv`) inside the project folder, install all required dependencies there, and launch the Contextor interface. This guarantees your global Python environment remains completely untouched and safe.

---

# Project Layout

```
contextor/              the installable package
    __main__.py         entry point (python -m contextor)
    cli.py              command-line interface
    core/               analysis engine
    ui/                 Tkinter interface
    repo_generator/     source bundling tool
main.py                 launcher for running from a source checkout
tests/                  test suite
```

---

# How to Use

Contextor provides both a Command-Line Interface (CLI) and a Graphical User Interface (GUI).

## Using the GUI

The easiest way to start Contextor is:

```bash
python main.py --gui
```

Or, once installed:

```bash
python -m contextor --gui
```

On Windows, you can also use:

```bash
run_contextor.bat
```

The launcher will:
- Detect the Python installation.
- Verify required dependencies.
- Install missing requirements when necessary.
- Start the Contextor graphical interface.

Then:
- Select the target repository.
- Configure exclusion rules for directories or specific files.
- Generate architectural reports.
- Inspect project layers, dependencies, and relationships.

## Using the CLI

Run an automated repository analysis:

```bash
python main.py /path/to/your/project
```

Contextor will:
- build the repository index;
- analyze dependencies;
- resolve symbol relationships;
- detect architectural cycles;
- calculate technical debt indicators;
- generate JSON and Markdown reports.

Or, once installed, from any directory:

```bash
contextor /path/to/your/project
```

Additional options:

```bash
contextor --help                       # full option list
contextor PROJECT --layer PROJECT/core # add a per-layer report
contextor PROJECT --file PROJECT/x.py  # add a single-file deep dive
contextor PROJECT --output ./reports   # choose the output directory
contextor PROJECT --quiet              # suppress progress logging
```

Exit codes: `0` no issues, `1` validation errors reported,
`2` invalid arguments, `130` cancelled.

Generated reports are saved into the `output/` directory next to the
Contextor installation, regardless of the directory you launch from.
Override the location with `--output` or the `CONTEXTOR_OUTPUT_DIR`
environment variable.

Each analysis keeps stable canonical filenames for MCP clients and also writes
a historical copy under `output/<repository>_<timestamp>/`. The canonical files
represent the latest run; timestamped subfolders are suitable for comparisons.

---

# Files Contextor Writes

Contextor writes reports externally, but maintains a lightweight, git-ignored registry inside the analyzed repository for stable ID management:

| Location | Contents | Override |
|---|---|---|
| `output/` next to the installation | Generated reports | `CONTEXTOR_OUTPUT_DIR` |
| `.contextor/` inside the analyzed repository | Persistent Identity Registry (automatically added to `.gitignore`) | N/A |
| User cache directory | Parse and graph caches, keyed per repository | `CONTEXTOR_CACHE_DIR` |
| User config directory | GUI state, exclude configuration | `CONTEXTOR_STATE_DIR` |

---

# Generated Output

Contextor generates structured architectural reports designed for both developers and AI systems.

Generated reports include:
- repository architecture overview;
- dependency relationships;
- symbol ownership and usage information;
- artifact consumption data;
- architectural hotspots;
- technical debt indicators;
- cycle detection results;
- graph analytics (fan-in/out, centrality, Jaccard clusters, Module Dependency Matrix);
- LLM-ready context snapshots.

The generated context allows Large Language Models to reason about complex repositories with architectural awareness instead of relying only on raw source files.

---

# How Contextor Works

Contextor uses static analysis techniques:
- Python AST parsing;
- deterministic symbol extraction;
- dependency graph construction;
- relationship mapping;
- architectural heuristics.

The analyzed code is never executed.

---

# License

This project is distributed under the:

**Contextor Community License v1.0**

Contextor is released under a source-available license with a non-commercial restriction.

**This license is not an OSI-approved Open Source license.**

The software may be used, modified, and distributed for:
- personal use;
- educational purposes;
- academic research;
- scientific research;
- non-commercial research projects;
- hobby projects;
- evaluation and testing.

Commercial use, including use by commercial organizations or integration into commercial products and services, requires a separate commercial license.

For complete licensing terms, please see the `LICENSE` file.

---

# Disclaimer

## No Warranty / Liability

This software is provided "as is", without warranty of any kind, express or implied.

The authors are not responsible for any consequences, data loss, architectural decisions, or damages resulting from the use of this tool.

Generated reports represent static architectural analysis and should be reviewed before making significant changes to production systems.

---

# Contact

For commercial licensing inquiries or other questions:

[wojciech.jarka77@gmail.com](mailto:wojciech.jarka77@gmail.com)
