import pytest

from contextor.core.lineage_query.service import SYMBOL_LINEAGE_SECTION_ORDER
from contextor.mcp.lineage_response import SymbolLineageResponsePlan, plan_symbol_lineage_response


def test_auto_plans_complete_symbol_candidate_for_size_decision():
    assert plan_symbol_lineage_response(mode=" AUTO ") == SymbolLineageResponsePlan("auto", SYMBOL_LINEAGE_SECTION_ORDER, True, True)


def test_preview_plans_all_sections_without_payload():
    assert plan_symbol_lineage_response(mode="preview") == SymbolLineageResponsePlan("preview", SYMBOL_LINEAGE_SECTION_ORDER, False, False)


def test_fetch_requires_explicit_sections_and_canonicalizes_order():
    assert plan_symbol_lineage_response(mode="fetch", sections=("state", "interface", "connections")) == SymbolLineageResponsePlan("fetch", ("interface", "connections", "state"), True, False)


@pytest.mark.parametrize("mode", ("auto", "preview"))
def test_auto_and_preview_reject_explicit_sections(mode):
    with pytest.raises(ValueError, match=f"{mode} mode does not accept an explicit section selection."):
        plan_symbol_lineage_response(mode=mode, sections=("interface",))


@pytest.mark.parametrize("sections", (None, ()))
def test_fetch_requires_non_empty_selection(sections):
    with pytest.raises(ValueError, match="fetch mode requires at least one section."):
        plan_symbol_lineage_response(mode="fetch", sections=sections)


def test_response_plan_rejects_invalid_contract():
    with pytest.raises(TypeError, match="mode must be a string."):
        plan_symbol_lineage_response(mode=object())
    with pytest.raises(ValueError, match="mode must be 'auto', 'preview', or 'fetch'."):
        plan_symbol_lineage_response(mode="other")
    with pytest.raises(TypeError, match="sections must be a tuple of section names."):
        plan_symbol_lineage_response(mode="fetch", sections=["interface"])
    with pytest.raises(ValueError, match="sections must contain non-empty strings."):
        plan_symbol_lineage_response(mode="fetch", sections=("",))
    with pytest.raises(ValueError, match="sections must not contain duplicates."):
        plan_symbol_lineage_response(mode="fetch", sections=("state", "state"))
    with pytest.raises(ValueError, match="Unknown symbol lineage sections: mystery"):
        plan_symbol_lineage_response(mode="fetch", sections=("mystery",))
