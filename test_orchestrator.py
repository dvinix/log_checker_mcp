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
                "githubOwner": "dvinix",
                "githubRepo": "log_checker_mcp",
                "logContent": """Traceback (most recent call last):
  File "D:\\log_checker_mcp\\calculator.py", line 6, in <module>
    print("Division:", divide(10, 0))
                       ^^^^^^^^^^^^^
  File "D:\\log_checker_mcp\\calculator.py", line 3, in divide
    return a / b
           ~~^~~
ZeroDivisionError: division by zero""",
                "dryRun": False
            })
            
            for content in result.content:
                if content.type == "text":
                    print(content.text)

if __name__ == "__main__":
    asyncio.run(run())
