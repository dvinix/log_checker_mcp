import os
import re
import time
import sys
from functools import partial

# Redirect prints to stderr
print = partial(print, file=sys.stderr)

from huggingface_hub import HfApi
from config import HF_SPACE_ID, ERROR_DEDUP_TTL_MS
import itertools

_seen_errors = {}
api = HfApi()

def get_new_errors():
    errors = []
    now = time.time() * 1000
    
    # clean up old seen errors
    keys_to_delete = [k for k, v in _seen_errors.items() if now - v > ERROR_DEDUP_TTL_MS]
    for k in keys_to_delete:
        del _seen_errors[k]

    try:
        # fetch_space_logs can hang if the stream is open. We read up to 1000 lines.
        print(f"[LogWatcher] Fetching logs from HF Space {HF_SPACE_ID}...")
        logs_generator = api.fetch_space_logs(repo_id=HF_SPACE_ID)
        lines = list(itertools.islice(logs_generator, 1000))
        print(f"[LogWatcher] Fetched {len(lines)} log lines.")
    except Exception as e:
        print(f"[LogWatcher] Failed to fetch logs from HF Space {HF_SPACE_ID}: {e}")
        return errors

    current_error = None
    stack_lines = []
    
    for i, line in enumerate(lines):
        line_str = str(line).strip()
        if not line_str:
            continue
            
        match = re.search(r'\b(ERROR|FATAL|EXCEPTION|CRITICAL)\b', line_str, re.IGNORECASE)
        
        if match:
            if current_error:
                current_error['stack'] = "\n".join(stack_lines)
                _add_if_new(current_error, errors)
                stack_lines = []
            
            level = match.group(1).upper()
            msg = line_str
            
            current_error = {
                'file': f"HF_Space:{HF_SPACE_ID}",
                'lineNumber': i + 1,
                'level': level,
                'message': msg,
                'stack': ''
            }
        elif current_error:
            stack_lines.append(line_str)
            
    if current_error:
        current_error['stack'] = "\n".join(stack_lines)
        _add_if_new(current_error, errors)
        
    return errors

def _add_if_new(error, error_list):
    err_sig = f"{error['message']}-{error['stack'][:200]}"
    now = time.time() * 1000
    if err_sig not in _seen_errors:
        _seen_errors[err_sig] = now
        error_list.append(error)
