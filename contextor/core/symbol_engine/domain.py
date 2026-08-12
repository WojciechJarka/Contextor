from dataclasses import dataclass, field


@dataclass
class SymbolFacts:
    classes: set[str] = field(default_factory=set)
    functions: set[str] = field(default_factory=set)
    methods: set[str] = field(default_factory=set)
    globals: set[str] = field(default_factory=set)
    calls: set[str] = field(default_factory=set)
    assignments: set[str] = field(default_factory=set)
    signatures: dict[str, str] = field(default_factory=dict)
    body_fingerprints: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def all_symbols(self) -> set[str]:
        return self.classes | self.functions | self.methods | self.globals

    def to_dict(self):
        return {
            "classes": sorted(self.classes),
            "functions": sorted(self.functions),
            "methods": sorted(self.methods),
            "globals": sorted(self.globals),
            "calls": sorted(self.calls),
            "assignments": sorted(self.assignments),
            "signatures": self.signatures,
            "body_fingerprints": self.body_fingerprints,
            "errors": self.errors,
        }
