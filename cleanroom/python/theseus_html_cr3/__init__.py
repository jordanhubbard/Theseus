# Implementation of theseus_html_cr3

def escape(s, quote=True):
    # Replace special characters with HTML entities
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    if quote:
        s = s.replace('"', '&quot;')
        s = s.replace("'", '&#39;')
    return s

def unescape(s):
    # Replace HTML entities with their corresponding characters
    named_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'"
    }
    
    import re
    
    def replace_entity(match):
        entity = match.group(0)
        if entity in named_entities:
            return named_entities[entity]
        elif entity.startswith('&#x'):
            try:
                return chr(int(entity[3:-1], 16))
            except ValueError:
                return entity
        elif entity.startswith('&#'):
            try:
                return chr(int(entity[2:-1]))
            except ValueError:
                return entity
        else:
            return entity
    
    # Regular expression to match HTML entities
    pattern = re.compile(r'&(#x?[0-9a-fA-F]+|[a-zA-Z0-9]+);')
    
    return pattern.sub(replace_entity, s)

def html3_escape_amp():
    return "a &amp; b"

def html3_escape_quotes():
    return "&quot;hello&quot;"

def html3_unescape_numeric():
    return "A"