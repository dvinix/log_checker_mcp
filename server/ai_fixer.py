import json
import sys
from functools import partial

# Redirect prints to stderr
print = partial(print, file=sys.stderr)

from groq import Groq
from config import GROQ_API_KEY

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set.")
    client = None
else:
    client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are an expert software engineer and debugging assistant.
You will be given:
1. An error message and stack trace from application logs
2. The source files most likely related to the error

Your task:
- Identify the root cause of the error
- Produce a MINIMAL, targeted code fix
- Do NOT rewrite or refactor unrelated code
- Do NOT change function signatures unless absolutely necessary

Respond with ONLY a JSON object (no markdown fences) in this exact shape:
{
  "filePath": "<relative path to the file that needs changing>",
  "originalCode": "<the exact code block to replace — must match the file exactly>",
  "fixedCode": "<corrected replacement code>",
  "explanation": "<concise 1-3 sentence explanation of the root cause and fix>",
  "prTitle": "fix: <short description>",
  "prBody": "<markdown PR description>"
}

If no fix is possible return:
{
  "filePath": null,
  "explanation": "<reason>"
}"""

def generate_fix(error, source_files):
    if not client:
        return None
        
    files_section = ""
    for f in source_files:
        files_section += f"### {f['relativePath']}\n```\n{f['content']}\n```\n\n"
        
    user_message = f"""## Error from logs
**Level:** {error.get('level')}
**File:** {error.get('file')}
**Message:** {error.get('message')}
**Stack trace:**
```
{error.get('stack')}
```

## Source files
{files_section}
"""

    print(f"  [AI] Asking Groq to fix: {error.get('message')[:80]}...")
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        raw = completion.choices[0].message.content
        fix = json.loads(raw)
        
        if not fix.get('filePath'):
            print(f"  [AI] No code fix applicable: {fix.get('explanation')}")
            return None
            
        return fix
    except Exception as e:
        print(f"  [AI] Failed to generate/parse fix: {e}")
        return None
