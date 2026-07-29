# Reposter

Reposter is an advanced static analysis and context extraction tool designed to analyze Python repositories. It acts as a bridge between complex codebases and Large Language Models (LLMs) or developers, building a comprehensive understanding of the project's architecture, dependencies, and technical debt without ever executing the code.

## What Reposter Does
- **Dependency Graph Building:** Extracts module dependencies (both hard imports and soft textual references) to construct a complete project architecture graph.
- **Architectural Debt Calculation:** Heuristically calculates technical debt by detecting circular dependencies, isolated modules, namespace collisions, and architectural hotspots.
- **Artifact Consumption Tracking:** Analyzes which symbols (classes, functions, methods) are actively used across the project and how they are consumed (e.g., direct calls, API imports, reflection, CLI/API exposure).
- **Context Generation:** Generates highly structured, 100% context-rich JSON and Markdown reports tailored for LLMs to understand the architecture, intent, and blast radius of any file or architectural layer.
- **Single-File Deep Dives:** Provides granular insights into individual files, including their semantic intent, exports, and relationships with the rest of the project.

## What Reposter Does NOT Do
- **Dynamic Analysis:** It does not execute your code. All analysis is purely static and safe.
- **Deep Runtime Type-Inference:** It relies heavily on AST parsing and exact symbol name matching rather than executing complex generic inference or runtime type checking.
- **Automated Code Modification:** It will not rewrite your code, fix bugs, or format files. It is strictly an observability and reporting tool.
- **Security Audits:** While it detects structural risks and technical debt, it is not a dedicated SAST tool for discovering security vulnerabilities.

## Prerequisites
- Python 3.9+ (or newer)
- **Git Context:** The module `core/analysis/git_context.py` requires `git` to be installed and available in your system's `PATH`.

## How to Use

Reposter offers both a Command-Line Interface (CLI) and a Graphical User Interface (GUI).

### Using the GUI
The most convenient way to interact with Reposter is through its GUI.
1. Run the interface:
   ```bash
   python ui/gui.py
   ```
2. Select your target project directory.
3. Manage exclusion rules for directories or specific files.
4. Generate comprehensive LLM context reports or inspect architectural layers directly in the UI.

### Using the CLI
To run an automated analysis from the terminal:
```bash
python cli.py /path/to/your/project
```
The CLI will build the index, detect cycles, calculate debt, and save the JSON/Markdown reports into the `output/` directory.

## License
This project is distributed under the **Reposter Community License v1.0**. 

**Note:** This is a "source-available" license with a strict non-commercial restriction, not an OSI-approved "Open Source" license. You are free to use, modify, and distribute this software for personal, educational, and non-commercial research purposes. Any commercial use (including internal use by commercial entities) requires a separate commercial license. For the exact terms, please see the `LICENSE` file.

## Disclaimer
**No Warranty / Liability:** This software is provided "as is", without warranty of any kind, express or implied. The author(s) are not responsible for any consequences, data loss, or damages resulting from the use of this tool. Always review generated reports and double-check architectural recommendations before making sweeping changes to your codebase.

## Contact
For commercial licensing or other inquiries, please contact: [wojciech.jarka77@gmail.com](mailto:wojciech.jarka77@gmail.com)
