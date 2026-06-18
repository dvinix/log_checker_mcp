#!/usr/bin/env python3
# orchestrator/main.py

import json
import os
import sys
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List
from contextlib import AsyncExitStack

from mcp.server.fastmcp import FastMCP
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from mcp import StdioServerParameters

# Initialize the Orchestrator Server
mcp = FastMCP("log-checker-mcp")

# Resolve absolute paths assuming the orchestrator and servers are sibling directories
SERVERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "servers")

async def call_child_tool(session: ClientSession, name: str, args: dict) -> dict:
    """Executes a tool on a child MCP server and parses the JSON text block."""
    result = await session.call_tool(name, arguments=args)
    text_content = next((c.text for c in result.content if c.type == "text"), None)
    if not text_content:
        raise ValueError(f"No text content returned from tool '{name}'")
    try:
        return json.loads(text_content)
    except Exception as e:
        print(f"FAILED TO PARSE JSON FROM TOOL {name}. Content was: {text_content!r}", file=sys.stderr)
        raise e

@mcp.tool()
async def check_logs(
    repoRoot: str,
    githubOwner: str,
    githubRepo: str,
    logContent: Optional[str] = None,
    logFilePath: Optional[str] = None,
    maxBugs: int = 10,
    dryRun: bool = False,
    baseBranch: Optional[str] = None,
    prLabels: Optional[List[str]] = None,
) -> str:
    """
    Full pipeline: parse logs -> identify bugs -> fix code -> open GitHub PR.
    Returns a complete AnalysisPipeline report including bugs, fixes, and PR URL.
    """
    if not logContent and not logFilePath:
        return json.dumps({"success": False, "error": "Provide 'logContent' or 'logFilePath'"})
        
    if prLabels is None:
        prLabels = ["bug", "automated-fix"]
        
    session_id = str(uuid.uuid4())
    pipeline = {
        "sessionId": session_id,
        "logSource": logFilePath or "(inline content)",
        "startedAt": datetime.utcnow().isoformat() + "Z",
        "bugs": [],
        "fixes": [],
        "status": "analyzing"
    }

    # Use AsyncExitStack to cleanly connect to and close child stdio streams 
    async with AsyncExitStack() as stack:
        try:
            print(f"[orchestrator] Starting session {session_id}", file=sys.stderr)

            # Define universal params using 'uv run' to execute child scripts
            def make_params(script_name):
                return StdioServerParameters(
                    command="uv",
                    args=["run", os.path.join(SERVERS_DIR, script_name, "main.py")],
                    env=os.environ.copy()
                )

            # 1. Spawn Bug Identifier
            bi_transport = await stack.enter_async_context(stdio_client(make_params("bug-identifier")))
            bi_session = await stack.enter_async_context(ClientSession(*bi_transport))
            await bi_session.initialize()

            # 2. Spawn Bug Fixer
            bf_transport = await stack.enter_async_context(stdio_client(make_params("bug-fixer")))
            bf_session = await stack.enter_async_context(ClientSession(*bf_transport))
            await bf_session.initialize()

            # 3. Spawn GitHub PR MCP
            gh_transport = await stack.enter_async_context(stdio_client(make_params("github-pr")))
            gh_session = await stack.enter_async_context(ClientSession(*gh_transport))
            await gh_session.initialize()

            # ── Step 1: Identify bugs 
            if logFilePath:
                bug_result = await call_child_tool(bi_session, "analyze_log_file", {"filePath": logFilePath, "maxBugs": maxBugs})
            else:
                bug_result = await call_child_tool(bi_session, "analyze_logs", {"logContent": logContent, "maxBugs": maxBugs})

            pipeline["bugs"] = bug_result.get("bugs", [])
            print(f"[orchestrator] Found {len(pipeline['bugs'])} bugs", file=sys.stderr)

            if not pipeline["bugs"]:
                pipeline["status"] = "completed"
                return json.dumps({"success": True, "message": "No bugs found.", "pipeline": pipeline}, indent=2)

            # ── Step 2: Fix bugs 
            pipeline["status"] = "fixing"
            fixable_bugs = [b for b in pipeline["bugs"] if b.get("filePath")]
            unfixable = len(pipeline["bugs"]) - len(fixable_bugs)

            if unfixable > 0:
                print(f"[orchestrator] Skipped {unfixable} bugs (no filePath provided).", file=sys.stderr)

            fixes = []
            if fixable_bugs:
                fix_result = await call_child_tool(bf_session, "fix_multiple_bugs", {
                    "bugs": fixable_bugs,
                    "repoRoot": repoRoot,
                    "dryRun": dryRun,
                    "stopOnFirstError": False
                })
                fixes = fix_result.get("results", [])

            pipeline["fixes"] = fixes
            applied_fixes = [f for f in fixes if f.get("applied")]
            print(f"[orchestrator] Applied {len(applied_fixes)} fixes", file=sys.stderr)

            # ── Step 3: Create GitHub PR 
            successful_fixes = [f for f in fixes if (f.get("applied") or dryRun) and not f.get("error")]

            if successful_fixes and not dryRun:
                pipeline["status"] = "creating_pr"
                pr_result = await call_child_tool(gh_session, "create_fix_pr", {
                    "owner": githubOwner,
                    "repo": githubRepo,
                    "fixes": successful_fixes,
                    "sessionId": session_id,
                    "baseBranch": baseBranch,
                    "labels": prLabels
                })

                if pr_result.get("success") and pr_result.get("pullRequest"):
                    pipeline["pullRequest"] = pr_result["pullRequest"]
                    print(f"[orchestrator] PR opened: {pipeline['pullRequest']['url']}", file=sys.stderr)
                else:
                    print(f"[orchestrator] PR creation failed: {pr_result.get('error')}", file=sys.stderr)

            pipeline["status"] = "completed"
            return json.dumps({
                "success": True,
                "pipeline": pipeline,
                "summary": {
                    "sessionId": session_id,
                    "bugsFound": len(pipeline["bugs"]),
                    "fixesApplied": len(applied_fixes),
                    "prUrl": pipeline.get("pullRequest", {}).get("url"),
                    "dryRun": dryRun
                }
            }, indent=2)

        except Exception as e:
            pipeline["status"] = "failed"
            pipeline["error"] = str(e)
            return json.dumps({"success": False, "error": str(e), "pipeline": pipeline}, indent=2)

if __name__ == "__main__":
    # Runs the orchestrator using standard stdio streams
    mcp.run(transport="stdio")