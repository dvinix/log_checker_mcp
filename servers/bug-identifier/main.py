import json
import re
import uuid
import os
import sys

# Ensure shared models can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.types import BugReport

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bug-identifier-mcp")

def parse_logs_to_bugs(log_content: str, max_bugs: int) -> list[dict]:
    # A simple regex to find typical Python exceptions or ERROR lines
    bugs = []
    lines = log_content.splitlines()
    for i, line in enumerate(lines):
        if len(bugs) >= max_bugs:
            break
        
        # very simple heuristic: look for "Error" or "Exception"
        if "Error" in line or "Exception" in line or "ERROR" in line:
            # try to extract file path if present
            file_path = None
            line_num = None
            # e.g., File "path/to/file.py", line 42
            m = re.search(r'File "([^"]+)", line (\d+)', line)
            if not m:
                # check previous lines
                for j in range(1, 4):
                    if i - j >= 0:
                        m = re.search(r'File "([^"]+)", line (\d+)', lines[i-j])
                        if m:
                            break
            
            if m:
                file_path = m.group(1)
                line_num = int(m.group(2))
                
            bug = BugReport(
                id=str(uuid.uuid4()),
                filePath=file_path,
                lineNumber=line_num,
                errorMessage=line.strip(),
                stackTrace="\n".join(lines[max(0, i-5):i+5]), # grab context
                severity="error"
            )
            bugs.append(bug.model_dump())
            
    return bugs

@mcp.tool()
def analyze_logs(logContent: str, maxBugs: int = 10) -> str:
    """Analyze raw log text and extract bugs."""
    bugs = parse_logs_to_bugs(logContent, maxBugs)
    return json.dumps({"bugs": bugs})

@mcp.tool()
def analyze_log_file(filePath: str, maxBugs: int = 10) -> str:
    """Read a log file from disk and extract bugs."""
    if not os.path.exists(filePath):
        return json.dumps({"bugs": []})
    with open(filePath, 'r', encoding='utf-8') as f:
        logContent = f.read()
    bugs = parse_logs_to_bugs(logContent, maxBugs)
    return json.dumps({"bugs": bugs})

if __name__ == "__main__":
    mcp.run(transport="stdio")
