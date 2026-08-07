"""
contextor/core/domain/graph.py

Dependency graph model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectGraph:
    """
    Gotowy graf zależności.
    """

    hard_edges: dict[str, set[str]]

    soft_edges: dict[str, set[str]]

    def with_module_edges(self, module_id: str, new_hard: set[str], new_soft: set[str]) -> "ProjectGraph":
        """
        Returns a new ProjectGraph with replaced outgoing edges for the given module_id.
        """
        new_hard_edges = {k: set(v) for k, v in self.hard_edges.items()}
        new_soft_edges = {k: set(v) for k, v in self.soft_edges.items()}
        
        new_hard_edges[module_id] = new_hard
        new_soft_edges[module_id] = new_soft
        
        return ProjectGraph(
            hard_edges={key: value for key, value in sorted(new_hard_edges.items())},
            soft_edges={key: value for key, value in sorted(new_soft_edges.items())}
        )

    def without_module(self, module_id: str) -> "ProjectGraph":
        """
        Returns a new ProjectGraph with the given module_id removed from both keys and values.
        """
        new_hard_edges = {}
        for k, v in self.hard_edges.items():
            if k == module_id:
                continue
            new_hard_edges[k] = {target for target in v if target != module_id}
            
        new_soft_edges = {}
        for k, v in self.soft_edges.items():
            if k == module_id:
                continue
            new_soft_edges[k] = {target for target in v if target != module_id}
            
        return ProjectGraph(
            hard_edges={key: value for key, value in sorted(new_hard_edges.items())},
            soft_edges={key: value for key, value in sorted(new_soft_edges.items())}
        )
