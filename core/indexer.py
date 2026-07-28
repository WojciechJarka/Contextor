"""
core/indexer.py

AST → RAW IMPORTS with depth-scope support.

Differentiates between:
- global imports
- local imports (inside functions/closures)

Builds stable module_id against project root.
"""


import ast

from pathlib import Path


from repo_guardian.core.domain.module import (
    Module,
)

from repo_guardian.core.domain.imports import (
    ImportRef,
)



# ==========================================================
# IMPORT EXTRACTION
# ==========================================================


class AdvancedImportVisitor(
    ast.NodeVisitor
):
    """
    Przechodzi AST zachowując informację
    o głębokości funkcji.

    Pozwala rozróżnić:

    import x

    oraz:

    def f():
        import x
    """



    def __init__(self):

        self.found_imports: list[ImportRef] = []

        self._in_function_depth = 0



    def visit_FunctionDef(
        self,
        node
    ):

        self._in_function_depth += 1

        self.generic_visit(
            node
        )

        self._in_function_depth -= 1



    def visit_AsyncFunctionDef(
        self,
        node
    ):

        self.visit_FunctionDef(
            node
        )



    def visit_Import(
        self,
        node
    ):

        is_local = (
            self._in_function_depth > 0
        )


        for item in node.names:


            self.found_imports.append(

                ImportRef(

                    module=item.name,

                    level=0,

                    names=[],

                    is_from_import=False,

                    is_local=is_local,

                )

            )



    def visit_ImportFrom(
        self,
        node
    ):

        is_local = (
            self._in_function_depth > 0
        )


        names = [

            item.name

            for item in node.names

        ]



        self.found_imports.append(

            ImportRef(

                module=node.module,

                level=node.level or 0,

                names=names,

                is_from_import=True,

                is_local=is_local,

            )

        )



def extract_imports(
    file_path: Path
) -> list[ImportRef]:
    """
    Ekstrakcja surowych importów AST.
    """

    try:

        source = file_path.read_text(
            encoding="utf-8"
        )


        tree = ast.parse(
            source
        )


    except Exception:

        return []



    visitor = AdvancedImportVisitor()


    visitor.visit(
        tree
    )


    return visitor.found_imports



# ==========================================================
# INDEX BUILDER
# ==========================================================


def build_index(
    root: str,
    excludes: list[str] = None
) -> dict[str, Module]:
    """
    Buduje indeks modułów projektu.

    Klucz:
        module_id

    Wartość:
        Module
    """



    root_path = Path(
        root
    ).resolve()

    if not root_path.exists():

        raise ValueError(

            f"Repository root does not exist: {root_path}"

        )



    if not root_path.is_dir():

        raise ValueError(

            f"Repository root is not directory: {root_path}"

        )



    modules: dict[str, Module] = {}



    ignored_dirs = {

        "venv",

        ".venv",

        "python",

        "Python",

        "__pycache__",

        ".git",

        ".tox",

        ".pytest_cache",

        "node_modules",

    }



    for path in root_path.rglob(
        "*.py"
    ):



        rel = path.relative_to(
            root_path
        )



        # ignorowanie katalogów
        # względem repo root

        if any(
            part in ignored_dirs
            for part in rel.parts
        ):
            continue

        if excludes:
            rel_str = rel.as_posix()
            is_excluded = False
            for ex in excludes:
                ex_norm = ex.replace("\\", "/")
                if rel_str == ex_norm or rel_str.startswith(ex_norm + "/"):
                    is_excluded = True
                    break
            if is_excluded:
                continue



        module_id = ".".join(

            rel.with_suffix("").parts

        )



        imports = extract_imports(
            path
        )



        modules[module_id] = Module(

            module_id=module_id,

            path=str(path.resolve()),

            absolute_path=str(
                path.resolve()
            ),

            imports=imports,

        )


    return modules
