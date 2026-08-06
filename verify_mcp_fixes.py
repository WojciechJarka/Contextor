import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def test_fixes():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "contextor.mcp_server"],
        env=os.environ.copy()
    )

    repo_path = "c:/Temp/Contextor_Repo"

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\n1. Running analyze_project to ensure data exists...")
            result = await session.call_tool("analyze_project", {"repo_path": repo_path})
            print(result.content[0].text[:200] + "...")
            
            print("\n2. Testing get_report_diff...")
            # We need to run analyze_project twice to get a diff report, but let's see if it works
            # Just touch a file or we can just run it twice
            Path(repo_path, "dummy.py").touch()
            await session.call_tool("analyze_project", {"repo_path": repo_path})
            Path(repo_path, "dummy.py").unlink()
            await session.call_tool("analyze_project", {"repo_path": repo_path})
            
            diff_res = await session.call_tool("get_report_diff", {"repo_path": repo_path})
            print(diff_res.content[0].text[:500])
            
            print("\n3. Testing get_file_edit_context (risk_score & tests_covering)...")
            ctx_res = await session.call_tool("get_file_edit_context", {
                "repo_path": repo_path,
                "file_path": f"{repo_path}/contextor/core/reporting_engine/json_reporter.py"
            })
            ctx_data = json.loads(ctx_res.content[0].text)
            print("Risk score:", ctx_data.get("risk_score"))
            print("Tests covering:", ctx_data.get("tests_covering"))
            
            print("\n4. Testing get_layer_isolation (boundary_violations)...")
            iso_res = await session.call_tool("get_layer_isolation", {
                "repo_path": repo_path,
                "layer_name": "contract"
            })
            iso_data = json.loads(iso_res.content[0].text)
            print("Violations count:", iso_data.get("boundary_violations_count"))
            if iso_data.get("boundary_violations_count", 0) > 0:
                print("Violations:", iso_data.get("boundary_violations")[:2])
                
            print("\n5. Testing query_json_data (safe sandbox)...")
            from pathlib import Path
            summary_path = list(Path(f"{repo_path}/output").glob("*_summary_*.json"))[0]
            
            query = "[h['module'] for h in data.get('top_hotspots', [])]"
            q_res = await session.call_tool("query_json_data", {
                "json_path": str(summary_path),
                "python_filter_expression": query
            })
            print("Hotspots via query:", q_res.content[0].text)

            # Test malicious query
            query_evil = "import os; os.system('echo HACKED')"
            q_res_evil = await session.call_tool("query_json_data", {
                "json_path": str(summary_path),
                "python_filter_expression": query_evil
            })
            print("Evil query result (should error safely):", q_res_evil.content[0].text)

if __name__ == "__main__":
    asyncio.run(test_fixes())
