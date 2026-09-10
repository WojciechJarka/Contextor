from __future__ import annotations

import ast

from contextor.core.analysis.lineage_extraction_emit import emit_surface
from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
from contextor.core.domain.lineage_facts import (
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    LineageConfidence,
    ResolutionKind,
    SurfaceDeclarationEvidence,
    SurfaceKind,
)


def _literal_all_items(node: ast.Assign) -> tuple[tuple[str, ast.Constant], ...] | None:
    if not isinstance(node.value, (ast.List, ast.Tuple)):
        return None
    items: list[tuple[str, ast.Constant]] = []
    for item in node.value.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str) or not item.value:
            return None
        items.append((item.value, item))
    return tuple(items)


def observe_all_assignment(state: LineageExtractionState, node: ast.Assign, binding) -> None:
    if not state.is_direct_module_statement(node):
        state.invalidate_all()
        return
    items = _literal_all_items(node)
    if items is None:
        state.invalidate_all()
        return
    state.record_all_exact(binding, items)


def observe_all_augassign(state: LineageExtractionState) -> None:
    state.invalidate_all()


def observe_all_delete(state: LineageExtractionState) -> None:
    state.invalidate_all()


def observe_all_mutation(state: LineageExtractionState, node: ast.Call) -> None:
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "__all__":
        state.invalidate_all()


def record_direct_public_candidates(state: LineageExtractionState, node: ast.AST, owner: str) -> None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        names = (node.name,)
    elif isinstance(node, ast.Assign):
        names = tuple(target.id for target in node.targets if isinstance(target, ast.Name) and target.id != "__all__")
    else:
        return
    frame = state.frame(owner)
    for name in names:
        binding = frame.get(name)
        if binding is not None:
            state.record_module_public_candidate(name, binding, node)


def finalize_surfaces(state: LineageExtractionState, paths: dict[int, str], module_name: str, module_owner: str) -> None:
    if state._all_status == "exact" and state._all_binding == state.current_module_surface_binding(module_owner, "__all__"):
        seen: set[str] = set()
        for ordinal, (name, item) in enumerate(state._all_items):
            if name in seen:
                continue
            seen.add(name)
            current = state.current_module_surface_binding(module_owner, name)
            candidate = state._module_public_candidates.get(name)
            imported = state.import_frame(module_owner).get(name)
            if candidate is not None and candidate[0] == current:
                emit_surface(state, paths, kind=SurfaceKind.EXPORT, exposed=current, node=item, declared_name=name, resolution_kind=ResolutionKind.LITERAL_CONTAINER_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ordinal=ordinal)
            elif current is not None and imported is not None and imported.symbol_name is not None and imported.binding_id == current.local_id:
                emit_surface(state, paths, kind=SurfaceKind.REEXPORT, exposed=current, node=item, declared_name=name, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION, ordinal=ordinal)
            else:
                emit_surface(state, paths, kind=SurfaceKind.EXPORT, exposed=ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, module_name, name), node=item, declared_name=name, resolution_kind=ResolutionKind.UNRESOLVED_NAME, confidence=LineageConfidence.UNRESOLVED, declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ordinal=ordinal)
        return
    if state._all_status != "absent":
        return
    for ordinal, (name, (binding, node)) in enumerate(sorted(state._module_public_candidates.items())):
        if name and not name.startswith("_") and state.current_module_surface_binding(module_owner, name) == binding:
            emit_surface(state, paths, kind=SurfaceKind.PUBLIC_SYMBOL, exposed=binding, node=node, declared_name=name, resolution_kind=ResolutionKind.PYTHON_NAME_CONVENTION, confidence=LineageConfidence.INFERRED, declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION, ordinal=ordinal)
