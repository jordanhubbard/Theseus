from theseus_re_cr2 import compile, findall, sub, split
from theseus_re_cr4 import search, match, finditer

def re5_compile_match():
    return compile('[0-9]+').match('123abc').group()

def re5_compile_findall():
    return compile(r'\w+').findall('hello world')

def re5_compile_sub():
    return compile(r'\d').sub('X', 'a1b2')
