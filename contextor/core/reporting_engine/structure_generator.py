def generate_structure_report(hard_edges: dict, soft_edges: dict) -> dict:
    return {
        "hard_edges": {k: sorted(set(v)) for k, v in sorted(hard_edges.items())},
        "soft_edges": {k: sorted(set(v)) for k, v in sorted(soft_edges.items())},
    }

def compact_structure_report(structure_report: dict, index_dict) -> dict:
    """Translates raw module string paths in the structure report to their IndexDictionary IDs."""
    compact = {"hard_edges": {}, "soft_edges": {}}
    
    for edge_type in ["hard_edges", "soft_edges"]:
        for src, targets in structure_report.get(edge_type, {}).items():
            src_id = index_dict.get_module_id(src)
            compact[edge_type][src_id] = sorted([index_dict.get_module_id(t) for t in targets])
            
    return compact
