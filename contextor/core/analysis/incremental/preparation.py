"""
contextor/core/analysis/incremental/preparation.py

Source preparation and semantic delta construction for incremental updates:
- Syntax validation and safe source reading
- Import and symbol artifact extraction
- Pure FileDelta and UsageDelta computation
- PreparedModuleUpdate contract
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Set, Dict, Any, Tuple

from contextor.core.analysis.state_manager import FileDelta
from contextor.core.domain.usage_facts import ModuleUsageFacts, diff_usage_facts



@dataclass(frozen=True)
class PreparedSourceUpdate:
    """Represents the complete extracted facts and deltas from a changed or added source file."""
    module_path: str
    is_new: bool
    new_imports: List[Any]
    new_artifacts: Dict[str, Any]
    new_usage: Optional[ModuleUsageFacts]
    delta: FileDelta
    usage_delta: Optional[Any]
    error_status: Optional[str] = None
    error_message: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None

    @property
    def has_error(self) -> bool:
        return self.error_status is not None


def extract_artifact_names(artifacts: Optional[Dict[str, Any]]) -> Set[str]:
    """Return definition artifacts represented in one module snapshot."""
    symbols = artifacts.get("symbols", {}) if artifacts else {}
    return {
        str(name)
        for category in ("functions", "classes", "methods")
        for name in symbols.get(category, [])
    }


def calculate_file_delta(
    module_path: str,
    persistent_id: Optional[str],
    is_new: bool,
    old_module: Optional[Any],
    old_artifacts: Optional[Dict[str, Any]],
    new_imports: Optional[List[Any]],
    new_artifacts_dict: Dict[str, Any],
) -> FileDelta:
    """
    Calculates exact FileDelta (structural changes: added/removed imports and definitions)
    between existing canonical state and candidate update.
    """
    delta = FileDelta(module_path=module_path, is_new=is_new)

    if is_new or persistent_id is None or old_module is None:
        delta.is_new = True
        delta.imports_added = sorted(
            {imp.module for imp in (new_imports or []) if imp.module}
        )
        delta.artifacts_added = sorted(extract_artifact_names(new_artifacts_dict))
        return delta

    old_imports = old_module.imports if old_module else []
    old_import_names = {imp.module for imp in old_imports if imp.module}
    new_import_names = {imp.module for imp in (new_imports or []) if imp.module}

    delta.imports_added = sorted(new_import_names - old_import_names)
    delta.imports_removed = sorted(old_import_names - new_import_names)

    new_artifact_names = extract_artifact_names(new_artifacts_dict)
    old_artifact_names = extract_artifact_names(old_artifacts or {})

    delta.artifacts_added = sorted(new_artifact_names - old_artifact_names)
    delta.artifacts_removed = sorted(old_artifact_names - new_artifact_names)

    return delta


def prepare_source_update(
    file_path: str | Path,
    module_path: str,
    is_new: bool,
    old_module: Optional[Any],
    old_artifacts: Optional[Dict[str, Any]],
    old_usage: Optional[ModuleUsageFacts],
    persistent_id: Optional[str] = None,
) -> PreparedSourceUpdate:
    """
    Parses and extracts all necessary facts from a changed/added source file,
    computes structural FileDelta and behavioral UsageDelta without mutating canonical state.
    """
    path = Path(file_path)

    # 1. Syntax validation and source reading
    try:
        source_text = path.read_text(encoding="utf-8")
        ast.parse(source_text, filename=str(path))
    except SyntaxError as exc:
        return PreparedSourceUpdate(
            module_path=module_path,
            is_new=is_new,
            new_imports=[],
            new_artifacts={},
            new_usage=None,
            delta=FileDelta(module_path=module_path, is_new=is_new),
            usage_delta=None,
            error_status="SYNTAX_ERROR",
            error_message=exc.msg,
            line_number=exc.lineno,
            column_number=exc.offset,
        )
    except OSError as exc:
        return PreparedSourceUpdate(
            module_path=module_path,
            is_new=is_new,
            new_imports=[],
            new_artifacts={},
            new_usage=None,
            delta=FileDelta(module_path=module_path, is_new=is_new),
            usage_delta=None,
            error_status="ERROR",
            error_message=str(exc),
        )

    # 2. Extract imports
    try:
        from contextor.core.symbol_engine.indexer import read_imports
        new_imports, error = read_imports(path)
        if error:
            return PreparedSourceUpdate(
                module_path=module_path,
                is_new=is_new,
                new_imports=[],
                new_artifacts={},
                new_usage=None,
                delta=FileDelta(module_path=module_path, is_new=is_new),
                usage_delta=None,
                error_status="SYNTAX_ERROR",
                error_message=str(error),
            )
    except Exception as exc:
        return PreparedSourceUpdate(
            module_path=module_path,
            is_new=is_new,
            new_imports=[],
            new_artifacts={},
            new_usage=None,
            delta=FileDelta(module_path=module_path, is_new=is_new),
            usage_delta=None,
            error_status="ERROR",
            error_message=str(exc),
        )

    # 3. Extract symbols & artifacts
    try:
        from contextor.core.reporting_layer.artifact_usage_report import (
            extract_file_symbols,
            _module_own_symbols,
        )
        raw_symbols = extract_file_symbols(str(path))
        own_symbols = _module_own_symbols(raw_symbols)
        old_consumers = (old_artifacts or {}).get("consumers", {})
        new_artifacts = {
            "symbols": raw_symbols,
            "own_symbols": own_symbols,
            "consumers": old_consumers,
        }
    except Exception:
        old_consumers = (old_artifacts or {}).get("consumers", {})
        new_artifacts = {"symbols": {}, "own_symbols": set(), "consumers": old_consumers}

    # 4. Calculate FileDelta
    delta = calculate_file_delta(
        module_path=module_path,
        persistent_id=persistent_id,
        is_new=is_new,
        old_module=old_module,
        old_artifacts=old_artifacts,
        new_imports=new_imports,
        new_artifacts_dict=new_artifacts,
    )

    # 5. Extract Usage facts & UsageDelta
    from contextor.core.reference.engine import extract_module_usage_facts
    new_usage = extract_module_usage_facts(
        module_path,
        source_text,
        imports=new_imports,
    )
    curr_old_usage = old_usage if old_usage is not None else ModuleUsageFacts()
    usage_delta = diff_usage_facts(module_path, curr_old_usage, new_usage)


    return PreparedSourceUpdate(
        module_path=module_path,
        is_new=is_new,
        new_imports=new_imports,
        new_artifacts=new_artifacts,
        new_usage=new_usage,
        delta=delta,
        usage_delta=usage_delta,
    )


def prepare_deleted_module_update(
    module_path: str,
    old_module: Optional[Any],
    old_artifacts: Optional[Dict[str, Any]],
    old_usage: Optional[ModuleUsageFacts],
) -> Tuple[FileDelta, Any]:
    """Prepares FileDelta and UsageDelta for a deleted module (Zero source I/O, Zero AST parse)."""
    delta = FileDelta(
        module_path=module_path,
        is_deleted=True,
        imports_removed=sorted(
            {
                imp.module
                for imp in (old_module.imports if old_module else [])
                if imp.module
            }
        ),
        artifacts_removed=sorted(extract_artifact_names(old_artifacts or {})),
    )
    curr_old_usage = old_usage if old_usage is not None else ModuleUsageFacts()
    usage_delta = diff_usage_facts(module_path, curr_old_usage, ModuleUsageFacts())
    return delta, usage_delta
