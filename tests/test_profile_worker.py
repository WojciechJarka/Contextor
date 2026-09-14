from pathlib import Path
import pytest
import contextor.core.analysis.profile_worker as profile_worker
def test_execute_profile_request_delegates_to_profile_runner(tmp_path: Path, monkeypatch):
    observed={}
    def runner(repo_path, *, exclude_paths=None):
        observed["path"]=repo_path; observed["excludes"]=exclude_paths
        return {"schema":"contextor-profile-analysis/v1","status":"ok","operation_id":"x"}
    monkeypatch.setattr(profile_worker,"run_analysis_profile",runner)
    result=profile_worker.execute_profile_request({"repo_path":str(tmp_path),"exclude_paths":["generated"]})
    assert Path(observed["path"])==tmp_path
    assert observed["excludes"]==["generated"]
    assert result["status"]=="ok"
@pytest.mark.parametrize("payload",[None,[],{},{"repo_path":""},{"repo_path":"x","exclude_paths":"x"},{"repo_path":"x","exclude_paths":[""]},{"repo_path":"x","exclude_paths":[1]}])
def test_execute_profile_request_rejects_invalid_request(payload):
    with pytest.raises(ValueError): profile_worker.execute_profile_request(payload)
