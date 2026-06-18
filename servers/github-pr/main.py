import os
import json
import subprocess
import sys
import httpx
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Ensure shared models can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.types import CodeFix

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("github-pr-mcp")

from typing import Optional

@mcp.tool()
def create_fix_pr(owner: str, repo: str, fixes: list[dict], sessionId: str, baseBranch: Optional[str] = None, labels: Optional[list[str]] = None) -> str:
    """Creates a new branch, commits fixes, and opens a GitHub Pull Request."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return json.dumps({"success": False, "error": "GITHUB_TOKEN not set"})
        
    branch_name = f"fix-bugs-{sessionId[:8]}"
    repoRoot = os.getcwd()
    
    try:
        remote_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
        
        # Create a branch and commit via git CLI
        subprocess.run(["git", "checkout", "-B", branch_name], check=True, cwd=repoRoot, capture_output=True)
        subprocess.run(["git", "add", "."], check=True, cwd=repoRoot, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Fix bugs from session {sessionId}"], check=False, cwd=repoRoot, capture_output=True)
        subprocess.run(["git", "push", "-f", "-u", remote_url, branch_name], check=True, cwd=repoRoot, capture_output=True)
        
        # Create PR via GitHub API
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        pr_title = f"Fix bugs identified in log session {sessionId[:8]}"
        pr_body = "The following fixes were applied:\n\n"
        for fix_dict in fixes:
            fix = CodeFix(**fix_dict)
            pr_body += f"- **{fix.filePath}**: {fix.explanation}\n"
            
        data = {
            "title": pr_title,
            "body": pr_body,
            "head": branch_name,
            "base": baseBranch or "main"
        }
        
        response = httpx.post(url, headers=headers, json=data)
        response.raise_for_status()
        pr_data = response.json()
        
        # Optionally add labels
        if labels and pr_data.get("number"):
            label_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_data['number']}/labels"
            httpx.post(label_url, headers=headers, json={"labels": labels})
            
        return json.dumps({"success": True, "pullRequest": {"url": pr_data.get("html_url"), "number": pr_data.get("number")}})
        
    except subprocess.CalledProcessError as e:
        return json.dumps({"success": False, "error": f"Git command failed: {e.stderr.decode()}"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

if __name__ == "__main__":
    mcp.run(transport="stdio")
