import os
import re
from config import SOURCE_DIR, ALLOWED_EXTENSIONS

def find_relevant_files(error):
    relevant_files = []
    stack = error.get('stack', '') + "\n" + error.get('message', '')
    
    # Extract potential filenames from stack trace
    pattern = r'([a-zA-Z0-9_\-\/\\]+\.(?:' + '|'.join(ext.strip('.') for ext in ALLOWED_EXTENSIONS) + r'))'
    potential_paths = re.findall(pattern, stack)
    
    potential_paths = list(set(potential_paths))
    
    for root, _, files in os.walk(SOURCE_DIR):
        # Skip standard dirs
        if any(skip in root for skip in ['node_modules', '.venv', '.git', '__pycache__']):
            continue
            
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in ALLOWED_EXTENSIONS:
                if any(file in path for path in potential_paths):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        relevant_files.append({
                            'path': full_path,
                            'relativePath': os.path.relpath(full_path, SOURCE_DIR),
                            'content': content
                        })
                    except:
                        pass
                        
    return relevant_files[:3] # Limit to 3 files
