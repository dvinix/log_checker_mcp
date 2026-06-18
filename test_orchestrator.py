import asyncio
import os
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from mcp import StdioServerParameters

async def run():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "d:\\log_checker_mcp\\orchestrator\\main.py"],
        env=os.environ.copy()
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Orchestrator initialized. Calling check_logs...")
            result = await session.call_tool("check_logs", arguments={
                "repoRoot": "d:\\log_checker_mcp",
                "githubOwner": "testowner",
                "githubRepo": "testrepo",
                "logContent": "File \"bad_file.py\", line 2\nZeroDivisionError: division by zero",
                "dryRun": True
            })
            
            for content in result.content:
                if content.type == "text":
                    print(content.text)

if __name__ == "__main__":
    asyncio.run(run())
