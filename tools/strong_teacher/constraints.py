"""Finite Quick-code grammar; all edges come from the actual native dictionary."""
import re


def read_facts(path):
    codes={}
    for line in path.read_text().splitlines():
        char,aliases=line.split('\t')
        if len(char)!=1:raise ValueError('One Unicode scalar required')
        for code in aliases.split(','):
            if not re.fullmatch('[a-z]{1,2}',code):raise ValueError('Invalid native alias')
            codes.setdefault(code,set()).add(char)
    return codes


def accept(code,text,codes):
    if not re.fullmatch('[a-z]{1,48}',code):return False
    positions={0}
    for char in text:
        positions={p+n for p in positions for n in (1,2)
            if p+n<=len(code) and char in codes.get(code[p:p+n],())}
        if not positions:return False
    return len(code) in positions


def align(code,text,codes):
    failed=set()
    def visit(p,at):
        if at==len(text):return [] if p==len(code) else None
        if (p,at) in failed:return None
        for n in (2,1):
            if p+n<=len(code) and text[at] in codes.get(code[p:p+n],()):
                rest=visit(p+n,at+1)
                if rest is not None:return [n]+rest
        failed.add((p,at));return None
    return visit(0,0)


def grammar(code,codes):
    if not re.fullmatch('[a-z]{1,48}',code):raise ValueError('Invalid Quick code')
    reachable={len(code)}
    for p in range(len(code)-1,-1,-1):
        if any(p+n in reachable and codes.get(code[p:p+n]) for n in (1,2) if p+n<=len(code)):
            reachable.add(p)
    if 0 not in reachable:raise ValueError('No legal complete Chinese output')
    out=['root ::= p0'];used=set()
    for p in sorted(reachable):
        if p==len(code):out.append(f'p{p} ::= ""');continue
        choices=[]
        for n in (2,1):
            key=code[p:p+n]
            if p+n<=len(code) and p+n in reachable and codes.get(key):
                used.add(key);choices.append(f'c{key} p{p+n}')
        out.append(f'p{p} ::= '+' | '.join(choices))
    for key in sorted(used):
        chars=''.join(('\\u%04x'%ord(c)) if ord(c)<=0xffff else ('\\U%08x'%ord(c)) for c in sorted(codes[key]))
        out.append(f'c{key} ::= [{chars}]')
    return '\n'.join(out)+'\n'
