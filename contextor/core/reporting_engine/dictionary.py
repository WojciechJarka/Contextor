"""
core/reporting_engine/dictionary.py

Generates and manages the master index dictionary for extreme JSON compression.
Converts module names to integers (e.g. 0, 1, 2).
Converts artifact names to prefixed integers (e.g. A0, A1, A2).
"""

from typing import Dict, Any, List

class IndexDictionary:
    def __init__(self):
        self.module_to_id: Dict[str, int] = {}
        self.id_to_module: Dict[int, str] = {}
        self.artifact_to_id: Dict[str, str] = {}
        self.id_to_artifact: Dict[str, str] = {}
        self._next_module_id = 0
        self._next_artifact_id = 0

    def get_module_id(self, module_name: str) -> int:
        if module_name not in self.module_to_id:
            idx = self._next_module_id
            self.module_to_id[module_name] = idx
            self.id_to_module[idx] = module_name
            self._next_module_id += 1
        return self.module_to_id[module_name]

    def get_artifact_id(self, artifact_name: str) -> str:
        if artifact_name not in self.artifact_to_id:
            idx = f"A{self._next_artifact_id}"
            self.artifact_to_id[artifact_name] = idx
            self.id_to_artifact[idx] = artifact_name
            self._next_artifact_id += 1
        return self.artifact_to_id[artifact_name]

    def to_json_dict(self) -> Dict[str, Any]:
        """Returns the dictionary representation for saving."""
        return {
            "modules": self.id_to_module,
            "artifacts": self.id_to_artifact
        }

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> 'IndexDictionary':
        """Reconstructs the index dictionary from saved JSON data."""
        idx = cls()
        modules = data.get("modules", {})
        artifacts = data.get("artifacts", {})
        
        for k, v in modules.items():
            k_int = int(k)
            idx.module_to_id[v] = k_int
            idx.id_to_module[k_int] = v
            idx._next_module_id = max(idx._next_module_id, k_int + 1)
            
        for k, v in artifacts.items():
            idx.artifact_to_id[v] = k
            idx.id_to_artifact[k] = v
            # parse the integer part of "Ax"
            try:
                num = int(k[1:])
                idx._next_artifact_id = max(idx._next_artifact_id, num + 1)
            except ValueError:
                pass
                
        return idx
