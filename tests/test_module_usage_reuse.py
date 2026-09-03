from types import SimpleNamespace

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.usage_facts import MODULE_USAGE_FACTS_SEMANTIC_VERSION, ModuleUsageFacts
from contextor.core.reference.module_usage_reuse import build_module_usage_baseline_with_reuse
from contextor.core.analysis.state_manager import FileState, FileStateManager


def _module(path):
    return SimpleNamespace(absolute_path=path, imports=(), ast_tree="x = call()")


def _manager(paths):
    values={path: SimpleNamespace(sha256=sha) for path, sha in paths.items()}
    return SimpleNamespace(get_tracked_sha256=lambda path: getattr(values.get(path), "sha256", ""))


def _state(modules, facts, manifest, **extra):
    state = RepositoryAnalysisState(modules=modules, module_usages=facts, module_usages_manifest=manifest)
    for key, value in extra.items(): setattr(state, key, value)
    return state


def _entry(mid, path, sha="sha", version=MODULE_USAGE_FACTS_SEMANTIC_VERSION):
    return {"module_id": mid, "path": path, "sha256": sha, "semantic_version": version}


def test_unchanged_reuses_without_extractor(monkeypatch, tmp_path):
    path = str((tmp_path / "a.py").resolve()); (tmp_path / "a.py").write_text("x = call()")
    modules = {"a": _module(path)}; fact = ModuleUsageFacts(symbol_calls_materialized=True, reference_evidence_materialized=True)
    previous = _state(modules, {"a": fact}, {"a": _entry("a", path)})
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError()))
    facts, manifest = build_module_usage_baseline_with_reuse(modules, previous, _manager({path: "sha"}))
    assert facts == {"a": fact}; assert manifest["a"] == _entry("a", path)


def test_missing_manifest_full_rebuild(monkeypatch, tmp_path):
    path = str((tmp_path / "a.py").resolve()); (tmp_path / "a.py").write_text("x = call()")
    modules={"a":_module(path)}; calls=[]
    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline", lambda m: calls.append(m) or {"a": ModuleUsageFacts()})
    facts, _ = build_module_usage_baseline_with_reuse(modules, _state(modules,{"a":ModuleUsageFacts()},{}), _manager({path:"sha"}))
    assert calls and set(facts)=={"a"}


def test_changed_stale_or_corrupt_extracts_only_affected(monkeypatch, tmp_path):
    paths=[]
    for name in ("a", "b"):
        p=tmp_path/f"{name}.py"; p.write_text("x = call()"); paths.append(str(p.resolve()))
    modules={name:_module(path) for name,path in zip(("a","b"),paths)}
    good=ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=True)
    previous=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1],"old")})
    calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*_a,**_k:calls.append(mid) or good)
    facts,_=build_module_usage_baseline_with_reuse(modules,previous,_manager({paths[0]:"sha",paths[1]:"new"}))
    assert facts["a"] is good and calls==["b"]


def test_semantic_mismatch_and_resync_full_rebuild(monkeypatch, tmp_path):
    path=str((tmp_path/"a.py").resolve()); (tmp_path/"a.py").write_text("x=1")
    modules={"a":_module(path)}; calls=[]
    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda m:calls.append(m) or {"a":ModuleUsageFacts()})
    prior=_state(modules,{"a":ModuleUsageFacts()},{"a":_entry("a",path,version="old")})
    build_module_usage_baseline_with_reuse(modules,prior,_manager({path:"sha"}))
    prior.resync_required=True
    build_module_usage_baseline_with_reuse(modules,prior,_manager({path:"sha"}))
    assert len(calls)==2


def test_tracked_sha_is_zero_io(monkeypatch, tmp_path):
    manager = FileStateManager(str(tmp_path / "cache")); path = str((tmp_path / "a.py").resolve())
    manager._state[path] = FileState(1, 1, "captured")
    monkeypatch.setattr(manager, "_compute_hash", lambda *_a: (_ for _ in ()).throw(AssertionError()))
    assert manager.get_tracked_sha256(path) == "captured"


def _two(tmp_path):
    paths=[]
    for n in ("a","b"):
        p=tmp_path/f"{n}.py"; p.write_text("x=1"); paths.append(str(p.resolve()))
    modules={n:_module(p) for n,p in zip(("a","b"),paths)}; good=ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=True)
    return modules,paths,good

def test_added_module_extracts_only_added(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); old={"a":modules["a"]}; prior=_state(old,{"a":good},{"a":_entry("a",paths[0])}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"new"})); assert calls==["b"]

def test_deleted_module_absent_from_outputs(tmp_path):
    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])})
    facts,manifest=build_module_usage_baseline_with_reuse({"a":modules["a"]},prior,_manager({paths[0]:"sha"})); assert set(facts)==set(manifest)=={"a"}

def test_stale_same_sha_extracts(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])},module_parse_freshness={"a":{"state":"stale"}}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]

def test_unmaterialized_channels_extract(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); bad=ModuleUsageFacts(symbol_calls_materialized=False,reference_evidence_materialized=True); prior=_state(modules,{"a":bad,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]

def test_unmaterialized_reference_evidence_extracts(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); bad=ModuleUsageFacts(symbol_calls_materialized=True,reference_evidence_materialized=False); prior=_state(modules,{"a":bad,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]

def test_corrupt_fact_extracts(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":object(),"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]

def test_wrong_path_extracts(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a","wrong"),"b":_entry("b",paths[1])}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]

def test_empty_sha_extracts(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"",paths[1]:"sha"})); assert calls==["a"]

def test_incomplete_usage_domain_full_rebuild(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); calls=[]; prior=_state(modules,{"a":good},{"a":_entry("a",paths[0]),"b":_entry("b",paths[1])})
    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda mods:calls.append(mods) or {k:good for k in mods})
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert len(calls)==1

def test_incomplete_manifest_domain_full_rebuild(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); calls=[]; prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0])})
    monkeypatch.setattr("contextor.core.reference.engine._build_module_usage_baseline",lambda mods:calls.append(mods) or {k:good for k in mods})
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert len(calls)==1

def test_wrong_manifest_identity_path_or_sha_extracts(monkeypatch,tmp_path):
    modules,paths,good=_two(tmp_path); entry=_entry("wrong",paths[0]); prior=_state(modules,{"a":good,"b":good},{"a":entry,"b":_entry("b",paths[1])}); calls=[]
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda mid,*a,**k:calls.append(mid) or good)
    build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"})); assert calls==["a"]

def test_partial_unmaterialized_raises(monkeypatch,tmp_path):
    import pytest
    modules,paths,good=_two(tmp_path); prior=_state(modules,{"a":good,"b":good},{"a":_entry("a",paths[0],"old"),"b":_entry("b",paths[1])})
    monkeypatch.setattr("contextor.core.reference.module_usage_reuse.extract_module_usage_facts",lambda *_a,**_k:ModuleUsageFacts())
    with pytest.raises(RuntimeError): build_module_usage_baseline_with_reuse(modules,prior,_manager({paths[0]:"sha",paths[1]:"sha"}))
