"""Қазақ кириллицасы → латын slug. Тізілім id-лерін тұрақты жасау үшін."""
M = {
    'а':'a','ә':'a','б':'b','в':'v','г':'g','ғ':'g','д':'d','е':'e','ё':'yo',
    'ж':'zh','з':'z','и':'i','й':'y','к':'k','қ':'q','л':'l','м':'m','н':'n',
    'ң':'n','о':'o','ө':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ұ':'u',
    'ү':'u','ф':'f','х':'h','һ':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','і':'i','ь':'','э':'e','ю':'yu','я':'ya',
}

def slug(s: str) -> str:
    out = []
    for ch in s.lower():
        if ch in M:
            out.append(M[ch])
        elif ch.isalnum() and ch.isascii():
            out.append(ch)
        elif ch in ' -–—_':
            out.append('-')
    r = ''.join(out)
    while '--' in r:
        r = r.replace('--', '-')
    return r.strip('-')
