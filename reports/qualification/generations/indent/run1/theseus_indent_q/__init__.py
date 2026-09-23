# generation A indent scan

def indent(text, prefix):
    def should_indent(line):
        return line.strip()

    return ''.join(
        prefix + line if should_indent(line) else line
        for line in text.splitlines(True)
    )
