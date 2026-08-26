import json

from contextor.core.canonical_state_query.contract import (
    CANONICAL_QUERY_SCHEMA_VERSION,
    LANGUAGE_VERSION,
    describe_contract,
)


def describe_canonical_state(
    schema_version: str = CANONICAL_QUERY_SCHEMA_VERSION,
    language_version: str = LANGUAGE_VERSION,
) -> str:
    return json.dumps(


        describe_contract(schema_version=schema_version, language_version=language_version),
        indent=2,
        ensure_ascii=False,
    )

