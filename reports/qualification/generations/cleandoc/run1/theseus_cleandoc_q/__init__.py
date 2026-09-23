# generation A cleandoc scan

def cleandoc(text):
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    margin = 2147483647
    for line in lines[1:]:
        content = line.lstrip()
        if content:
            indent = len(line) - len(content)
            if indent < margin:
                margin = indent
    lines[0] = lines[0].lstrip()
    if margin < 2147483647:
        for i in range(1, len(lines)):
            lines[i] = lines[i][margin:]
    return "\n".join(lines)
