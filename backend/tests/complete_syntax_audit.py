import re
import sys

def audit_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"Auditing {filepath}: {len(lines)} lines total.")
    issues = []

    # 1. Bracket stack check
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    in_str = None
    in_template = False
    in_comment = False

    for l_idx, line in enumerate(lines, 1):
        i = 0
        while i < len(line):
            ch = line[i]

            # Block comment
            if in_comment:
                if ch == '*' and i + 1 < len(line) and line[i+1] == '/':
                    in_comment = False
                    i += 2
                    continue
                i += 1
                continue

            # Line comment
            if not in_str and not in_template:
                if ch == '/' and i + 1 < len(line) and line[i+1] == '*':
                    in_comment = True
                    i += 2
                    continue
                if ch == '/' and i + 1 < len(line) and line[i+1] == '/':
                    break

            # Strings
            if ch in ('"', "'"):
                if in_str == ch:
                    if i > 0 and line[i-1] == '\\' and (i < 2 or line[i-2] != '\\'):
                        pass
                    else:
                        in_str = None
                elif in_str is None and not in_template:
                    in_str = ch
            elif ch == '`':
                if in_str is None:
                    if in_template:
                        if i > 0 and line[i-1] == '\\' and (i < 2 or line[i-2] != '\\'):
                            pass
                        else:
                            in_template = False
                    else:
                        in_template = True
            elif in_str is None and not in_template:
                if ch in "({[":
                    stack.append((ch, l_idx, i+1))
                elif ch in ")}]":
                    if not stack:
                        issues.append((l_idx, f"Unmatched closing '{ch}'"))
                    else:
                        top, top_l, top_c = stack.pop()
                        if top != pairs[ch]:
                            issues.append((l_idx, f"Mismatched '{ch}', expected '{top}' from line {top_l}:{top_c}"))
            i += 1

    if stack:
        for ch, l, c in stack:
            issues.append((l, f"Unclosed '{ch}' opened at col {c}"))

    # 2. Check for object literal syntax anomalies: e.g. stray single letters or missing commas
    for l_idx, line in enumerate(lines, 1):
        # strip comments
        s = re.sub(r'//.*$', '', line).strip()
        # look for stray single letter like "foo, D bar," or "foo, D,"
        m = re.search(r'\b[a-zA-Z0-9_]+\s*,\s*([A-Za-z])\s+([a-zA-Z0-9_]+)', s)
        if m:
            stray = m.group(1)
            # ignore valid keywords like 'const', 'let', 'var', 'as', 'in', etc.
            if stray not in ('a', 'I'): # even 'a' or 'I' shouldn't appear like "x, a y"
                issues.append((l_idx, f"Possible stray identifier '{stray}' before '{m.group(2)}': {s}"))
        
        # look for double commas
        if ',,' in s and not re.search(r'["\'`].*,,.*["\'`]', s):
            issues.append((l_idx, f"Double comma detected: {s}"))

        # look for trailing colon with no value e.g. "key: ,"
        if re.search(r'\b[a-zA-Z0-9_]+\s*:\s*,', s):
            issues.append((l_idx, f"Colon followed by comma (missing value): {s}"))

        # look for stray closing tag
        if re.search(r'<\s*/\s*>', s):
            pass # fragment closing

    # 3. Check JSX div balance
    text = "".join(lines)
    # Remove strings and comments for tag counting
    cleaned_text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    cleaned_text = re.sub(r'/\*.*?\*/', '', cleaned_text, flags=re.DOTALL)
    # exclude self-closing divs: <div ... />
    non_self_divs = re.sub(r'<div\b[^>]*?/>', '', cleaned_text)
    opens = len(re.findall(r'<div\b[^>]*>', non_self_divs))
    closes = len(re.findall(r'</div>', non_self_divs))
    if opens != closes:
        issues.append((0, f"JSX <div> tag mismatch: {opens} opening vs {closes} closing (diff={opens-closes})"))

    print(f"\n--- Audit complete: {len(issues)} issues found ---")
    for l, msg in issues:
        print(f"Line {l}: {msg}")
    
    return len(issues) == 0

if __name__ == "__main__":
    success = audit_file("frontend/js/app.js")
    sys.exit(0 if success else 1)

