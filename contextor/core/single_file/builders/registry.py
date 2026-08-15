import ast
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from contextor.core.program_log import log_program_event

@dataclass(frozen=True)
class ContextPayload:
    file_path: str
    module_id: str
    modules: dict
    root_path: str
    module: Any
    tree: ast.AST
    source: str
    project_graph: Any
    global_report: dict | None = None

class BuildState:
    def __init__(self):
        self._data: dict[str, Any] = {}
        
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
        
    def keys(self) -> set[str]:
        return set(self._data.keys())
        
    def __getitem__(self, key: str) -> Any:
        return self._data[key]
        
    def update(self, result: dict[str, Any]) -> None:
        self._data.update(result)
        
    def to_dict(self) -> dict[str, Any]:
        return self._data.copy()

@runtime_checkable
class ContextBuilder(Protocol):
    name: str
    requires: set[str]
    provides: set[str]
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        ...

class BuilderRegistry:
    def __init__(self):
        self._builders: list[ContextBuilder] = []
        
    def register(self, builder: ContextBuilder) -> None:
        self._builders.append(builder)
        
    def build_all(self, payload: ContextPayload, progress_callback=None) -> dict[str, Any]:
        from contextor.core.errors import checkpoint

        # Validate providers
        all_provided = set()
        for b in self._builders:
            intersect = all_provided.intersection(b.provides)
            if intersect:
                raise RuntimeError(f"Duplicate providers for {intersect} (Conflict with {b.name})")
            all_provided.update(b.provides)
            
        # Topological Sort
        sorted_builders = []
        visited = set()
        temp_mark = set()
        
        def visit(builder):
            if builder.name in temp_mark:
                raise RuntimeError("Dependency cycle detected!")
            if builder.name in visited:
                return
                
            temp_mark.add(builder.name)
            
            # Find dependencies
            for req in builder.requires:
                # Find the builder that provides this requirement
                provider = next((b for b in self._builders if req in b.provides), None)
                if not provider:
                    # Some requirements might not be provided by builders if they are optional or not found
                    # In a strict DAG, if a requirement is missing from all providers, it's a fatal error
                    raise RuntimeError(f"Missing dependency '{req}' required by '{builder.name}'")
                visit(provider)
                
            temp_mark.remove(builder.name)
            visited.add(builder.name)
            sorted_builders.append(builder)
            
        for b in self._builders:
            if b.name not in visited:
                visit(b)
                
        # Execution
        state = BuildState()
        for completed, b in enumerate(sorted_builders):
            checkpoint(
                progress_callback,
                f"Single-file context builder: {b.name}",
                completed,
                len(sorted_builders),
            )
            missing = b.requires - state.keys()
            if missing:
                raise RuntimeError(f"[{b.name}] Runtime dependency error. Missing: {missing}")
                
            log_program_event("BUILDER", "start", name=b.name)
            result = b.build(payload, state)
            
            # Validate output matches provides
            produced_keys = set(result.keys())
            if produced_keys != b.provides:
                unexpected = produced_keys - b.provides
                missing_provided = b.provides - produced_keys
                raise RuntimeError(f"[{b.name}] Contract violation. Unexpected: {unexpected}. Missing: {missing_provided}")
                
            state.update(result)
            log_program_event(
                "BUILDER", "complete", name=b.name, outputs=len(result)
            )
            
        return state.to_dict()
