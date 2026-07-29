# Contextor

Contextor transforms complex Python repositories into structured architectural context that both developers and Large Language Models (LLMs) can understand.

It builds a comprehensive representation of a project's architecture, dependencies, relationships, symbol usage, and technical debt through static analysis — without ever executing the analyzed code.

Contextor acts as an intelligence layer between software repositories and AI systems, providing the architectural awareness required to reason about large and complex codebases.

---

## What Contextor Does

- **Dependency Graph Building:**  
  Extracts module dependencies, including hard imports and soft textual references, to construct a complete architectural graph of the project.

- **Architectural Debt Calculation:**  
  Calculates structural risk indicators by detecting circular dependencies, isolated modules, namespace collisions, dependency hotspots, and architectural inconsistencies.

- **Artifact Consumption Tracking:**  
  Analyzes how symbols (classes, functions, and methods) are defined, consumed, and exposed throughout the repository, including direct calls, API imports, reflection patterns, and CLI/API entry points.

- **Context Generation:**  
  Generates highly structured JSON and Markdown reports designed for Large Language Models (LLMs) and developers, providing architectural understanding, intent, ownership, dependencies, and change impact analysis.

- **Single-File Architectural Deep Dives:**  
  Provides detailed analysis of individual files, including semantic purpose, exported symbols, dependencies, consumers, and relationships with the wider system.

---

## What Contextor Does NOT Do

- **Dynamic Analysis:**  
  Contextor does not execute analyzed code. All analysis is performed through static repository inspection.

- **Deep Runtime Type Inference:**  
  Contextor relies on AST parsing and deterministic symbol analysis rather than runtime execution, dynamic inference, or complex type checking.

- **Automated Code Modification:**  
  Contextor does not rewrite code, fix bugs, or format files. It is designed for architectural visibility, analysis, and decision support.

- **Security Auditing:**  
  Contextor identifies structural risks and technical debt, but it is not a dedicated SAST security vulnerability scanner.

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
- JSON and Markdown reporting
- Single-file architectural analysis

---

# Prerequisites

- Python 3.9+ (or newer)
- Git (optional, required for repository context information)
- Git must be installed and available in your system's `PATH`

---

# Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/Contextor.git
cd Contextor
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

---

# How to Use

Contextor provides both a Command-Line Interface (CLI) and a Graphical User Interface (GUI).

## Using the GUI

The easiest way to start Contextor is:

```bash
python main.py --gui
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
python main.py --cli /path/to/your/project
```

Contextor will:
- build the repository index;
- analyze dependencies;
- resolve symbol relationships;
- detect architectural cycles;
- calculate technical debt indicators;
- generate JSON and Markdown reports.

Generated reports are saved into:

```
output/
```

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
