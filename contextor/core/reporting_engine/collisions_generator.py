from datetime import datetime
from contextor.core.validator.collisions import validate_name_collisions
from .formatting import _collision_severity

def generate_collisions_report(modules: dict, precomputed: list | None = None) -> dict:
    all_collisions = precomputed if precomputed is not None else validate_name_collisions(modules)
    collisions_data = []

    for error in all_collisions:
        severity = getattr(error, "severity", None)
        if severity is None:
            severity = _collision_severity(
                artifact_type=getattr(error, "artifact_type", "unknown"),
                symbol_details=getattr(error, "symbol_details", []),
                code_snippets=getattr(error, "code_snippets", {}),
            )
        collisions_data.append(
            {
                "message": error.message,
                "nodes": error.nodes,
                "artifact_type": getattr(error, "artifact_type", "unknown"),
                "is_identical": getattr(error, "is_identical", False),
                "severity": severity,
                "conflicting_code": getattr(error, "code_snippets", {}),
                "symbol_details": getattr(error, "symbol_details", []),
            }
        )

    identical_count = sum(1 for c in collisions_data if c["is_identical"])
    conflicting_count = len(collisions_data) - identical_count

    severity_counts = {
        "critical": sum(1 for c in collisions_data if c.get("severity") == "critical"),
        "warning": sum(1 for c in collisions_data if c.get("severity") == "warning"),
        "info": sum(1 for c in collisions_data if c.get("severity") == "info"),
    }

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    collisions_data.sort(key=lambda c: severity_order.get(c.get("severity", "warning"), 1))

    return {
        "generated_at": datetime.now().isoformat(),
        "total_collisions": len(collisions_data),
        "collision_summary": {
            "total": len(collisions_data),
            "identical": identical_count,
            "conflicting": conflicting_count,
            "by_severity": severity_counts,
        },
        "collisions": collisions_data,
    }
