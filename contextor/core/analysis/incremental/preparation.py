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
    new_collision_facts: Optional[List[Dict[str, Any]]] = None
    collision_facts_changed: bool = False
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


def _collision_facts_differ(
    old_facts: Optional[List[Dict[str, Any]]],
    new_facts: Optional[List[Dict[str, Any]]],
) -> bool:
    """
    Semantic comparison between old hydrated collision facts and fresh extracted collision facts.
    Compares structural identity fields (name, type, file, file_path, line/col numbers) first.
    If the old hydrated fact has code == "", does not materialize fresh CollisionFact code:
    structurally identical unique facts are unchanged.
    If the old fact has non-empty code (pre-existing collision candidate), materializes and compares code.
    """
    if old_facts is None or new_facts is None:
        return old_facts != new_facts
    if len(old_facts) != len(new_facts):
        return True

    structural_fields = (
        "name",
        "type",
        "file",
        "file_path",
        "line_start",
        "line_end",
        "col_start",
        "col_end",
    )
    for old_f, new_f in zip(old_facts, new_facts):
        for field in structural_fields:
            if old_f.get(field) != new_f.get(field):
                return True

        old_code = old_f.get("code")
        if old_code:
            new_code = new_f.get("code") if isinstance(new_f, dict) else getattr(new_f, "code", "")
            if old_code != new_code:
                return True

    return False


def prepare_source_update(
    file_path: str | Path,
    module_path: str,
    is_new: bool,
    old_module: Optional[Any],
    old_artifacts: Optional[Dict[str, Any]],
    old_usage: Optional[ModuleUsageFacts],
    persistent_id: Optional[str] = None,
    old_collision_facts: Optional[List[Dict[str, Any]]] = None,
) -> PreparedSourceUpdate:
    """
    Parses and extracts all necessary facts from a changed/added source file,
    computes structural FileDelta, behavioral UsageDelta, and collision facts without mutating canonical state.
    """
    path = Path(file_path)

    # 1. Syntax validation and source reading
    try:
        source_text = path.read_text(encoding="utf-8")
        parsed_tree = ast.parse(source_text, filename=str(path))
    except SyntaxError as exc:
        return PreparedSourceUpdate(
            module_path=module_path,
            is_new=is_new,
            new_imports=[],
            new_artifacts={},
            new_usage=None,
            delta=FileDelta(module_path=module_path, is_new=is_new),
            usage_delta=None,
            new_collision_facts=None,
            collision_facts_changed=True if old_collision_facts is not None else False,
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
            new_collision_facts=None,
            collision_facts_changed=True if old_collision_facts is not None else False,
            error_status="ERROR",
            error_message=str(exc),
        )

    # 2. Extract imports
    try:
        from contextor.core.symbol_engine.indexer import read_imports
        new_imports, error = read_imports(path, tree=parsed_tree)
        if error:
            return PreparedSourceUpdate(
                module_path=module_path,
                is_new=is_new,
                new_imports=[],
                new_artifacts={},
                new_usage=None,
                delta=FileDelta(module_path=module_path, is_new=is_new),
                usage_delta=None,
                new_collision_facts=None,
                collision_facts_changed=True if old_collision_facts is not None else False,
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
            new_collision_facts=None,
            collision_facts_changed=True if old_collision_facts is not None else False,
            error_status="ERROR",
            error_message=str(exc),
        )

    # 3. Extract symbols & artifacts
    try:
        from contextor.core.reporting_layer.artifact_usage_report import (
            extract_file_symbols,
            _module_own_symbols,
        )
        raw_symbols = extract_file_symbols(str(path), tree=parsed_tree)
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

    # 4. Extract collision facts
    from contextor.core.validator.collisions import extract_module_collision_facts
    new_collision_facts = extract_module_collision_facts(
        parsed_tree,
        module_path,
        str(path.resolve()),
    )
    if old_collision_facts is None:
        collision_facts_changed = True
    else:
        collision_facts_changed = _collision_facts_differ(old_collision_facts, new_collision_facts)

    # 5. Calculate FileDelta
    delta = calculate_file_delta(
        module_path=module_path,
        persistent_id=persistent_id,
        is_new=is_new,
        old_module=old_module,
        old_artifacts=old_artifacts,
        new_imports=new_imports,
        new_artifacts_dict=new_artifacts,
    )

    # 6. Extract Usage facts & UsageDelta
    from contextor.core.reference.engine import extract_module_usage_facts
    new_usage = extract_module_usage_facts(
        module_path,
        parsed_tree,
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
        new_collision_facts=new_collision_facts,
        collision_facts_changed=collision_facts_changed,
    )


def prepare_deleted_module_update(
    module_path: str,
    old_module: Optional[Any],
    old_artifacts: Optional[Dict[str, Any]],
    old_usage: Optional[ModuleUsageFacts],
    old_collision_facts: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[FileDelta, Any, bool]:
    """Prepares FileDelta, UsageDelta, and collision facts invalidation for a deleted module."""
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
    collision_facts_changed = bool(old_collision_facts) if old_collision_facts is not None else True
    return delta, usage_delta, collision_facts_changed
