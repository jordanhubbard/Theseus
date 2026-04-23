"""
theseus_this_cr — Clean-room this module.
No import of the standard `this` module.
The Zen of Python, encoded with a ROT-13 cipher.
"""

# The encoded Zen of Python (ROT-13 of the actual text)
s = """Gur Mra bs Clguba, ol Gvz Crgref

Ornhgvshy vf orggre guna htyl.
Rkcyvpvg vf orggre guna vzcyvpvg.
Fvzcyr vf orggre guna pbzcyrk.
Pbzcyrk vf orggre guna pbzcyvpngrq.
Syng vf orggre guna arfgrq.
Fcnefr vf orggre guna qrafr.
Ernqnovyvgl pbhagf.
Fcrpvny pnfrf nera'g fcrpvny rabhtu gb oernx gur ehyrf.
Nygubhtu cenpgvpnyvgl orngf chevgl.
Reebef fubhyq arire cnff fvyragyl.
Hayrff rkcyvpvgyl fvyraprq.
Va gur snpr bs nzovthvgl, ershfr gur grzcgngvba gb thrff.
Gurer fubhyq or bar-- naq cersrenoyl bayl bar --boivbhf jnl gb qb vg.
Nygubhtu gung jnl znl abg or boivbhf ng svefg hayrff lbh'er Qhgpu.
Abj vf orggre guna arire.
Nygubhtu arire vf bsgra orggre guna *evtug* abj.
Vs gur vzcyrzragngvba vf uneq gb rkcynva, vg'f n onq vqrn.
Vs gur vzcyrzragngvba vf rnfl gb rkcynva, vg znl or n tbbq vqrn.
Anzrfcnprf ner bar ubaxvat terng vqrn -- yrg'f qb zber bs gubfr!"""

# Build the ROT-13 decode table
d = {}
for c in (65, 97):
    for i in range(26):
        d[chr(c + i)] = chr(c + (i + 13) % 26)


def _decode(text):
    """Decode ROT-13 encoded text."""
    return ''.join(d.get(c, c) for c in text)


# The decoded text (but we don't print it on import like the original does)
_decoded = _decode(s)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def this2_zen():
    """s attribute contains the encoded Zen of Python; returns True."""
    return (isinstance(s, str) and
            'Mra' in s and
            'Clguba' in s)


def this2_decode():
    """The decoded text contains 'Beautiful is better than ugly'; returns True."""
    decoded = _decode(s)
    return ('Beautiful is better than ugly' in decoded and
            'Zen of Python' in decoded)


def this2_d():
    """d dict maps encoded to decoded characters; returns True."""
    return (isinstance(d, dict) and
            d.get('G') == 'T' and
            d.get('a') == 'n' and
            len(d) == 52)


__all__ = [
    's', 'd',
    'this2_zen', 'this2_decode', 'this2_d',
]
