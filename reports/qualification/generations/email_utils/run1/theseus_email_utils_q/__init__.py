# generation A address scan

def parseaddr(addr):
    if isinstance(addr, list):
        addr = addr[0]
    if not isinstance(addr, str):
        return ('', '')
    def _quote_str(s):
        return s.replace('\\', '\\\\').replace('"', '\\"')
    def _iter_escaped_chars(s):
        pos = 0
        escape = False
        for pos, ch in enumerate(s):
            if escape:
                yield (pos, '\\' + ch)
                escape = False
            elif ch == '\\':
                escape = True
            else:
                yield (pos, ch)
        if escape:
            yield (pos, '\\')
    def _strip_quoted_realnames(s):
        if '"' not in s:
            return s
        start = 0
        open_pos = None
        result = []
        for pos, ch in _iter_escaped_chars(s):
            if ch == '"':
                if open_pos is None:
                    open_pos = pos
                else:
                    if start != open_pos:
                        result.append(s[start:open_pos])
                    start = pos + 1
                    open_pos = None
        if start < len(s):
            result.append(s[start:])
        return ''.join(result)
    def _check_parenthesis(s):
        s = _strip_quoted_realnames(s)
        opens = 0
        for pos, ch in _iter_escaped_chars(s):
            if ch == '(':
                opens += 1
            elif ch == ')':
                opens -= 1
                if opens < 0:
                    return False
        return opens == 0
    def _pre_parse_validation(s):
        if not _check_parenthesis(s):
            return "('', '')"
        return s
    def _post_parse_validation(tups):
        out = []
        for v in tups:
            if '[' in v[1]:
                out.append(('', ''))
            else:
                out.append(v)
        return out
    def _address_list(field):
        EMPTYSTRING = ''
        SPACE = ' '
        st = {
            'field': field,
            'pos': 0,
            'commentlist': [],
            'specials': '()<>@,:;."[]',
            'LWS': ' \t',
            'CR': '\r\n',
        }
        st['FWS'] = st['LWS'] + st['CR']
        st['atomends'] = st['specials'] + st['LWS'] + st['CR']
        st['phraseends'] = st['atomends'].replace('.', '')

        def gotonext():
            wslist = []
            while st['pos'] < len(st['field']):
                if st['field'][st['pos']] in st['LWS'] + '\n\r':
                    if st['field'][st['pos']] not in '\n\r':
                        wslist.append(st['field'][st['pos']])
                    st['pos'] += 1
                elif st['field'][st['pos']] == '(':
                    st['commentlist'].append(getcomment())
                else:
                    break
            return EMPTYSTRING.join(wslist)

        def getcomment():
            return getdelimited('(', ')\r', True)

        def getdelimited(beginchar, endchars, allowcomments=True):
            if st['field'][st['pos']] != beginchar:
                return ''
            slist = ['']
            quote = False
            st['pos'] += 1
            while st['pos'] < len(st['field']):
                if quote:
                    slist.append(st['field'][st['pos']])
                    quote = False
                elif st['field'][st['pos']] in endchars:
                    st['pos'] += 1
                    break
                elif allowcomments and st['field'][st['pos']] == '(':
                    slist.append(getcomment())
                    continue
                elif st['field'][st['pos']] == '\\':
                    quote = True
                else:
                    slist.append(st['field'][st['pos']])
                st['pos'] += 1
            return EMPTYSTRING.join(slist)

        def getquote():
            return getdelimited('"', '"\r', False)

        def getatom(atomends=None):
            atomlist = ['']
            if atomends is None:
                atomends = st['atomends']
            while st['pos'] < len(st['field']):
                if st['field'][st['pos']] in atomends:
                    break
                atomlist.append(st['field'][st['pos']])
                st['pos'] += 1
            return EMPTYSTRING.join(atomlist)

        def getdomainliteral():
            return '[%s]' % getdelimited('[', ']\r', False)

        def getdomain():
            sdlist = []
            while st['pos'] < len(st['field']):
                if st['field'][st['pos']] in st['LWS']:
                    st['pos'] += 1
                elif st['field'][st['pos']] == '(':
                    st['commentlist'].append(getcomment())
                elif st['field'][st['pos']] == '[':
                    sdlist.append(getdomainliteral())
                elif st['field'][st['pos']] == '.':
                    st['pos'] += 1
                    sdlist.append('.')
                elif st['field'][st['pos']] == '@':
                    return EMPTYSTRING
                elif st['field'][st['pos']] in st['atomends']:
                    break
                else:
                    sdlist.append(getatom())
            return EMPTYSTRING.join(sdlist)

        def getaddrspec():
            aslist = []
            gotonext()
            while st['pos'] < len(st['field']):
                preserve_ws = True
                if st['field'][st['pos']] == '.':
                    if aslist and not aslist[-1].strip():
                        aslist.pop()
                    aslist.append('.')
                    st['pos'] += 1
                    preserve_ws = False
                elif st['field'][st['pos']] == '"':
                    aslist.append('"%s"' % _quote_str(getquote()))
                elif st['field'][st['pos']] in st['atomends']:
                    if aslist and not aslist[-1].strip():
                        aslist.pop()
                    break
                else:
                    aslist.append(getatom())
                ws = gotonext()
                if preserve_ws and ws:
                    aslist.append(ws)
            if st['pos'] >= len(st['field']) or st['field'][st['pos']] != '@':
                return EMPTYSTRING.join(aslist)
            aslist.append('@')
            st['pos'] += 1
            gotonext()
            domain = getdomain()
            if not domain:
                return EMPTYSTRING
            return EMPTYSTRING.join(aslist) + domain

        def getrouteaddr():
            if st['field'][st['pos']] != '<':
                return
            expectroute = False
            st['pos'] += 1
            gotonext()
            adlist = ''
            while st['pos'] < len(st['field']):
                if expectroute:
                    getdomain()
                    expectroute = False
                elif st['field'][st['pos']] == '>':
                    st['pos'] += 1
                    break
                elif st['field'][st['pos']] == '@':
                    st['pos'] += 1
                    expectroute = True
                elif st['field'][st['pos']] == ':':
                    st['pos'] += 1
                else:
                    adlist = getaddrspec()
                    st['pos'] += 1
                    break
                gotonext()
            return adlist

        def getphraselist():
            plist = []
            while st['pos'] < len(st['field']):
                if st['field'][st['pos']] in st['FWS']:
                    st['pos'] += 1
                elif st['field'][st['pos']] == '"':
                    plist.append(getquote())
                elif st['field'][st['pos']] == '(':
                    st['commentlist'].append(getcomment())
                elif st['field'][st['pos']] in st['phraseends']:
                    break
                else:
                    plist.append(getatom(st['phraseends']))
            return plist

        def getaddress():
            st['commentlist'] = []
            gotonext()
            oldpos = st['pos']
            oldcl = st['commentlist'][:]
            plist = getphraselist()
            gotonext()
            returnlist = []
            if st['pos'] >= len(st['field']):
                if plist:
                    returnlist = [(SPACE.join(st['commentlist']), plist[0])]
            elif st['field'][st['pos']] in '.@':
                st['pos'] = oldpos
                st['commentlist'] = oldcl
                addrspec = getaddrspec()
                returnlist = [(SPACE.join(st['commentlist']), addrspec)]
            elif st['field'][st['pos']] == ':':
                returnlist = []
                fieldlen = len(st['field'])
                st['pos'] += 1
                while st['pos'] < len(st['field']):
                    gotonext()
                    if st['pos'] < fieldlen and st['field'][st['pos']] == ';':
                        st['pos'] += 1
                        break
                    returnlist = returnlist + getaddress()
            elif st['field'][st['pos']] == '<':
                routeaddr = getrouteaddr()
                if st['commentlist']:
                    returnlist = [(SPACE.join(plist) + ' (' + ' '.join(st['commentlist']) + ')', routeaddr)]
                else:
                    returnlist = [(SPACE.join(plist), routeaddr)]
            else:
                if plist:
                    returnlist = [(SPACE.join(st['commentlist']), plist[0])]
                elif st['pos'] < len(st['field']) and st['field'][st['pos']] in st['specials']:
                    st['pos'] += 1
            gotonext()
            if st['pos'] < len(st['field']) and st['field'][st['pos']] == ',':
                st['pos'] += 1
            return returnlist

        def getaddrlist():
            result = []
            while st['pos'] < len(st['field']):
                ad = getaddress()
                if ad:
                    result += ad
                else:
                    result.append(('', ''))
            return result

        if not field:
            return []
        return getaddrlist()
    addr = _pre_parse_validation(addr)
    addrs = _address_list(addr)
    addrs = _post_parse_validation(addrs)
    if not addrs or len(addrs) > 1:
        return ('', '')
    return addrs[0]
