"""Conservative AST guard evidence for explicit import occurrences.

Only literal boolean conditions can block a branch here. Named guards are
recognition candidates, never verified runtime values or safety proofs.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .provenance import ImportProvenance, extract_import_provenance


@dataclass(frozen=True)
class GuardFrameEvidence:
    kind: str
    branch: str
    line: int
    predicate_kind: str
    predicate_truth: str
    branch_gate: str


@dataclass(frozen=True)
class ImportGuardAssessment:
    ordinal: int
    line: int
    gate: str
    frames: tuple[GuardFrameEvidence, ...]
    initialization_reachability: str = "UNKNOWN"


@dataclass(frozen=True)
class GuardProjection:
    module_id: str
    source_fingerprint: str
    assessments: tuple[ImportGuardAssessment, ...]


def _literal_truth(node: ast.AST) -> bool | None:
    if isinstance(node, ast.Constant) and type(node.value) is bool:
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        inner = _literal_truth(node.operand)
        return None if inner is None else not inner
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        values = [_literal_truth(child) for child in node.values]
        if any(value is None for value in values):
            return None
        return all(values) if isinstance(node.op, ast.And) else any(values)
    return None


def _binding_occurrences(tree: ast.Module) -> dict[str, list[ast.AST]]:
    """Gather potential lexical writes, conservatively across all scopes."""
    owners: dict[str, list[ast.AST]] = {}

    def add(name: str, node: ast.AST) -> None:
        owners.setdefault(name, []).append(node)

    class Visitor(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import) -> None:
            for item in node.names:
                add(item.asname or item.name.split(".")[0], node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for item in node.names:
                if item.name != "*":
                    add(item.asname or item.name, node)

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                add(node.id, node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            add(node.name, node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            add(node.name, node)
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            add(node.name, node)
            self.generic_visit(node)

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name:
                add(node.name, node)
            self.generic_visit(node)

        def visit_arg(self, node: ast.arg) -> None:
            add(node.arg, node)
            self.generic_visit(node)

    Visitor().visit(tree)
    return owners


def _known_typing_aliases(
    tree: ast.Module,
    before_line: int,
    bindings: dict[str, list[ast.AST]],
) -> tuple[set[str], set[str]]:
    """Identify unshadowed top-level syntactic origins only, not runtime truth."""
    module_names: set[str] = set()
    constant_names: set[str] = set()
    for statement in tree.body:
        if getattr(statement, "lineno", 0) >= before_line:
            continue
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                bound = alias.asname or alias.name.split(".")[0]
                if alias.name == "typing" and bindings.get(bound) == [statement]:
                    module_names.add(bound)
        elif isinstance(statement, ast.ImportFrom):
            if statement.level != 0 or statement.module != "typing":
                continue
            for alias in statement.names:
                bound = alias.asname or alias.name
                if alias.name == "TYPE_CHECKING" and bindings.get(bound) == [statement]:
                    constant_names.add(bound)
    return module_names, constant_names


def _is_main_pattern(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    if not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
        return False
    left, right = node.left, node.comparators[0]
    return (
        isinstance(left, ast.Name) and left.id == "__name__"
        and isinstance(right, ast.Constant) and right.value == "__main__"
    ) or (
        isinstance(right, ast.Name) and right.id == "__name__"
        and isinstance(left, ast.Constant) and left.value == "__main__"
    )


def _predicate_evidence(
    node: ast.AST,
    tree: ast.Module,
    bindings: dict[str, list[ast.AST]],
    before_line: int,
) -> tuple[str, str]:
    truth = _literal_truth(node)
    if truth is not None:
        return "LITERAL_BOOLEAN", "TRUE" if truth else "FALSE"
    if _is_main_pattern(node):
        return "MAIN_GUARD_CANDIDATE", "UNKNOWN"
    modules, names = _known_typing_aliases(tree, before_line, bindings)
    if isinstance(node, ast.Name) and node.id in names:
        return "TYPE_CHECKING_CANDIDATE", "UNKNOWN"
    if (
        isinstance(node, ast.Attribute)
        and node.attr == "TYPE_CHECKING"
        and isinstance(node.value, ast.Name)
        and node.value.id in modules
    ):
        return "TYPE_CHECKING_CANDIDATE", "UNKNOWN"
    return "UNKNOWN_EXPRESSION", "UNKNOWN"


def project_import_guards(
    tree: ast.AST,
    provenance: ImportProvenance,
) -> GuardProjection:
    """Map each lexical import to guard evidence; never certify cycle safety."""
    if not isinstance(tree, ast.Module):
        raise TypeError("tree must be an ast.Module")
    if not isinstance(provenance, ImportProvenance):
        raise TypeError("provenance must be ImportProvenance")

    replay = extract_import_provenance(
        tree,
        module_id=provenance.module_id,
        source_key=provenance.source_key,
        source_path=provenance.source_path,
        source_fingerprint=provenance.source_fingerprint,
    )
    if replay != provenance:
        raise ValueError("AST import occurrences differ from provenance")

    # Multiple matching If statements are treated as ambiguous, not guessed.
    lookup: dict[tuple[int, str], list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            lookup.setdefault(
                (node.lineno, ast.dump(node.test, include_attributes=False)), []
            ).append(node.test)

    bindings = _binding_occurrences(tree)
    assessments: list[ImportGuardAssessment] = []
    for occurrence in provenance.occurrences:
        frame_evidence: list[GuardFrameEvidence] = []
        for frame in occurrence.controls:
            if frame.kind != "IF":
                predicate_kind, truth = "NON_IF_CONTROL", "UNKNOWN"
            else:
                matches = lookup.get((frame.line, frame.expression or ""), [])
                if len(matches) != 1:
                    predicate_kind, truth = "UNRESOLVED_IF", "UNKNOWN"
                else:
                    predicate_kind, truth = _predicate_evidence(
                        matches[0], tree, bindings, frame.line
                    )
            if truth == "UNKNOWN":
                gate = "UNKNOWN"
            else:
                taken = (truth == "TRUE") == (frame.branch == "BODY")
                gate = "POSSIBLE" if taken else "BLOCKED"
            frame_evidence.append(
                GuardFrameEvidence(
                    kind=frame.kind,
                    branch=frame.branch,
                    line=frame.line,
                    predicate_kind=predicate_kind,
                    predicate_truth=truth,
                    branch_gate=gate,
                )
            )

        if any(frame.branch_gate == "BLOCKED" for frame in frame_evidence):
            overall = "BLOCKED_BY_LITERAL"
        elif any(frame.branch_gate == "UNKNOWN" for frame in frame_evidence):
            overall = "GUARDED_UNKNOWN"
        else:
            overall = "NO_KNOWN_GUARD_BLOCKER"
        assessments.append(
            ImportGuardAssessment(
                ordinal=occurrence.ordinal,
                line=occurrence.line,
                gate=overall,
                frames=tuple(frame_evidence),
            )
        )

    return GuardProjection(
        module_id=provenance.module_id,
        source_fingerprint=provenance.source_fingerprint,
        assessments=tuple(assessments),
    )
