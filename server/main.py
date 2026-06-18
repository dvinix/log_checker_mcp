import time
import schedule
import os
import sys
from functools import partial

# Redirect all prints to stderr to avoid breaking MCP JSON-RPC
print = partial(print, file=sys.stderr)

from mcp.server.fastmcp import FastMCP
from config import CRON_SCHEDULE, SOURCE_DIR
from log_watcher import get_new_errors
from source_finder import find_relevant_files
from ai_fixer import generate_fix
from github_pr import apply_fix_and_raise_pr

def run_pipeline():
    print(f"\n[Pipeline] Starting run...")
    
    errors = get_new_errors()
    if not errors:
        print("  [OK] No new errors found")
        return
        
    print(f"  [WARN] Found {len(errors)} new error(s)")
    
    for i, error in enumerate(errors):
        print("-" * 60)
        print(f"  [{i+1}/{len(errors)}] {error['level']}: {error['message'][:100]}")
        
        try:
            print("  [Source] Locating relevant files...")
            source_files = find_relevant_files(error)
            
            if not source_files:
                print("  No source files found - skipping")
                continue
                
            print(f"  Found: {', '.join([f['relativePath'] for f in source_files])}")
            
            fix = generate_fix(error, source_files)
            if not fix:
                continue
                
            print(f"  [AI] Fix generated: {fix['prTitle']}")
            
            target_file = None
            fix_basename = os.path.basename(fix['filePath'].replace('/', os.sep))
            
            for f in source_files:
                if os.path.basename(f['relativePath']) == fix_basename:
                    target_file = f
                    break
                    
            if not target_file:
                abs_path = os.path.join(SOURCE_DIR, fix['filePath'])
                if os.path.exists(abs_path):
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        target_file = {
                            'path': abs_path,
                            'content': f.read()
                        }
                        
            if not target_file:
                print(f"  Could not find file to patch: {fix['filePath']}")
                continue
                
            result = apply_fix_and_raise_pr(fix, target_file['path'], target_file['content'])
            print(f"  [OK] PR raised: {result['prUrl']}")
            print(f"    Branch: {result['branchName']}")
            
        except Exception as e:
            print(f"  [FAIL] Pipeline failed for error: {e}")

mcp = FastMCP("log-checker")

@mcp.tool()
def run_pipeline_tool() -> str:
    """Run the log checking and bug fixing pipeline."""
    print("Received request to run pipeline via MCP...")
    run_pipeline()
    return "Pipeline execution completed."

if __name__ == "__main__":
    print("Starting FastMCP server...")
    mcp.run()
