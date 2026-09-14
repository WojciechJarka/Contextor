import asyncio
import json
from pathlib import Path
import contextor.mcp.tools.contextor_profile_analysis as profile_tool
class P:
    returncode=0
    async def communicate(self, request):
        self.request=request
        return json.dumps({"schema":"contextor-profile-analysis/v1","status":"ok","operation_id":"profile-test"}).encode(), b""
def test_contextor_profile_analysis_uses_isolated_worker_process(tmp_path: Path, monkeypatch):
    observed={}; process=P()
    async def fake(*args, **kwargs): observed["args"]=args; observed["kwargs"]=kwargs; return process
    monkeypatch.setattr(profile_tool.asyncio,"create_subprocess_exec",fake)
    raw=asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path),exclude_paths=["generated"]))
    assert observed["args"]==(profile_tool.sys.executable,"-u","-m","contextor.core.analysis.profile_worker")
    assert json.loads(process.request)=={"repo_path":str(tmp_path.resolve()),"exclude_paths":["generated"]}
    assert json.loads(raw)["status"]=="ok"
def test_contextor_profile_analysis_rejects_missing_repository_before_worker(tmp_path: Path, monkeypatch):
    async def forbidden(*args, **kwargs): raise AssertionError()
    monkeypatch.setattr(profile_tool.asyncio,"create_subprocess_exec",forbidden)
    assert asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path/"missing"))).startswith("Error:")
