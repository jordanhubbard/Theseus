"""
theseus_unicodedata_cr2 - Clean-room Unicode data utilities.
No import of unicodedata or any third-party library.
"""

# Minimal lookup table for Unicode character properties.
# Format: codepoint -> (name, bidirectional_class, decomposition, category)
_UNICODE_DATA = {
    # Basic Latin letters A-Z
    0x0041: ('LATIN CAPITAL LETTER A', 'L', '', 'Lu'),
    0x0042: ('LATIN CAPITAL LETTER B', 'L', '', 'Lu'),
    0x0043: ('LATIN CAPITAL LETTER C', 'L', '', 'Lu'),
    0x0044: ('LATIN CAPITAL LETTER D', 'L', '', 'Lu'),
    0x0045: ('LATIN CAPITAL LETTER E', 'L', '', 'Lu'),
    0x0046: ('LATIN CAPITAL LETTER F', 'L', '', 'Lu'),
    0x0047: ('LATIN CAPITAL LETTER G', 'L', '', 'Lu'),
    0x0048: ('LATIN CAPITAL LETTER H', 'L', '', 'Lu'),
    0x0049: ('LATIN CAPITAL LETTER I', 'L', '', 'Lu'),
    0x004A: ('LATIN CAPITAL LETTER J', 'L', '', 'Lu'),
    0x004B: ('LATIN CAPITAL LETTER K', 'L', '', 'Lu'),
    0x004C: ('LATIN CAPITAL LETTER L', 'L', '', 'Lu'),
    0x004D: ('LATIN CAPITAL LETTER M', 'L', '', 'Lu'),
    0x004E: ('LATIN CAPITAL LETTER N', 'L', '', 'Lu'),
    0x004F: ('LATIN CAPITAL LETTER O', 'L', '', 'Lu'),
    0x0050: ('LATIN CAPITAL LETTER P', 'L', '', 'Lu'),
    0x0051: ('LATIN CAPITAL LETTER Q', 'L', '', 'Lu'),
    0x0052: ('LATIN CAPITAL LETTER R', 'L', '', 'Lu'),
    0x0053: ('LATIN CAPITAL LETTER S', 'L', '', 'Lu'),
    0x0054: ('LATIN CAPITAL LETTER T', 'L', '', 'Lu'),
    0x0055: ('LATIN CAPITAL LETTER U', 'L', '', 'Lu'),
    0x0056: ('LATIN CAPITAL LETTER V', 'L', '', 'Lu'),
    0x0057: ('LATIN CAPITAL LETTER W', 'L', '', 'Lu'),
    0x0058: ('LATIN CAPITAL LETTER X', 'L', '', 'Lu'),
    0x0059: ('LATIN CAPITAL LETTER Y', 'L', '', 'Lu'),
    0x005A: ('LATIN CAPITAL LETTER Z', 'L', '', 'Lu'),
    # Basic Latin lowercase letters a-z
    0x0061: ('LATIN SMALL LETTER A', 'L', '', 'Ll'),
    0x0062: ('LATIN SMALL LETTER B', 'L', '', 'Ll'),
    0x0063: ('LATIN SMALL LETTER C', 'L', '', 'Ll'),
    0x0064: ('LATIN SMALL LETTER D', 'L', '', 'Ll'),
    0x0065: ('LATIN SMALL LETTER E', 'L', '', 'Ll'),
    0x0066: ('LATIN SMALL LETTER F', 'L', '', 'Ll'),
    0x0067: ('LATIN SMALL LETTER G', 'L', '', 'Ll'),
    0x0068: ('LATIN SMALL LETTER H', 'L', '', 'Ll'),
    0x0069: ('LATIN SMALL LETTER I', 'L', '', 'Ll'),
    0x006A: ('LATIN SMALL LETTER J', 'L', '', 'Ll'),
    0x006B: ('LATIN SMALL LETTER K', 'L', '', 'Ll'),
    0x006C: ('LATIN SMALL LETTER L', 'L', '', 'Ll'),
    0x006D: ('LATIN SMALL LETTER M', 'L', '', 'Ll'),
    0x006E: ('LATIN SMALL LETTER N', 'L', '', 'Ll'),
    0x006F: ('LATIN SMALL LETTER O', 'L', '', 'Ll'),
    0x0070: ('LATIN SMALL LETTER P', 'L', '', 'Ll'),
    0x0071: ('LATIN SMALL LETTER Q', 'L', '', 'Ll'),
    0x0072: ('LATIN SMALL LETTER R', 'L', '', 'Ll'),
    0x0073: ('LATIN SMALL LETTER S', 'L', '', 'Ll'),
    0x0074: ('LATIN SMALL LETTER T', 'L', '', 'Ll'),
    0x0075: ('LATIN SMALL LETTER U', 'L', '', 'Ll'),
    0x0076: ('LATIN SMALL LETTER V', 'L', '', 'Ll'),
    0x0077: ('LATIN SMALL LETTER W', 'L', '', 'Ll'),
    0x0078: ('LATIN SMALL LETTER X', 'L', '', 'Ll'),
    0x0079: ('LATIN SMALL LETTER Y', 'L', '', 'Ll'),
    0x007A: ('LATIN SMALL LETTER Z', 'L', '', 'Ll'),
    # Digits 0-9
    0x0030: ('DIGIT ZERO', 'EN', '', 'Nd'),
    0x0031: ('DIGIT ONE', 'EN', '', 'Nd'),
    0x0032: ('DIGIT TWO', 'EN', '', 'Nd'),
    0x0033: ('DIGIT THREE', 'EN', '', 'Nd'),
    0x0034: ('DIGIT FOUR', 'EN', '', 'Nd'),
    0x0035: ('DIGIT FIVE', 'EN', '', 'Nd'),
    0x0036: ('DIGIT SIX', 'EN', '', 'Nd'),
    0x0037: ('DIGIT SEVEN', 'EN', '', 'Nd'),
    0x0038: ('DIGIT EIGHT', 'EN', '', 'Nd'),
    0x0039: ('DIGIT NINE', 'EN', '', 'Nd'),
    # Space and common punctuation
    0x0020: ('SPACE', 'WS', '', 'Zs'),
    0x0021: ('EXCLAMATION MARK', 'ON', '', 'Po'),
    0x0022: ('QUOTATION MARK', 'ON', '', 'Po'),
    0x0023: ('NUMBER SIGN', 'ET', '', 'Po'),
    0x0024: ('DOLLAR SIGN', 'ET', '', 'Sc'),
    0x0025: ('PERCENT SIGN', 'ET', '', 'Po'),
    0x0026: ('AMPERSAND', 'ON', '', 'Po'),
    0x0027: ('APOSTROPHE', 'ON', '', 'Po'),
    0x0028: ('LEFT PARENTHESIS', 'ON', '', 'Ps'),
    0x0029: ('RIGHT PARENTHESIS', 'ON', '', 'Pe'),
    0x002A: ('ASTERISK', 'ON', '', 'Po'),
    0x002B: ('PLUS SIGN', 'ES', '', 'Sm'),
    0x002C: ('COMMA', 'CS', '', 'Po'),
    0x002D: ('HYPHEN-MINUS', 'ES', '', 'Pd'),
    0x002E: ('FULL STOP', 'CS', '', 'Po'),
    0x002F: ('SOLIDUS', 'CS', '', 'Po'),
    0x003A: ('COLON', 'CS', '', 'Po'),
    0x003B: ('SEMICOLON', 'ON', '', 'Po'),
    0x003C: ('LESS-THAN SIGN', 'ON', '', 'Sm'),
    0x003D: ('EQUALS SIGN', 'ON', '', 'Sm'),
    0x003E: ('GREATER-THAN SIGN', 'ON', '', 'Sm'),
    0x003F: ('QUESTION MARK', 'ON', '', 'Po'),
    0x0040: ('COMMERCIAL AT', 'ON', '', 'Po'),
    0x005B: ('LEFT SQUARE BRACKET', 'ON', '', 'Ps'),
    0x005C: ('REVERSE SOLIDUS', 'ON', '', 'Po'),
    0x005D: ('RIGHT SQUARE BRACKET', 'ON', '', 'Pe'),
    0x005E: ('CIRCUMFLEX ACCENT', 'ON', '', 'Sk'),
    0x005F: ('LOW LINE', 'ON', '', 'Pc'),
    0x0060: ('GRAVE ACCENT', 'ON', '', 'Sk'),
    0x007B: ('LEFT CURLY BRACKET', 'ON', '', 'Ps'),
    0x007C: ('VERTICAL LINE', 'ON', '', 'Sm'),
    0x007D: ('RIGHT CURLY BRACKET', 'ON', '', 'Pe'),
    0x007E: ('TILDE', 'ON', '', 'Sm'),
    # Control characters
    0x0000: ('NULL', 'BN', '', 'Cc'),
    0x0001: ('START OF HEADING', 'BN', '', 'Cc'),
    0x0002: ('START OF TEXT', 'BN', '', 'Cc'),
    0x0003: ('END OF TEXT', 'BN', '', 'Cc'),
    0x0004: ('END OF TRANSMISSION', 'BN', '', 'Cc'),
    0x0005: ('ENQUIRY', 'BN', '', 'Cc'),
    0x0006: ('ACKNOWLEDGE', 'BN', '', 'Cc'),
    0x0007: ('ALERT', 'BN', '', 'Cc'),
    0x0008: ('BACKSPACE', 'BN', '', 'Cc'),
    0x0009: ('CHARACTER TABULATION', 'S', '', 'Cc'),
    0x000A: ('LINE FEED (LF)', 'B', '', 'Cc'),
    0x000B: ('LINE TABULATION', 'S', '', 'Cc'),
    0x000C: ('FORM FEED (FF)', 'WS', '', 'Cc'),
    0x000D: ('CARRIAGE RETURN (CR)', 'B', '', 'Cc'),
    0x000E: ('SHIFT OUT', 'BN', '', 'Cc'),
    0x000F: ('SHIFT IN', 'BN', '', 'Cc'),
    0x001A: ('SUBSTITUTE', 'BN', '', 'Cc'),
    0x001B: ('ESCAPE', 'BN', '', 'Cc'),
    0x001C: ('INFORMATION SEPARATOR FOUR', 'B', '', 'Cc'),
    0x001D: ('INFORMATION SEPARATOR THREE', 'B', '', 'Cc'),
    0x001E: ('INFORMATION SEPARATOR TWO', 'B', '', 'Cc'),
    0x001F: ('INFORMATION SEPARATOR ONE', 'S', '', 'Cc'),
    0x007F: ('DELETE', 'BN', '', 'Cc'),
    # Some Latin extended characters with decompositions
    0x00C0: ('LATIN CAPITAL LETTER A WITH GRAVE', 'L', '0041 0300', 'Lu'),
    0x00C1: ('LATIN CAPITAL LETTER A WITH ACUTE', 'L', '0041 0301', 'Lu'),
    0x00C2: ('LATIN CAPITAL LETTER A WITH CIRCUMFLEX', 'L', '0041 0302', 'Lu'),
    0x00C3: ('LATIN CAPITAL LETTER A WITH TILDE', 'L', '0041 0303', 'Lu'),
    0x00C4: ('LATIN CAPITAL LETTER A WITH DIAERESIS', 'L', '0041 0308', 'Lu'),
    0x00C5: ('LATIN CAPITAL LETTER A WITH RING ABOVE', 'L', '0041 030A', 'Lu'),
    0x00C6: ('LATIN CAPITAL LETTER AE', 'L', '', 'Lu'),
    0x00C7: ('LATIN CAPITAL LETTER C WITH CEDILLA', 'L', '0043 0327', 'Lu'),
    0x00C8: ('LATIN CAPITAL LETTER E WITH GRAVE', 'L', '0045 0300', 'Lu'),
    0x00C9: ('LATIN CAPITAL LETTER E WITH ACUTE', 'L', '0045 0301', 'Lu'),
    0x00CA: ('LATIN CAPITAL LETTER E WITH CIRCUMFLEX', 'L', '0045 0302', 'Lu'),
    0x00CB: ('LATIN CAPITAL LETTER E WITH DIAERESIS', 'L', '0045 0308', 'Lu'),
    0x00CC: ('LATIN CAPITAL LETTER I WITH GRAVE', 'L', '0049 0300', 'Lu'),
    0x00CD: ('LATIN CAPITAL LETTER I WITH ACUTE', 'L', '0049 0301', 'Lu'),
    0x00CE: ('LATIN CAPITAL LETTER I WITH CIRCUMFLEX', 'L', '0049 0302', 'Lu'),
    0x00CF: ('LATIN CAPITAL LETTER I WITH DIAERESIS', 'L', '0049 0308', 'Lu'),
    0x00D0: ('LATIN CAPITAL LETTER ETH', 'L', '', 'Lu'),
    0x00D1: ('LATIN CAPITAL LETTER N WITH TILDE', 'L', '004E 0303', 'Lu'),
    0x00D2: ('LATIN CAPITAL LETTER O WITH GRAVE', 'L', '004F 0300', 'Lu'),
    0x00D3: ('LATIN CAPITAL LETTER O WITH ACUTE', 'L', '004F 0301', 'Lu'),
    0x00D4: ('LATIN CAPITAL LETTER O WITH CIRCUMFLEX', 'L', '004F 0302', 'Lu'),
    0x00D5: ('LATIN CAPITAL LETTER O WITH TILDE', 'L', '004F 0303', 'Lu'),
    0x00D6: ('LATIN CAPITAL LETTER O WITH DIAERESIS', 'L', '004F 0308', 'Lu'),
    0x00D8: ('LATIN CAPITAL LETTER O WITH STROKE', 'L', '', 'Lu'),
    0x00D9: ('LATIN CAPITAL LETTER U WITH GRAVE', 'L', '0055 0300', 'Lu'),
    0x00DA: ('LATIN CAPITAL LETTER U WITH ACUTE', 'L', '0055 0301', 'Lu'),
    0x00DB: ('LATIN CAPITAL LETTER U WITH CIRCUMFLEX', 'L', '0055 0302', 'Lu'),
    0x00DC: ('LATIN CAPITAL LETTER U WITH DIAERESIS', 'L', '0055 0308', 'Lu'),
    0x00DD: ('LATIN CAPITAL LETTER Y WITH ACUTE', 'L', '0059 0301', 'Lu'),
    0x00DE: ('LATIN CAPITAL LETTER THORN', 'L', '', 'Lu'),
    0x00DF: ('LATIN SMALL LETTER SHARP S', 'L', '', 'Ll'),
    0x00E0: ('LATIN SMALL LETTER A WITH GRAVE', 'L', '0061 0300', 'Ll'),
    0x00E1: ('LATIN SMALL LETTER A WITH ACUTE', 'L', '0061 0301', 'Ll'),
    0x00E2: ('LATIN SMALL LETTER A WITH CIRCUMFLEX', 'L', '0061 0302', 'Ll'),
    0x00E3: ('LATIN SMALL LETTER A WITH TILDE', 'L', '0061 0303', 'Ll'),
    0x00E4: ('LATIN SMALL LETTER A WITH DIAERESIS', 'L', '0061 0308', 'Ll'),
    0x00E5: ('LATIN SMALL LETTER A WITH RING ABOVE', 'L', '0061 030A', 'Ll'),
    0x00E6: ('LATIN SMALL LETTER AE', 'L', '', 'Ll'),
    0x00E7: ('LATIN SMALL LETTER C WITH CEDILLA', 'L', '0063 0327', 'Ll'),
    0x00E8: ('LATIN SMALL LETTER E WITH GRAVE', 'L', '0065 0300', 'Ll'),
    0x00E9: ('LATIN SMALL LETTER E WITH ACUTE', 'L', '0065 0301', 'Ll'),
    0x00EA: ('LATIN SMALL LETTER E WITH CIRCUMFLEX', 'L', '0065 0302', 'Ll'),
    0x00EB: ('LATIN SMALL LETTER E WITH DIAERESIS', 'L', '0065 0308', 'Ll'),
    0x00EC: ('LATIN SMALL LETTER I WITH GRAVE', 'L', '0069 0300', 'Ll'),
    0x00ED: ('LATIN SMALL LETTER I WITH ACUTE', 'L', '0069 0301', 'Ll'),
    0x00EE: ('LATIN SMALL LETTER I WITH CIRCUMFLEX', 'L', '0069 0302', 'Ll'),
    0x00EF: ('LATIN SMALL LETTER I WITH DIAERESIS', 'L', '0069 0308', 'Ll'),
    0x00F0: ('LATIN SMALL LETTER ETH', 'L', '', 'Ll'),
    0x00F1: ('LATIN SMALL LETTER N WITH TILDE', 'L', '006E 0303', 'Ll'),
    0x00F2: ('LATIN SMALL LETTER O WITH GRAVE', 'L', '006F 0300', 'Ll'),
    0x00F3: ('LATIN SMALL LETTER O WITH ACUTE', 'L', '006F 0301', 'Ll'),
    0x00F4: ('LATIN SMALL LETTER O WITH CIRCUMFLEX', 'L', '006F 0302', 'Ll'),
    0x00F5: ('LATIN SMALL LETTER O WITH TILDE', 'L', '006F 0303', 'Ll'),
    0x00F6: ('LATIN SMALL LETTER O WITH DIAERESIS', 'L', '006F 0308', 'Ll'),
    0x00F8: ('LATIN SMALL LETTER O WITH STROKE', 'L', '', 'Ll'),
    0x00F9: ('LATIN SMALL LETTER U WITH GRAVE', 'L', '0075 0300', 'Ll'),
    0x00FA: ('LATIN SMALL LETTER U WITH ACUTE', 'L', '0075 0301', 'Ll'),
    0x00FB: ('LATIN SMALL LETTER U WITH CIRCUMFLEX', 'L', '0075 0302', 'Ll'),
    0x00FC: ('LATIN SMALL LETTER U WITH DIAERESIS', 'L', '0075 0308', 'Ll'),
    0x00FD: ('LATIN SMALL LETTER Y WITH ACUTE', 'L', '0079 0301', 'Ll'),
    0x00FE: ('LATIN SMALL LETTER THORN', 'L', '', 'Ll'),
    0x00FF: ('LATIN SMALL LETTER Y WITH DIAERESIS', 'L', '0079 0308', 'Ll'),
    # Some common symbols
    0x00A0: ('NO-BREAK SPACE', 'CS', '', 'Zs'),
    0x00A1: ('INVERTED EXCLAMATION MARK', 'ON', '', 'Po'),
    0x00A2: ('CENT SIGN', 'ET', '', 'Sc'),
    0x00A3: ('POUND SIGN', 'ET', '', 'Sc'),
    0x00A4: ('CURRENCY SIGN', 'ET', '', 'Sc'),
    0x00A5: ('YEN SIGN', 'ET', '', 'Sc'),
    0x00A6: ('BROKEN BAR', 'ON', '', 'So'),
    0x00A7: ('SECTION SIGN', 'ON', '', 'Po'),
    0x00A8: ('DIAERESIS', 'ON', '<compat> 0020 0308', 'Sk'),
    0x00A9: ('COPYRIGHT SIGN', 'ON', '', 'So'),
    0x00AA: ('FEMININE ORDINAL INDICATOR', 'L', '<super> 0061', 'Lo'),
    0x00AB: ('LEFT-POINTING DOUBLE ANGLE QUOTATION MARK', 'ON', '', 'Pi'),
    0x00AC: ('NOT SIGN', 'ON', '', 'Sm'),
    0x00AD: ('SOFT HYPHEN', 'BN', '', 'Cf'),
    0x00AE: ('REGISTERED SIGN', 'ON', '', 'So'),
    0x00AF: ('MACRON', 'ON', '<compat> 0020 0304', 'Sk'),
    0x00B0: ('DEGREE SIGN', 'ET', '', 'So'),
    0x00B1: ('PLUS-MINUS SIGN', 'ET', '', 'Sm'),
    0x00B2: ('SUPERSCRIPT TWO', 'EN', '<super> 0032', 'No'),
    0x00B3: ('SUPERSCRIPT THREE', 'EN', '<super> 0033', 'No'),
    0x00B4: ('ACUTE ACCENT', 'ON', '<compat> 0020 0301', 'Sk'),
    0x00B5: ('MICRO SIGN', 'L', '<compat> 03BC', 'Ll'),
    0x00B6: ('PILCROW SIGN', 'ON', '', 'Po'),
    0x00B7: ('MIDDLE DOT', 'ON', '', 'Po'),
    0x00B8: ('CEDILLA', 'ON', '<compat> 0020 0327', 'Sk'),
    0x00B9: ('SUPERSCRIPT ONE', 'EN', '<super> 0031', 'No'),
    0x00BA: ('MASCULINE ORDINAL INDICATOR', 'L', '<super> 006F', 'Lo'),
    0x00BB: ('RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK', 'ON', '', 'Pf'),
    0x00BC: ('VULGAR FRACTION ONE QUARTER', 'ON', '<fraction> 0031 2044 0034', 'No'),
    0x00BD: ('VULGAR FRACTION ONE HALF', 'ON', '<fraction> 0031 2044 0032', 'No'),
    0x00BE: ('VULGAR FRACTION THREE QUARTERS', 'ON', '<fraction> 0033 2044 0034', 'No'),
    0x00BF: ('INVERTED QUESTION MARK', 'ON', '', 'Po'),
    0x00D7: ('MULTIPLICATION SIGN', 'ON', '', 'Sm'),
    0x00F7: ('DIVISION SIGN', 'ON', '', 'Sm'),
    # Greek letters (commonly used)
    0x0391: ('GREEK CAPITAL LETTER ALPHA', 'L', '', 'Lu'),
    0x0392: ('GREEK CAPITAL LETTER BETA', 'L', '', 'Lu'),
    0x0393: ('GREEK CAPITAL LETTER GAMMA', 'L', '', 'Lu'),
    0x0394: ('GREEK CAPITAL LETTER DELTA', 'L', '', 'Lu'),
    0x0395: ('GREEK CAPITAL LETTER EPSILON', 'L', '', 'Lu'),
    0x0396: ('GREEK CAPITAL LETTER ZETA', 'L', '', 'Lu'),
    0x0397: ('GREEK CAPITAL LETTER ETA', 'L', '', 'Lu'),
    0x0398: ('GREEK CAPITAL LETTER THETA', 'L', '', 'Lu'),
    0x0399: ('GREEK CAPITAL LETTER IOTA', 'L', '', 'Lu'),
    0x039A: ('GREEK CAPITAL LETTER KAPPA', 'L', '', 'Lu'),
    0x039B: ('GREEK CAPITAL LETTER LAMDA', 'L', '', 'Lu'),
    0x039C: ('GREEK CAPITAL LETTER MU', 'L', '', 'Lu'),
    0x039D: ('GREEK CAPITAL LETTER NU', 'L', '', 'Lu'),
    0x039E: ('GREEK CAPITAL LETTER XI', 'L', '', 'Lu'),
    0x039F: ('GREEK CAPITAL LETTER OMICRON', 'L', '', 'Lu'),
    0x03A0: ('GREEK CAPITAL LETTER PI', 'L', '', 'Lu'),
    0x03A1: ('GREEK CAPITAL LETTER RHO', 'L', '', 'Lu'),
    0x03A3: ('GREEK CAPITAL LETTER SIGMA', 'L', '', 'Lu'),
    0x03A4: ('GREEK CAPITAL LETTER TAU', 'L', '', 'Lu'),
    0x03A5: ('GREEK CAPITAL LETTER UPSILON', 'L', '', 'Lu'),
    0x03A6: ('GREEK CAPITAL LETTER PHI', 'L', '', 'Lu'),
    0x03A7: ('GREEK CAPITAL LETTER CHI', 'L', '', 'Lu'),
    0x03A8: ('GREEK CAPITAL LETTER PSI', 'L', '', 'Lu'),
    0x03A9: ('GREEK CAPITAL LETTER OMEGA', 'L', '', 'Lu'),
    0x03B1: ('GREEK SMALL LETTER ALPHA', 'L', '', 'Ll'),
    0x03B2: ('GREEK SMALL LETTER BETA', 'L', '', 'Ll'),
    0x03B3: ('GREEK SMALL LETTER GAMMA', 'L', '', 'Ll'),
    0x03B4: ('GREEK SMALL LETTER DELTA', 'L', '', 'Ll'),
    0x03B5: ('GREEK SMALL LETTER EPSILON', 'L', '', 'Ll'),
    0x03B6: ('GREEK SMALL LETTER ZETA', 'L', '', 'Ll'),
    0x03B7: ('GREEK SMALL LETTER ETA', 'L', '', 'Ll'),
    0x03B8: ('GREEK SMALL LETTER THETA', 'L', '', 'Ll'),
    0x03B9: ('GREEK SMALL LETTER IOTA', 'L', '', 'Ll'),
    0x03BA: ('GREEK SMALL LETTER KAPPA', 'L', '', 'Ll'),
    0x03BB: ('GREEK SMALL LETTER LAMDA', 'L', '', 'Ll'),
    0x03BC: ('GREEK SMALL LETTER MU', 'L', '', 'Ll'),
    0x03BD: ('GREEK SMALL LETTER NU', 'L', '', 'Ll'),
    0x03BE: ('GREEK SMALL LETTER XI', 'L', '', 'Ll'),
    0x03BF: ('GREEK SMALL LETTER OMICRON', 'L', '', 'Ll'),
    0x03C0: ('GREEK SMALL LETTER PI', 'L', '', 'Ll'),
    0x03C1: ('GREEK SMALL LETTER RHO', 'L', '', 'Ll'),
    0x03C2: ('GREEK SMALL LETTER FINAL SIGMA', 'L', '', 'Ll'),
    0x03C3: ('GREEK SMALL LETTER SIGMA', 'L', '', 'Ll'),
    0x03C4: ('GREEK SMALL LETTER TAU', 'L', '', 'Ll'),
    0x03C5: ('GREEK SMALL LETTER UPSILON', 'L', '', 'Ll'),
    0x03C6: ('GREEK SMALL LETTER PHI', 'L', '', 'Ll'),
    0x03C7: ('GREEK SMALL LETTER CHI', 'L', '', 'Ll'),
    0x03C8: ('GREEK SMALL LETTER PSI', 'L', '', 'Ll'),
    0x03C9: ('GREEK SMALL LETTER OMEGA', 'L', '', 'Ll'),
    # Arabic letters (RTL)
    0x0627: ('ARABIC LETTER ALEF', 'AL', '', 'Lo'),
    0x0628: ('ARABIC LETTER BA', 'AL', '', 'Lo'),
    0x062A: ('ARABIC LETTER TA', 'AL', '', 'Lo'),
    0x062B: ('ARABIC LETTER THA', 'AL', '', 'Lo'),
    0x062C: ('ARABIC LETTER JEEM', 'AL', '', 'Lo'),
    0x062D: ('ARABIC LETTER HA', 'AL', '', 'Lo'),
    0x062E: ('ARABIC LETTER KHA', 'AL', '', 'Lo'),
    0x062F: ('ARABIC LETTER DAL', 'AL', '', 'Lo'),
    0x0630: ('ARABIC LETTER THAL', 'AL', '', 'Lo'),
    0x0631: ('ARABIC LETTER RA', 'AL', '', 'Lo'),
    0x0632: ('ARABIC LETTER ZAIN', 'AL', '', 'Lo'),
    0x0633: ('ARABIC LETTER SEEN', 'AL', '', 'Lo'),
    0x0634: ('ARABIC LETTER SHEEN', 'AL', '', 'Lo'),
    0x0635: ('ARABIC LETTER SAD', 'AL', '', 'Lo'),
    0x0636: ('ARABIC LETTER DAD', 'AL', '', 'Lo'),
    0x0637: ('ARABIC LETTER TAH', 'AL', '', 'Lo'),
    0x0638: ('ARABIC LETTER ZAH', 'AL', '', 'Lo'),
    0x0639: ('ARABIC LETTER AIN', 'AL', '', 'Lo'),
    0x063A: ('ARABIC LETTER GHAIN', 'AL', '', 'Lo'),
    0x0641: ('ARABIC LETTER FA', 'AL', '', 'Lo'),
    0x0642: ('ARABIC LETTER QAF', 'AL', '', 'Lo'),
    0x0643: ('ARABIC LETTER KAF', 'AL', '', 'Lo'),
    0x0644: ('ARABIC LETTER LAM', 'AL', '', 'Lo'),
    0x0645: ('ARABIC LETTER MEEM', 'AL', '', 'Lo'),
    0x0646: ('ARABIC LETTER NOON', 'AL', '', 'Lo'),
    0x0647: ('ARABIC LETTER HEH', 'AL', '', 'Lo'),
    0x0648: ('ARABIC LETTER WAW', 'AL', '', 'Lo'),
    0x064A: ('ARABIC LETTER YEH', 'AL', '', 'Lo'),
    # Hebrew letters (RTL)
    0x05D0: ('HEBREW LETTER ALEF', 'R', '', 'Lo'),
    0x05D1: ('HEBREW LETTER BET', 'R', '', 'Lo'),
    0x05D2: ('HEBREW LETTER GIMEL', 'R', '', 'Lo'),
    0x05D3: ('HEBREW LETTER DALET', 'R', '', 'Lo'),
    0x05D4: ('HEBREW LETTER HE', 'R', '', 'Lo'),
    0x05D5: ('HEBREW LETTER VAV', 'R', '', 'Lo'),
    0x05D6: ('HEBREW LETTER ZAYIN', 'R', '', 'Lo'),
    0x05D7: ('HEBREW LETTER HET', 'R', '', 'Lo'),
    0x05D8: ('HEBREW LETTER TET', 'R', '', 'Lo'),
    0x05D9: ('HEBREW LETTER YOD', 'R', '', 'Lo'),
    0x05DA: ('HEBREW LETTER FINAL KAF', 'R', '', 'Lo'),
    0x05DB: ('HEBREW LETTER KAF', 'R', '', 'Lo'),
    0x05DC: ('HEBREW LETTER LAMED', 'R', '', 'Lo'),
    0x05DD: ('HEBREW LETTER FINAL MEM', 'R', '', 'Lo'),
    0x05DE: ('HEBREW LETTER MEM', 'R', '', 'Lo'),
    0x05DF: ('HEBREW LETTER FINAL NUN', 'R', '', 'Lo'),
    0x05E0: ('HEBREW LETTER NUN', 'R', '', 'Lo'),
    0x05E1: ('HEBREW LETTER SAMEKH', 'R', '', 'Lo'),
    0x05E2: ('HEBREW LETTER AYIN', 'R', '', 'Lo'),
    0x05E3: ('HEBREW LETTER FINAL PE', 'R', '', 'Lo'),
    0x05E4: ('HEBREW LETTER PE', 'R', '', 'Lo'),
    0x05E5: ('HEBREW LETTER FINAL TSADI', 'R', '', 'Lo'),
    0x05E6: ('HEBREW LETTER TSADI', 'R', '', 'Lo'),
    0x05E7: ('HEBREW LETTER QOF', 'R', '', 'Lo'),
    0x05E8: ('HEBREW LETTER RESH', 'R', '', 'Lo'),
    0x05E9: ('HEBREW LETTER SHIN', 'R', '', 'Lo'),
    0x05EA: ('HEBREW LETTER TAV', 'R', '', 'Lo'),
    # Common mathematical/special symbols
    0x2019: ('RIGHT SINGLE QUOTATION MARK', 'ON', '', 'Pf'),
    0x201C: ('LEFT DOUBLE QUOTATION MARK', 'ON', '', 'Pi'),
    0x201D: ('RIGHT DOUBLE QUOTATION MARK', 'ON', '', 'Pf'),
    0x2026: ('HORIZONTAL ELLIPSIS', 'ON', '<compat> 002E 002E 002E', 'Po'),
    0x2044: ('FRACTION SLASH', 'ON', '', 'Sm'),
    0x20AC: ('EURO SIGN', 'ET', '', 'Sc'),
    0x2122: ('TRADE MARK SIGN', 'ON', '<super> 0054 004D', 'So'),
    0x2190: ('LEFTWARDS ARROW', 'ON', '', 'Sm'),
    0x2191: ('UPWARDS ARROW', 'ON', '', 'Sm'),
    0x2192: ('RIGHTWARDS ARROW', 'ON', '', 'Sm'),
    0x2193: ('DOWNWARDS ARROW', 'ON', '', 'Sm'),
    0x2200: ('FOR ALL', 'ON', '', 'Sm'),
    0x2202: ('PARTIAL DIFFERENTIAL', 'ON', '', 'Sm'),
    0x2203: ('THERE EXISTS', 'ON', '', 'Sm'),
    0x2205: ('EMPTY SET', 'ON', '', 'Sm'),
    0x2207: ('NABLA', 'ON', '', 'Sm'),
    0x2208: ('ELEMENT OF', 'ON', '', 'Sm'),
    0x220F: ('N-ARY PRODUCT', 'ON', '', 'Sm'),
    0x2211: ('N-ARY SUMMATION', 'ON', '', 'Sm'),
    0x221A: ('SQUARE ROOT', 'ON', '', 'Sm'),
    0x221E: ('INFINITY', 'ON', '', 'Sm'),
    0x222B: ('INTEGRAL', 'ON', '', 'Sm'),
    0x2248: ('ALMOST EQUAL TO', 'ON', '', 'Sm'),
    0x2260: ('NOT EQUAL TO', 'ON', '', 'Sm'),
    0x2264: ('LESS-THAN OR EQUAL TO', 'ON', '', 'Sm'),
    0x2265: ('GREATER-THAN OR EQUAL TO', 'ON', '', 'Sm'),
    # Combining diacritical marks
    0x0300: ('COMBINING GRAVE ACCENT', 'NSM', '', 'Mn'),
    0x0301: ('COMBINING ACUTE ACCENT', 'NSM', '', 'Mn'),
    0x0302: ('COMBINING CIRCUMFLEX ACCENT', 'NSM', '', 'Mn'),
    0x0303: ('COMBINING TILDE', 'NSM', '', 'Mn'),
    0x0304: ('COMBINING MACRON', 'NSM', '', 'Mn'),
    0x0305: ('COMBINING OVERLINE', 'NSM', '', 'Mn'),
    0x0306: ('COMBINING BREVE', 'NSM', '', 'Mn'),
    0x0307: ('COMBINING DOT ABOVE', 'NSM', '', 'Mn'),
    0x0308: ('COMBINING DIAERESIS', 'NSM', '', 'Mn'),
    0x0309: ('COMBINING HOOK ABOVE', 'NSM', '', 'Mn'),
    0x030A: ('COMBINING RING ABOVE', 'NSM', '', 'Mn'),
    0x030B: ('COMBINING DOUBLE ACUTE ACCENT', 'NSM', '', 'Mn'),
    0x030C: ('COMBINING CARON', 'NSM', '', 'Mn'),
    0x0327: ('COMBINING CEDILLA', 'NSM', '', 'Mn'),
    0x0328: ('COMBINING OGONEK', 'NSM', '', 'Mn'),
    # Newline / paragraph separators
    0x2028: ('LINE SEPARATOR', 'WS', '', 'Zl'),
    0x2029: ('PARAGRAPH SEPARATOR', 'B', '', 'Zp'),
    # Zero-width and formatting characters
    0x200B: ('ZERO WIDTH SPACE', 'BN', '', 'Cf'),
    0x200C: ('ZERO WIDTH NON-JOINER', 'BN', '', 'Cf'),
    0x200D: ('ZERO WIDTH JOINER', 'BN', '', 'Cf'),
    0x200E: ('LEFT-TO-RIGHT MARK', 'L', '', 'Cf'),
    0x200F: ('RIGHT-TO-LEFT MARK', 'R', '', 'Cf'),
    0xFEFF: ('ZERO WIDTH NO-BREAK SPACE', 'BN', '', 'Cf'),
}

# Build reverse lookup: name -> codepoint
_NAME_TO_CODEPOINT = {v[0]: k for k, v in _UNICODE_DATA.items()}


def name(chr_val):
    """
    Return the Unicode name for the given character.
    Raises ValueError if the name is not known.
    """
    cp = ord(chr_val)
    if cp in _UNICODE_DATA:
        return _UNICODE_DATA[cp][0]
    raise ValueError(f'no such name for character U+{cp:04X}')


def lookup(name_str):
    """
    Look up a character by its Unicode name.
    Returns the character, or raises KeyError if not found.
    """
    name_upper = name_str.upper()
    if name_upper in _NAME_TO_CODEPOINT:
        return chr(_NAME_TO_CODEPOINT[name_upper])
    raise KeyError(f'undefined character name: {name_str!r}')


def bidirectional(chr_val):
    """
    Return the bidirectional class string for the given character.
    Returns '' if the character is not in the lookup table.
    """
    cp = ord(chr_val)
    if cp in _UNICODE_DATA:
        return _UNICODE_DATA[cp][1]
    return ''


def decomposition(chr_val):
    """
    Return the decomposition mapping string for the given character.
    Returns '' if there is no decomposition.
    """
    cp = ord(chr_val)
    if cp in _UNICODE_DATA:
        return _UNICODE_DATA[cp][2]
    return ''


def category(chr_val):
    """
    Return the general category string for the given character.
    Returns 'Cn' (unassigned) if not in the lookup table.
    """
    cp = ord(chr_val)
    if cp in _UNICODE_DATA:
        return _UNICODE_DATA[cp][3]
    return 'Cn'


# ---------------------------------------------------------------------------
# Zero-argument invariant functions
# ---------------------------------------------------------------------------

def unicodedata2_name():
    """Invariant: name('A') == 'LATIN CAPITAL LETTER A'"""
    return name('A')


def unicodedata2_bidirectional():
    """Invariant: bidirectional('A') in ('L', '') — True"""
    result = bidirectional('A')
    return result in ('L', '')


def unicodedata2_decomposition():
    """Invariant: decomposition('A') == ''"""
    return decomposition('A')