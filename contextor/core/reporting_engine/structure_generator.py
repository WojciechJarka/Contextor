def generate_structure_report(hard_edges: dict, soft_edges: dict) -> dict:
    return {
        "hard_edges": {k: sorted(set(v)) for k, v in sorted(hard_edges.items())},
        "soft_edges": {k: sorted(set(v)) for k, v in sorted(soft_edges.items())},
    }
