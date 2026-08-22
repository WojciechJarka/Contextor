import copy
import difflib
import pytest

from contextor.mcp.query_helpers import (
    FUZZY_MIN_SCORE,
    FUZZY_MAX_CANDIDATES,
    is_module_id,
    resolve_module_identity,
    resolve_artifact_identity,
)


@pytest.fixture
def module_maps():
    mod_path_to_id = {
        "pkg.core": "10/1",
        "pkg.utils": "11/1",
        "pkg.models": "12/1",
        "pkg.services.auth": "13/1",
        "pkg.services.billing": "14/1",
        "pkg.services.shipping": "15/1",
        "pkg.services.notifications": "16/1",
        "pkg.services.reporting": "17/1",
    }
    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}
    return mod_path_to_id, mod_id_to_path


@pytest.fixture
def artifact_maps():
    art_path_to_id = {
        "pkg.core::my_func": "A100/1",
        "pkg.core::calculate_total": "A101/1",
        "pkg.utils::calculate_total": "A102/1",
        "pkg.models::User": "A103/1",
        "pkg.services.auth::authenticate_user": "A104/1",
        "pkg.services.auth::authorize_token": "A105/1",
        "pkg.services.billing::charge_customer": "A106/1",
        "pkg.services.shipping::create_label": "A107/1",
        "pkg.services.notifications::send_email": "A108/1",
        "pkg.services.notifications::send_sms": "A109/1",
        "pkg.services.reporting::generate_summary": "A110/1",
    }
    art_id_to_path = {v: k for k, v in art_path_to_id.items()}
    return art_path_to_id, art_id_to_path


# =========================================================================
# MODULE RESOLUTION TESTS
# =========================================================================

def test_resolve_module_exact_id(module_maps):
    p2i, i2p = module_maps
    res = resolve_module_identity("10/1", p2i, i2p)
    assert res == {
        "status": "resolved",
        "resolution": "exact_id",
        "module": "pkg.core",
        "module_id": "10/1",
        "similar_candidates": [],
    }


def test_resolve_module_exact_name(module_maps):
    p2i, i2p = module_maps
    res = resolve_module_identity("pkg.core", p2i, i2p)
    assert res == {
        "status": "resolved",
        "resolution": "exact_name",
        "module": "pkg.core",
        "module_id": "10/1",
        "similar_candidates": [],
    }


def test_resolve_module_nonexistent_id_never_fuzzy(module_maps):
    p2i, i2p = module_maps
    res = resolve_module_identity("999/1", p2i, i2p)
    assert res == {
        "status": "not_found",
        "query": "999/1",
        "query_kind": "module_id",
        "similar_candidates": [],
    }


def test_resolve_module_fuzzy_missing_letter(module_maps):
    p2i, i2p = module_maps
    res = resolve_module_identity("pkg.cor", p2i, i2p)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg.cor"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["module"] == "pkg.core"
    assert top["module_id"] == "10/1"
    assert top["score"] >= FUZZY_MIN_SCORE


def test_resolve_module_fuzzy_transposition(module_maps):
    p2i, i2p = module_maps
    res = resolve_module_identity("pkg.coer", p2i, i2p)
    assert res["status"] == "not_found"
    assert any(c["module"] == "pkg.core" for c in res["similar_candidates"])


def test_resolve_module_fuzzy_threshold_rejects_unrelated(module_maps):
    p2i, i2p = module_maps
    res = resolve_module_identity("completely.unrelated.module", p2i, i2p)
    assert res == {
        "status": "not_found",
        "query": "completely.unrelated.module",
        "similar_candidates": [],
    }


def test_resolve_module_max_5():
    p2i = {
        f"pkg.services.item_{i}": f"10{i}/1"
        for i in range(10)
    }
    i2p = {v: k for k, v in p2i.items()}
    res = resolve_module_identity("pkg.services.item", p2i, i2p)
    assert res["status"] == "not_found"
    assert len(res["similar_candidates"]) == FUZZY_MAX_CANDIDATES


def test_resolve_module_deterministic_equal_score_ordering(monkeypatch):
    p2i = {
        "pkg.beta": "1/1",
        "pkg.alpha": "2/1",
        "pkg.gamma": "3/1",
    }
    i2p = {v: k for k, v in p2i.items()}
    monkeypatch.setattr(difflib.SequenceMatcher, "ratio", lambda self: 0.85)
    res = resolve_module_identity("query", p2i, i2p)
    names = [c["module"] for c in res["similar_candidates"]]
    assert names == ["pkg.alpha", "pkg.beta", "pkg.gamma"]


# =========================================================================
# ARTIFACT RESOLUTION TESTS
# =========================================================================

def test_resolve_artifact_exact_id(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("A100/1", p2i, i2p)
    assert res == {
        "status": "resolved",
        "resolution": "exact_id",
        "artifact": "pkg.core::my_func",
        "artifact_id": "A100/1",
        "similar_candidates": [],
    }


def test_resolve_artifact_lowercase_a_id(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("a100/1", p2i, i2p)
    assert res == {
        "status": "resolved",
        "resolution": "exact_id",
        "artifact": "pkg.core::my_func",
        "artifact_id": "A100/1",
        "similar_candidates": [],
    }


def test_resolve_artifact_nonexistent_id_never_fuzzy(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("A999/1", p2i, i2p)
    assert res == {
        "status": "not_found",
        "query": "A999/1",
        "query_kind": "artifact_id",
        "similar_candidates": [],
    }


def test_resolve_artifact_exact_full_canonical_identity(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("pkg.core::my_func", p2i, i2p)
    assert res == {
        "status": "resolved",
        "resolution": "exact_identity",
        "artifact": "pkg.core::my_func",
        "artifact_id": "A100/1",
        "similar_candidates": [],
    }


def test_resolve_artifact_unique_exact_leaf(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("my_func", p2i, i2p)
    assert res == {
        "status": "resolved",
        "resolution": "exact_leaf",
        "artifact": "pkg.core::my_func",
        "artifact_id": "A100/1",
        "similar_candidates": [],
    }


def test_resolve_artifact_ambiguous_exact_leaf(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("calculate_total", p2i, i2p)
    assert res == {
        "status": "ambiguous",
        "resolution": "exact_leaf",
        "query": "calculate_total",
        "candidates": [
            {
                "artifact": "pkg.core::calculate_total",
                "artifact_id": "A101/1",
            },
            {
                "artifact": "pkg.utils::calculate_total",
                "artifact_id": "A102/1",
            },
        ],
    }


def test_resolve_artifact_fuzzy_full_identity_typo(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("pkg.core::my_fnc", p2i, i2p)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg.core::my_fnc"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["artifact"] == "pkg.core::my_func"
    assert top["artifact_id"] == "A100/1"
    assert top["score"] >= FUZZY_MIN_SCORE


def test_resolve_artifact_fuzzy_leaf_typo(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("my_fnc", p2i, i2p)
    assert res["status"] == "not_found"
    assert res["query"] == "my_fnc"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["artifact"] == "pkg.core::my_func"
    assert top["artifact_id"] == "A100/1"
    assert top["score"] >= FUZZY_MIN_SCORE


def test_resolve_artifact_score_and_id_returned_with_candidate(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("my_fnc", p2i, i2p)
    for c in res["similar_candidates"]:
        assert "artifact" in c
        assert "artifact_id" in c
        assert "score" in c
        assert isinstance(c["score"], float)
        assert c["score"] >= FUZZY_MIN_SCORE


def test_resolve_artifact_max_5():
    p2i = {
        f"pkg.mod::function_{i}": f"A{100+i}/1"
        for i in range(10)
    }
    i2p = {v: k for k, v in p2i.items()}
    res = resolve_artifact_identity("function", p2i, i2p)
    assert res["status"] == "not_found"
    assert len(res["similar_candidates"]) == FUZZY_MAX_CANDIDATES


def test_resolve_artifact_deterministic_equal_score_ordering(monkeypatch):
    p2i = {
        "pkg.z::common_beta": "A1/1",
        "pkg.a::common_alpha": "A2/1",
    }
    i2p = {v: k for k, v in p2i.items()}
    monkeypatch.setattr(difflib.SequenceMatcher, "ratio", lambda self: 0.85)
    res = resolve_artifact_identity("query", p2i, i2p)
    artifacts = [c["artifact"] for c in res["similar_candidates"]]
    assert artifacts == ["pkg.a::common_alpha", "pkg.z::common_beta"]


def test_resolve_artifact_unrelated_query_below_threshold(artifact_maps):
    p2i, i2p = artifact_maps
    res = resolve_artifact_identity("completely_unrelated_symbol", p2i, i2p)
    assert res == {
        "status": "not_found",
        "query": "completely_unrelated_symbol",
        "similar_candidates": [],
    }


# =========================================================================
# GENERAL & BOUNDARY TESTS
# =========================================================================

def test_identity_resolution_empty_or_whitespace(module_maps, artifact_maps):
    m_p2i, m_i2p = module_maps
    a_p2i, a_i2p = artifact_maps

    for empty_input in ("", "   ", "\t\n"):
        m_res = resolve_module_identity(empty_input, m_p2i, m_i2p)
        assert m_res == {
            "status": "not_found",
            "query": "",
            "similar_candidates": [],
        }

        a_res = resolve_artifact_identity(empty_input, a_p2i, a_i2p)
        assert a_res == {
            "status": "not_found",
            "query": "",
            "similar_candidates": [],
        }


def test_active_only_recovery_excluded():
    active_p2i = {"pkg.active_module": "1/1"}
    active_i2p = {"1/1": "pkg.active_module"}
    recovery_p2i = {"pkg.recovered_module": "2/1"}  # Excluded from resolver parameters

    res = resolve_module_identity("pkg.recovered_module", active_p2i, active_i2p)
    # Since recovery is excluded from active maps, it's not found and not resolved
    assert res["status"] == "not_found"
    # Even if fuzzy matches, it only matches active
    for c in res["similar_candidates"]:
        assert c["module"] == "pkg.active_module"


def test_input_maps_not_mutated(module_maps, artifact_maps):
    m_p2i, m_i2p = module_maps
    a_p2i, a_i2p = artifact_maps

    m_p2i_copy = copy.deepcopy(m_p2i)
    m_i2p_copy = copy.deepcopy(m_i2p)
    a_p2i_copy = copy.deepcopy(a_p2i)
    a_i2p_copy = copy.deepcopy(a_i2p)

    resolve_module_identity("pkg.cor", m_p2i, m_i2p)
    resolve_artifact_identity("my_fnc", a_p2i, a_i2p)

    assert m_p2i == m_p2i_copy
    assert m_i2p == m_i2p_copy
    assert a_p2i == a_p2i_copy
    assert a_i2p == a_i2p_copy


def test_fuzzy_threshold_boundary(monkeypatch):
    p2i = {
        "pkg.exact_threshold": "1/1",
        "pkg.below_threshold": "2/1",
    }
    i2p = {v: k for k, v in p2i.items()}

    def mock_ratio(self):
        if str(self.b).endswith("exact_threshold"):
            return 0.75
        elif str(self.b).endswith("below_threshold"):
            return 0.7499
        return 0.0

    monkeypatch.setattr(difflib.SequenceMatcher, "ratio", mock_ratio)

    res = resolve_module_identity("query", p2i, i2p)
    candidates = [c["module"] for c in res["similar_candidates"]]
    assert "pkg.exact_threshold" in candidates
    assert "pkg.below_threshold" not in candidates


def test_resolver_signatures_locked():
    import inspect

    mod_sig = inspect.signature(resolve_module_identity)
    assert list(mod_sig.parameters.keys()) == [
        "query",
        "mod_path_to_id",
        "mod_id_to_path",
    ]
    for param in mod_sig.parameters.values():
        assert param.default is inspect.Parameter.empty

    art_sig = inspect.signature(resolve_artifact_identity)
    assert list(art_sig.parameters.keys()) == [
        "query",
        "art_path_to_id",
        "art_id_to_path",
    ]
    for param in art_sig.parameters.values():
        assert param.default is inspect.Parameter.empty


def test_is_module_id():
    # True
    assert is_module_id("259/1") is True
    assert is_module_id(" 259/1 ") is True
    assert is_module_id("10/1") is True
    assert is_module_id("0/0") is True

    # False
    assert is_module_id("A259/1") is False
    assert is_module_id("259") is False
    assert is_module_id("259/abc") is False
    assert is_module_id("pkg/mod.py") is False
    assert is_module_id("pkg.mod") is False
    assert is_module_id("") is False
    assert is_module_id("259/1/2") is False
