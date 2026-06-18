import os
import json
import sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Ensure shared models can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.types import BugReport, CodeFix

from mcp.server.fastmcp import FastMCP
from google import genai

mcp = FastMCP("bug-fixer-mcp")

@mcp.tool()
def fix_multiple_bugs(bugs: list[dict], repoRoot: str, dryRun: bool = False, stopOnFirstError: bool = False) -> str:
    """Uses Gemini API Pro to generate and apply code patches."""
    client = genai.Client() # Uses GEMINI_API_KEY from environment
    results = []
    
    for bug_dict in bugs:
        bug = BugReport(**bug_dict)
        if not bug.filePath:
            continue
            
        full_path = bug.filePath
        if not os.path.isabs(full_path):
            full_path = os.path.join(repoRoot, full_path)
            
        if not os.path.exists(full_path):
            results.append(CodeFix(
                bugId=bug.id,
                filePath=bug.filePath,
                explanation="File not found.",
                applied=False,
                error="File not found"
            ).model_dump())
            continue
            
        with open(full_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
            
        # Prompt Gemini to fix
        prompt = f"""
You are an expert Python developer. A bug was found in this file: {bug.filePath}.
Error Message: {bug.errorMessage}
Stack Trace Context:
{bug.stackTrace or 'N/A'}

Line Number: {bug.lineNumber or 'N/A'}

File Content:
```python
{file_content}
```

Please fix the bug. Return ONLY a JSON object with two keys:
"fixedCode": the complete fixed code for the entire file.
"explanation": a short explanation of what you changed.

Do not use markdown formatting around the JSON block. Ensure valid JSON.
"""
        
        try:
            from contextlib import redirect_stdout
            import sys
            with redirect_stdout(sys.stderr):
                response = client.models.generate_content(
                    model='gemini-2.5-pro',
                    contents=prompt,
                    config={'response_mime_type': 'application/json'}
                )
            
            resp_data = json.loads(response.text)
            fixed_code = resp_data.get('fixedCode', file_content)
            explanation = resp_data.get('explanation', 'No explanation provided.')
            
            if not dryRun:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                    
            results.append(CodeFix(
                bugId=bug.id,
                filePath=bug.filePath,
                fixedCode=fixed_code,
                explanation=explanation,
                applied=True
            ).model_dump())
            
        except Exception as e:
            results.append(CodeFix(
                bugId=bug.id,
                filePath=bug.filePath,
                explanation="Failed to fix.",
                applied=False,
                error=str(e)
            ).model_dump())
            
            if stopOnFirstError:
                break

    return json.dumps({"results": results})

if __name__ == "__main__":
    mcp.run(transport="stdio")
