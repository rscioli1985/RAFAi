from __future__ import annotations

from services.backend.graphql.schema import schema


def test_graphql_schema_contains_expected_types() -> None:
    printed = schema.as_str()
    assert "type Query" in printed
    assert "type Mutation" in printed
    assert "runScrape" in printed
    assert "reanalyze" in printed
    assert "reembed" in printed
