"""Clean-room subset of html.entities."""

name2codepoint = {
    "quot": 34,
    "amp": 38,
    "lt": 60,
    "gt": 62,
    "nbsp": 160,
    "copy": 169,
    "reg": 174,
    "Aacute": 193,
    "aacute": 225,
}

codepoint2name = {
    34: "quot",
    38: "amp",
    60: "lt",
    62: "gt",
    160: "nbsp",
    169: "copy",
    174: "reg",
    193: "Aacute",
    225: "aacute",
}

entitydefs = {
    "quot": '"',
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "nbsp": "\xa0",
    "copy": "\xa9",
    "reg": "\xae",
    "Aacute": "\xc1",
    "aacute": "\xe1",
}

html5 = {
    "quot;": '"',
    "amp;": "&",
    "amp": "&",
    "lt;": "<",
    "lt": "<",
    "gt;": ">",
    "gt": ">",
    "nbsp;": "\xa0",
    "copy;": "\xa9",
    "reg;": "\xae",
    "Aacute;": "\xc1",
    "aacute;": "\xe1",
}


def html_entities_amp_codepoint():
    return name2codepoint["amp"]


def html_entities_gt_html5():
    return html5["gt;"]


def html_entities_nbsp_entitydef():
    return ord(entitydefs["nbsp"])


def html_entities_dicts():
    return all(
        isinstance(value, dict)
        for value in (html5, name2codepoint, codepoint2name, entitydefs)
    )
