import sys

def verify_js_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    lines = code.splitlines()
    print(f"Total lines in {filepath}: {len(lines)}")

    stack = []
    pairs = {")": "(", "}": "{", "]": "["}
    in_template = False
    in_str = None
    in_comment = False

    for l_idx, line in enumerate(lines, 1):
        i = 0
        while i < len(line):
            ch = line[i]
            if in_comment:
                if ch == "*" and i + 1 < len(line) and line[i+1] == "/":
                    in_comment = False
                    i += 1
                i += 1
                continue
            if not in_str and not in_template:
                if ch == "/" and i + 1 < len(line) and line[i+1] == "*":
                    in_comment = True
                    i += 2
                    continue
                if ch == "/" and i + 1 < len(line) and line[i+1] == "/":
                    break
            if ch in ('"', "'"):
                if in_str == ch:
                    if i > 0 and line[i-1] == "\\" and (i < 2 or line[i-2] != "\\"):
                        pass
                    else:
                        in_str = None
                elif in_str is None and not in_template:
                    in_str = ch
            elif ch == "`":
                if in_str is None:
                    in_template = not in_template
            elif in_str is None and not in_template:
                if ch in "({[":
                    stack.append((ch, l_idx, i+1))
                elif ch in ")}]":
                    if not stack:
                        print(f"ERROR: Unmatched {ch} at line {l_idx}:{i+1}")
                        return False
                    top, top_l, top_c = stack.pop()
                    if top != pairs[ch]:
                        print(f"ERROR: Mismatch {ch} at line {l_idx}:{i+1}, expected {top} from line {top_l}:{top_c}")
                        return False
            i += 1

    if stack:
        print(f"ERROR: Unclosed brackets: {len(stack)}")
        for item in stack[-5:]:
            print(f"  Unclosed {item[0]} from line {item[1]}:{item[2]}")
        return False

    print("Bracket syntax balance: 100% CLEAN AND VALID!")
    return True

if __name__ == "__main__":
    success = verify_js_file("frontend/js/app.js")
    sys.exit(0 if success else 1)
