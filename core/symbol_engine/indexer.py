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
from repo_guardian.core.analysis.cache_manager import CacheManager
import dataclasses
from concurrent.futures import ProcessPoolExecutor, as_completed



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



def _process_single_file(path_str: str, root_str: str) -> dict:
    """Funkcja pomocnicza dla wieloprocesowości."""
    path = Path(path_str)
    
    # Próba odczytu z cache
    cache = CacheManager(root_str)
    cached_data = cache.get(path)
    
    if cached_data:
        imports = [ImportRef(**imp) for imp in cached_data.get("imports", [])]
    else:
        imports = extract_imports(path)
        cache.set(path, {"imports": [dataclasses.asdict(imp) for imp in imports]})
        
    rel = path.relative_to(Path(root_str))
    module_id = ".".join(rel.with_suffix("").parts)
    
    return {
        "module_id": module_id,
        "path": str(path.resolve()),
        "imports": imports,
        "filename": path.name
    }


# ==========================================================
# INDEX BUILDER
# ==========================================================


def build_index(
    root: str,
    excludes: list[str] = None,
    extra_ignored_dirs: set = None,
    progress_callback = None
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

    if extra_ignored_dirs:
        ignored_dirs.update(extra_ignored_dirs)



    files_to_process = []
    for path in root_path.rglob("*.py"):
        rel = path.relative_to(root_path)
        if any(part in ignored_dirs for part in rel.parts):
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
        files_to_process.append(path)

    total_files = len(files_to_process)
    if progress_callback:
        progress_callback(0, total_files, "Start...")

    completed = 0
    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(_process_single_file, str(p), str(root_path)): p
            for p in files_to_process
        }
        
        for future in as_completed(futures):
            res = future.result()
            modules[res["module_id"]] = Module(
                module_id=res["module_id"],
                path=res["path"],
                absolute_path=res["path"],
                imports=res["imports"],
            )
            
            completed += 1
            if progress_callback:
                if not progress_callback(completed, total_files, res["filename"]):
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise Exception("Analysis cancelled by user")

    return modules
