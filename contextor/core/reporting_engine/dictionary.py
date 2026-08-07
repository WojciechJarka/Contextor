"""
core/reporting_engine/dictionary.py

Generates and manages the master index dictionary for extreme JSON compression.
Now acts as a view/proxy over PersistentIdentityRegistry.
"""

from typing import Dict, Any, List, Optional
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

class IndexDictionary:
    def __init__(self, registry: PersistentIdentityRegistry):
        self.registry = registry

    def get_module_id(self, module_name: str) -> str:
        # Try to get from registry
        obj_id = self.registry.get_module_id(module_name)
        if obj_id is not None:
            return obj_id
            
        # If it doesn't exist, it means it wasn't synced. We just return it as a string to avoid crashes,
        # but in a correct flow, it should have been synced.
        return module_name

    def get_artifact_id(self, artifact_name: str) -> str:
        obj_id = self.registry.get_artifact_id(artifact_name)
        if obj_id is not None:
            return obj_id
        return artifact_name

    def to_json_dict(self) -> Dict[str, Any]:
        """Returns the dictionary representation for saving."""
        # The legacy format returned a dictionary. 
        # But wait! We no longer save the dictionary! 
        # The user plan says: "Usuwamy: _save_index_dictionary_with_dedup(), lokalne numerowanie raportów."
        # We can just return empty dict here or the current active state if anything still calls it.
        # Let's return the active mapping just in case it's used for in-memory debugging.
        modules = {}
        if "module_registry" in self.registry._state:
            modules = self.registry._state["module_registry"].get("id_to_path", {})
            
        artifacts = {}
        if "artifact_registry" in self.registry._state:
            artifacts = self.registry._state["artifact_registry"].get("id_to_path", {})
            
        return {
            "modules": modules,
            "artifacts": artifacts
        }

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> 'IndexDictionary':
        """Reconstructs the index dictionary from saved JSON data."""
        raise NotImplementedError("IndexDictionary.from_json_dict is obsolete and should not be used.")

def compact_recursively(data: Any, index_dict: IndexDictionary, known_modules: set[str]) -> Any:
    """Recursively replaces module names and artifact keys with their string IDs."""
    if isinstance(data, dict):
        return {
            str(compact_recursively(k, index_dict, known_modules)): 
            compact_recursively(v, index_dict, known_modules)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [compact_recursively(x, index_dict, known_modules) for x in data]
    elif isinstance(data, str):
        if data in known_modules:
            return index_dict.get_module_id(data)
        if "::" in data:
            parts = data.split("::")
            if len(parts) == 2 and parts[0] in known_modules:
                return index_dict.get_artifact_id(data)
        if " -> " in data:
            parts = data.split(" -> ")
            compacted_parts = []
            for part in parts:
                if part in known_modules:
                    compacted_parts.append(str(index_dict.get_module_id(part)))
                else:
                    compacted_parts.append(part)
            return " -> ".join(compacted_parts)
        return data
    else:
        return data
