import os
import re

def parse_paths_from_text(text: str) -> list[str]:
    """
    Extracts valid file paths from arbitrary text.
    Handles comma-separated, numbered lists, comments, spaces in paths, etc.
    """
    found_paths = []
    seen = set()

    def add_path(p):
        p = os.path.abspath(p)
        if p not in seen:
            seen.add(p)
            found_paths.append(p)

    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try checking the whole line first (common case, e.g., one path per line)
        clean_line = line.strip('"\' \t,;')
        if os.path.isfile(clean_line):
            add_path(clean_line)
            continue
            
        # Find all boundaries that could start a path
        # We consider a word start as the beginning of the line or after a space, tab, comma, semicolon, etc.
        word_starts = [0] + [m.end() for m in re.finditer(r'[ \t,;:\'"\(\[\{=]+', line)]
        
        skip_until = -1
        for start_idx in word_starts:
            if start_idx < skip_until:
                continue
            if start_idx >= len(line):
                continue
                
            # Limit candidate length to 1000 characters to prevent long lines from hanging
            candidate_full = line[start_idx:start_idx + 1000]
            
            found_len = 0
            # Right-shrink the candidate to find the longest valid file path
            while candidate_full:
                candidate_clean = candidate_full.strip('"\' \t,;.')
                if candidate_clean and os.path.isfile(candidate_clean):
                    add_path(candidate_clean)
                    found_len = len(candidate_full)
                    break
                
                # If we are down to 1 character, stop shrinking
                if len(candidate_full) <= 1:
                    break
                candidate_full = candidate_full[:-1]
                
            if found_len > 0:
                skip_until = start_idx + found_len

    return found_paths
