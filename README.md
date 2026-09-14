# Contextor MCP

**Architectural intelligence for AI coding agents working with Python repositories.**

Contextor MCP gives Large Language Models a persistent, queryable model of a Python codebase instead of forcing them to rediscover the repository through repeated file scans, grep searches, and large source dumps.

It analyzes the repository statically, maintains canonical architectural state, and exposes focused MCP tools that answer questions such as:

- Where is the canonical owner of this behavior?
- What calls or consumes this symbol?
- What depends on this module?
- What will be affected if this artifact changes?
- Which tests are structurally connected to this code?
- What is the safest context to inspect before editing a file?
- How does a value or semantic fact flow through the system?
- Did an edit remain inside the expected architectural flow?

Contextor MCP does not tell an AI agent how to write the code.

It tells the agent **where to look, what is connected, which state is authoritative, and when deeper inspection is necessary.**

---

## Why Contextor MCP Exists

A typical coding agent working on an unfamiliar repository starts with textual exploration:

~~~text
search → grep → open files → more search → reconstruct architecture → edit
~~~

That works, but it forces the model to repeatedly infer system structure from fragments of source code.

Contextor MCP changes the workflow:

~~~text
architecture → owner → dependencies / lineage → exact implementation → edit → verification
~~~

The LLM still performs the reasoning and writes the code.

Contextor MCP supplies the architectural context needed to perform that reasoning without reconstructing the repository from scratch every time.

This is especially useful for large existing codebases, where locating the correct owner, lifecycle, dependency boundary, or semantic flow can consume more context than the actual implementation change.

---

## Core Idea

Contextor MCP builds and maintains a canonical model of the repository.

That model contains much more than filenames and imports. Depending on the analysis family, it includes:

- modules and persistent module identities;
- symbols and persistent artifact identities;
- hard and soft dependencies;
- direct and transitive consumers;
- artifact usage;
- intra-module symbol calls;
- semantic ownership;
- callable interfaces;
- semantic anchors;
- data and call flows;
- exposed surfaces;
- syntax diagnostics;
- dependency topology;
- cycles and architectural hotspots;
- layer relationships;
- technical-debt signals;
- test reachability;
- Git and report-history context.

The analyzed application code is never executed.

---

## Architecture-First Agentic Coding

Contextor MCP is designed around **progressive disclosure**.

An agent should not need to load an entire repository to understand one change.

A typical workflow can look like:

~~~text
1. Identify the relevant module or symbol.
2. Ask Contextor MCP for ownership and architectural context.
3. Inspect call context, consumers, blast radius, or semantic lineage when needed.
4. Retrieve only the exact implementation or source range required.
5. Edit the code.
6. Run focused tests.
7. Query Contextor MCP again to verify that the resulting flow and ownership remain coherent.
~~~

This makes textual search a verification mechanism rather than the primary mechanism for discovering the architecture.

Contextor MCP can therefore participate on both sides of an edit.

**Pre-edit**

- locate the canonical owner;
- establish call paths and dependencies;
- determine blast radius;
- identify relevant tests;
- constrain the safe edit surface.

**Post-edit**

- verify ownership;
- verify call paths;
- verify canonical semantic flow;
- detect unexpected architectural changes;
- confirm that the edited code remains connected to the intended lifecycle.

---

## Canonical LIVE State

Contextor MCP maintains repository analysis as canonical state rather than treating every query as an isolated scan.

A complete repository analysis establishes the baseline.

After that, supported changes can be maintained incrementally through the LIVE system.

The canonical state is revisioned and can contain independently fresh or stale analysis families. Queries use explicit freshness contracts and fail closed when required evidence is unavailable or no longer trustworthy.

This means an MCP answer can distinguish between:

~~~text
known and fresh
known but stale
not materialized
deferred
resource limited
ambiguous
unavailable
~~~

instead of silently presenting incomplete architectural information as current truth.

---

## Universal Semantic Lineage

Contextor MCP includes canonical semantic lineage as a first-class repository-analysis family.

Lineage represents relationships that are difficult to express with imports or a traditional call graph alone, including:

- semantic ownership;
- symbol anchors;
- call and value flows;
- parameter and return relationships;
- state relationships;
- exposed or registered surfaces;
- callable interface descriptors;
- symbolic boundaries that cannot be resolved safely.

Lineage uses persistent canonical identities where exact resolution is possible and preserves explicit symbolic boundaries where it is not.

This allows an agent to ask how a symbol or fact participates in the wider system without rebuilding those relationships from source during every query.

---

## Persistent Identity

Modules and artifacts receive stable, generation-aware identities.

Examples:

~~~text
17/4
A5/2
~~~

These identities survive normal repository evolution and allow Contextor MCP to reason about the same architectural object across analyses even when textual reports or paths change.

Removed identities are retained through recovery history rather than silently reassigned to unrelated objects.

Persistent identities are repository-scoped.

---

## Dependency and Blast-Radius Analysis

Contextor MCP models both direct dependencies and wider architectural impact.

It can expose:

- hard imports;
- soft references;
- direct consumers;
- transitive downstream modules;
- artifact-level blast radius;
- module-level blast radius;
- isolated modules;
- dependency cycles;
- hotspots;
- graph centrality;
- bridge behavior;
- architectural layers;
- dependency matrices;
- shared-usage clusters.

The goal is not merely to answer:

> Where is this symbol referenced?

but also:

> What part of the system depends on this behavior, and how far can a change propagate?

---

## Editing Context

Contextor MCP can construct focused context for code modification without requiring the agent to inspect the entire repository.

Depending on the request, edit context can include:

- the target module;
- architectural role;
- imports and dependencies;
- owned artifacts;
- consumers;
- relevant tests;
- syntax diagnostics;
- blast-radius evidence;
- exact symbol implementations;
- source ranges;
- canonical freshness information.

This supports small, evidence-driven patches rather than broad exploratory context loading.

---

## Test Reachability

Contextor MCP can locate tests structurally connected to production code.

Reachability can follow relationships such as:

- direct imports;
- aliases;
- re-exports;
- public facades.

This is static evidence, not a claim of runtime coverage.

The purpose is to help an agent identify the smallest relevant test surface before escalating to larger test suites.

---

## Architectural Analysis

Contextor MCP also provides repository-level architectural analysis, including:

- dependency graph generation;
- circular dependencies;
- namespace collisions;
- isolated modules;
- architectural hotspots;
- layer violations;
- fan-in and fan-out;
- PageRank;
- betweenness;
- hub and authority scores;
- bridge scores;
- technical-debt indicators;
- dependency matrices;
- shared-usage relationships.

These signals can be queried directly or persisted in generated reports.

---

## Semantic and Architectural Diffs

Git answers:

> What text changed?

Contextor MCP can additionally answer:

> What architectural facts changed?

Canonical report comparison can expose changes such as:

- dependency topology;
- module relationships;
- hotspots;
- layers;
- architectural metrics;
- technical debt.

Git remains the authority for exact textual diffs.

Contextor MCP supplies architectural consequences and context.

---

## MCP Interface

Contextor MCP exposes focused tools rather than requiring an LLM to consume one massive analysis document.

The available tool families include operations for:

### Analysis

- full repository analysis;
- layer analysis;
- single-file analysis;
- asynchronous analysis status;
- LIVE events.

### Repository architecture

- project architecture;
- module context;
- layer isolation;
- canonical-state description and bounded projections.

### Symbols and source

- artifact lookup;
- artifacts owned by a module;
- symbol implementation;
- symbol call context;
- symbol lineage;
- source ranges;
- source search.

### Change planning

- file edit context;
- artifact blast radius;
- module blast radius;
- tests covering a target;
- report comparison.

### Canonical semantic facts

- universal symbol lineage;
- canonical fact lineage;
- persistent identity-backed relationships.

### Documentation

Contextor MCP exposes its own MCP documentation so agents can discover tool purpose, parameters, freshness requirements, representations, and failure contracts without relying on README documentation alone.

---

## Bounded and Indexed Responses

Large repositories can produce more architectural data than should be placed directly into an LLM context window.

Contextor MCP therefore supports bounded responses and, where appropriate, indexed representations using persistent identities.

Large result sets can use progressive disclosure instead of forcing the complete payload into a single answer.

The objective is not merely smaller JSON.

It is to deliver **the smallest context that preserves the information needed for the current reasoning step.**

---

## Full Analysis and Warm Iterations

A repository needs one complete analysis before Contextor MCP can safely provide the full canonical model.

The initial analysis establishes identities and repository-wide analysis families.

After that, LIVE and incremental workflows can reuse canonical state for supported changes.

Layer and single-file analysis can therefore operate against existing canonical repository state rather than rebuilding the entire repository every time.

A full rebuild remains the correctness fallback when required state is:

- missing;
- stale;
- incomplete;
- incompatible;
- associated with another repository identity;
- invalidated by scope or exclusion changes.

---

## Static Analysis and Dynamic Python

Contextor MCP does not execute the analyzed repository.

Analysis is based on deterministic static evidence such as:

- Python AST;
- symbol extraction;
- import relationships;
- source-level references;
- canonical identities;
- interface descriptors;
- materialized semantic facts.

Dynamic Python behavior cannot always be resolved exactly.

Examples include:

- runtime dependency injection;
- dynamic imports;
- `getattr`;
- monkey patching;
- framework-generated behavior;
- runtime registration;
- reflection.

Contextor MCP does not fabricate certainty in these cases.

Where exact semantic resolution is unavailable, the model can retain explicit symbolic or dynamic boundaries instead.

---

## What Contextor MCP Does Not Do

Contextor MCP is not:

- a version-control system;
- a replacement for Git;
- a code formatter;
- an autonomous code-writing engine;
- a runtime profiler;
- a debugger;
- a full Python type checker;
- a security vulnerability scanner;
- a substitute for executing tests.

It provides architectural and semantic intelligence to developers and AI coding agents.

The developer or agent still performs the actual code modification and validation.

---

## GUI, CLI and MCP

Contextor MCP can be used through:

- the graphical desktop interface;
- the command-line interface;
- the MCP server.

### GUI

From a source checkout:

~~~bash
python main.py --gui
~~~

Or:

~~~bash
python -m contextor --gui
~~~

On Windows the bundled launcher can also be used:

~~~bash
run_contextor.bat
~~~

### CLI

Analyze a repository:

~~~bash
contextor /path/to/project
~~~

Examples:

~~~bash
contextor PROJECT --layer PROJECT/core
contextor PROJECT --file PROJECT/module.py
contextor PROJECT --output ./reports
contextor PROJECT --quiet
~~~

### MCP Server

The package exposes:

~~~bash
contextor-mcp
~~~

Configure this command as an MCP server in a compatible client.

MCP analysis operations are non-blocking where appropriate and expose job/status information rather than forcing long repository analyses into one synchronous request.

---

## Installation

### Requirements

- Python 3.10 or newer
- Git for Git-aware repository context
- Tkinter when using the desktop GUI

Runtime dependencies are installed from the package configuration and include the MCP and LIVE components required by Contextor MCP.

For development:

~~~bash
pip install -e ".[dev]"
~~~

For a normal editable installation:

~~~bash
pip install -e .
~~~

The Windows launcher can create and manage an isolated virtual environment for desktop use.

---

## Files and Repository Safety

Contextor MCP does not execute or modify the source code of the repository being analyzed as part of analysis.

Generated reports, persistent identities, caches, configuration, LIVE metadata, and recovery state are maintained separately from analyzed source according to the configured Contextor storage locations.

Persistent repository identity prevents state from unrelated repository roots from being silently mixed.

---

## Generated Reports

Although MCP queries can work directly from canonical state, Contextor MCP can also generate persistent architectural reports.

These include information such as:

- repository architecture;
- dependencies;
- symbol ownership;
- artifact consumption;
- graph analytics;
- cycles;
- hotspots;
- technical-debt indicators;
- layer analysis;
- single-file context;
- Git-aware architectural comparisons.

Stable canonical report names can coexist with timestamped historical snapshots.

Reports are useful for inspection and historical comparison, but the MCP query layer is not limited to reading static report files.

---

## Design Principles

Contextor MCP follows several core principles:

**Canonical state over query-time reconstruction**  
Architectural facts that can remain current should be maintained as repository state rather than repeatedly reconstructed for every LLM request.

**Persistent identity over fragile text matching**  
Modules and artifacts should remain identifiable across repository evolution.

**Progressive disclosure over context dumping**  
Return only the information required for the current reasoning step.

**Fail closed over fabricated certainty**  
Stale, incomplete, ambiguous, or unavailable evidence must remain explicit.

**Static evidence over runtime guessing**  
Dynamic boundaries are represented honestly rather than resolved speculatively.

**Architecture before text search**  
Use structural knowledge to locate the correct code; use source search for exact textual verification.

---

## License

Contextor MCP is distributed under the:

**Contextor Community License v1.0**

The software is source-available under a non-commercial license.

It may be used, modified, and distributed for:

- personal use;
- educational purposes;
- academic research;
- scientific research;
- non-commercial research;
- hobby projects;
- evaluation and testing.

Commercial use, including use by commercial organizations or integration into commercial products and services, requires a separate commercial license.

This is **not an OSI-approved Open Source license**.

See `LICENSE` for the complete terms.

---

## Disclaimer

Contextor MCP is provided “as is”, without warranty of any kind.

Static architectural analysis has inherent limits, particularly in highly dynamic Python systems.

Architectural information produced by Contextor MCP should therefore be treated as engineering evidence rather than a substitute for tests, runtime observation, or developer review.

---

## Contact

For commercial licensing or other inquiries:

[wojciech.jarka77@gmail.com](mailto:wojciech.jarka77@gmail.com)