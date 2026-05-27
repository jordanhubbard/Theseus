"""Clean-room subset of mailcap file matching."""


def getcaps():
    return {}


def lookup(caps, MIMEtype, key=None):
    entries = []
    mime = MIMEtype.lower()
    major = mime.split("/", 1)[0] + "/*" if "/" in mime else mime
    for candidate in (mime, major):
        for entry in caps.get(candidate, []):
            if key is None or key in entry:
                entries.append(entry)
    return entries


def findmatch(caps, MIMEtype, key="view", filename="/dev/null", plist=[]):
    params = _plist_dict(plist)
    for entry in lookup(caps, MIMEtype, key):
        command = entry.get(key)
        if command is None:
            continue
        return (_substitute(command, filename, params), entry)
    return (None, None)


def _plist_dict(plist):
    params = {}
    for item in plist or []:
        if "=" in item:
            name, value = item.split("=", 1)
            params[name] = value
    return params


def _substitute(command, filename, params):
    result = []
    i = 0
    while i < len(command):
        char = command[i]
        if char != "%":
            result.append(char)
            i += 1
            continue
        if i + 1 >= len(command):
            result.append(char)
            i += 1
            continue
        marker = command[i + 1]
        if marker == "s":
            result.append(filename)
            i += 2
        elif marker == "%":
            result.append("%")
            i += 2
        elif marker == "{" and "}" in command[i + 2:]:
            end = command.index("}", i + 2)
            name = command[i + 2:end]
            result.append(params.get(name, ""))
            i = end + 1
        else:
            result.append(char)
            i += 1
    return "".join(result)


def mailcap_getcaps_type():
    return isinstance(getcaps(), dict)


def mailcap_findmatch_doc_example():
    caps = {"video/mpeg": [{"view": "xmpeg %s"}]}
    return findmatch(caps, "video/mpeg", filename="tmp1223")[0]


def mailcap_findmatch_none():
    return findmatch({}, "text/plain") == (None, None)


def mailcap_findmatch_params():
    caps = {"message/partial": [{"view": "showpartial %{id} %{number} %{total}"}]}
    plist = ["id=1", "number=2", "total=3"]
    return findmatch(caps, "message/partial", plist=plist)[0]
