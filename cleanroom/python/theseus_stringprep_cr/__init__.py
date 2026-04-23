"""
theseus_stringprep_cr - Clean-room implementation of stringprep table lookups.
Do NOT import the original stringprep module.
"""

# RFC 3454 Table C.1.1 - Space-like characters
# Per spec simplification: only chr(0x0020) (ASCII space) returns True
def in_table_c11(c: str) -> bool:
    """Return True if c is in RFC 3454 table C.1.1 (space-like characters).
    Simplified: only chr(0x0020) returns True.
    """
    return c == '\x20'


# RFC 3454 Table D.1 - Characters with bidirectional property R or AL
# This is a subset of Unicode characters with right-to-left or Arabic Letter properties.
_TABLE_D1 = frozenset([
    # Hebrew letters and related (R property)
    '\u05BE', '\u05C0', '\u05C3', '\u05C6',
    '\u05D0', '\u05D1', '\u05D2', '\u05D3', '\u05D4', '\u05D5', '\u05D6', '\u05D7',
    '\u05D8', '\u05D9', '\u05DA', '\u05DB', '\u05DC', '\u05DD', '\u05DE', '\u05DF',
    '\u05E0', '\u05E1', '\u05E2', '\u05E3', '\u05E4', '\u05E5', '\u05E6', '\u05E7',
    '\u05E8', '\u05E9', '\u05EA',
    '\u05F0', '\u05F1', '\u05F2', '\u05F3', '\u05F4',
    '\u07C0', '\u07C1', '\u07C2', '\u07C3', '\u07C4', '\u07C5', '\u07C6', '\u07C7',
    '\u07C8', '\u07C9', '\u07CA',
    '\u07CB', '\u07CC', '\u07CD', '\u07CE', '\u07CF',
    '\u07D0', '\u07D1', '\u07D2', '\u07D3', '\u07D4', '\u07D5', '\u07D6', '\u07D7',
    '\u07D8', '\u07D9', '\u07DA', '\u07DB', '\u07DC', '\u07DD', '\u07DE', '\u07DF',
    '\u07E0', '\u07E1', '\u07E2', '\u07E3', '\u07E4', '\u07E5', '\u07E6', '\u07E7',
    '\u07E8', '\u07E9', '\u07EA',
    '\u07F4', '\u07F5', '\u07FA',
    # Arabic letters (AL property)
    '\u0600', '\u0601', '\u0602', '\u0603',
    '\u060B', '\u060D',
    '\u061B', '\u061E', '\u061F',
    '\u0621', '\u0622', '\u0623', '\u0624', '\u0625', '\u0626', '\u0627', '\u0628',
    '\u0629', '\u062A', '\u062B', '\u062C', '\u062D', '\u062E', '\u062F',
    '\u0630', '\u0631', '\u0632', '\u0633', '\u0634', '\u0635', '\u0636', '\u0637',
    '\u0638', '\u0639', '\u063A', '\u063B', '\u063C', '\u063D', '\u063E', '\u063F',
    '\u0640', '\u0641', '\u0642', '\u0643', '\u0644', '\u0645', '\u0646', '\u0647',
    '\u0648', '\u0649', '\u064A',
    '\u066D', '\u066E', '\u066F',
    '\u0671', '\u0672', '\u0673', '\u0674', '\u0675', '\u0676', '\u0677', '\u0678',
    '\u0679', '\u067A', '\u067B', '\u067C', '\u067D', '\u067E', '\u067F',
    '\u0680', '\u0681', '\u0682', '\u0683', '\u0684', '\u0685', '\u0686', '\u0687',
    '\u0688', '\u0689', '\u068A', '\u068B', '\u068C', '\u068D', '\u068E', '\u068F',
    '\u0690', '\u0691', '\u0692', '\u0693', '\u0694', '\u0695', '\u0696', '\u0697',
    '\u0698', '\u0699', '\u069A', '\u069B', '\u069C', '\u069D', '\u069E', '\u069F',
    '\u06A0', '\u06A1', '\u06A2', '\u06A3', '\u06A4', '\u06A5', '\u06A6', '\u06A7',
    '\u06A8', '\u06A9', '\u06AA', '\u06AB', '\u06AC', '\u06AD', '\u06AE', '\u06AF',
    '\u06B0', '\u06B1', '\u06B2', '\u06B3', '\u06B4', '\u06B5', '\u06B6', '\u06B7',
    '\u06B8', '\u06B9', '\u06BA', '\u06BB', '\u06BC', '\u06BD', '\u06BE', '\u06BF',
    '\u06C0', '\u06C1', '\u06C2', '\u06C3', '\u06C4', '\u06C5', '\u06C6', '\u06C7',
    '\u06C8', '\u06C9', '\u06CA', '\u06CB', '\u06CC', '\u06CD', '\u06CE', '\u06CF',
    '\u06D0', '\u06D1', '\u06D2', '\u06D3', '\u06D4', '\u06D5',
    '\u06E5', '\u06E6', '\u06EE', '\u06EF',
    '\u06FA', '\u06FB', '\u06FC', '\u06FD', '\u06FE', '\u06FF',
    '\u0700', '\u0701', '\u0702', '\u0703', '\u0704', '\u0705', '\u0706', '\u0707',
    '\u0708', '\u0709', '\u070A', '\u070B', '\u070C', '\u070D',
    '\u070F',
    '\u0710',
    '\u0712', '\u0713', '\u0714', '\u0715', '\u0716', '\u0717', '\u0718', '\u0719',
    '\u071A', '\u071B', '\u071C', '\u071D', '\u071E', '\u071F',
    '\u0720', '\u0721', '\u0722', '\u0723', '\u0724', '\u0725', '\u0726', '\u0727',
    '\u0728', '\u0729', '\u072A', '\u072B', '\u072C', '\u072D', '\u072E', '\u072F',
    '\u074D', '\u074E', '\u074F',
    '\u0750', '\u0751', '\u0752', '\u0753', '\u0754', '\u0755', '\u0756', '\u0757',
    '\u0758', '\u0759', '\u075A', '\u075B', '\u075C', '\u075D', '\u075E', '\u075F',
    '\u0760', '\u0761', '\u0762', '\u0763', '\u0764', '\u0765', '\u0766', '\u0767',
    '\u0768', '\u0769', '\u076A', '\u076B', '\u076C', '\u076D',
])


def in_table_d1(c: str) -> bool:
    """Return True if c has bidirectional property R or AL (RFC 3454 Table D.1)."""
    return c in _TABLE_D1


def map_table_b2(c: str) -> str:
    """Case folding map for c per RFC 3454 Table B.2.
    Simplified: lowercase ASCII letters, else return c unchanged.
    """
    cp = ord(c)
    # ASCII uppercase A-Z -> lowercase a-z
    if 0x0041 <= cp <= 0x005A:
        return chr(cp + 0x20)
    return c


# --- Test helpers referenced in invariants ---

def stringprep_space() -> bool:
    """in_table_c11(' ') == True"""
    return in_table_c11(' ')


def stringprep_not_space() -> bool:
    """in_table_c11('A') == False"""
    return in_table_c11('A')


def stringprep_map_b2() -> str:
    """map_table_b2('A') == 'a'"""
    return map_table_b2('A')


__all__ = [
    'in_table_c11',
    'in_table_d1',
    'map_table_b2',
    'stringprep_space',
    'stringprep_not_space',
    'stringprep_map_b2',
]