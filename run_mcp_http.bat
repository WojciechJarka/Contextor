@echo off
setlocal
cd /d "%~dp0"

set "CONTEXTOR_MCP_TRANSPORT=streamable-http"
set "CONTEXTOR_MCP_HOST=127.0.0.1"
set "CONTEXTOR_MCP_PORT=8765"

"C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u -m contextor.mcp_server
