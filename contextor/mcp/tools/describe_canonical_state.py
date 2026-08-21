import json

from contextor.core.canonical_state_query import describe_contract


def describe_canonical_state() -> str:
    return json.dumps(describe_contract(), indent=2, ensure_ascii=False)

