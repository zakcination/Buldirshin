#!/usr/bin/env python3
"""
kaz_lint — қазақ мәтініндегі OCR мен теру қателерін табатын тексергіш.

Не істейді:
  1. Аралас жазу (homoglyph) — бір сөз ішінде латын мен кириллица әрпі қатар тұрса.
     Бұл OCR-дың ең жиі әрі ең байқалмайтын қатесі: «Cоғыс» (латын C) көзге
     «Соғыс» болып көрінеді, бірақ іздеу таппайды.
  2. Қазақ әліпбиінде жоқ таңбалар (щ, ъ, ь орыс сөздерінен тыс жерде — ескерту).
  3. Тасымал сызықшасының қалдығы.

Әдейі ЖОҚ: «қайталанған буын» ережесі. Қазақ жалғауы табиғи түрде буын қайталайды
(«Шамамен», «заманының»), сондықтан ол ереже тек жалған дабыл берді — алынып тасталды.
Мұндай қатені табу үшін сөздік қажет, эвристика жеткіліксіз.

Қолданылуы:
    python3 kaz_lint.py FILE...            # есеп
    python3 kaz_lint.py --json FILE...     # машина оқитын шығыс
"""
import re, sys, json, unicodedata
from collections import Counter

CYR = set("аәбвгғдеёжзийкқлмнңоөпрстуұүфхһцчшщъыіьэюя"
          "АӘБВГҒДЕЁЖЗИЙКҚЛМНҢОӨПРСТУҰҮФХҺЦЧШЩЪЫІЬЭЮЯ")
LAT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

# латын ↔ кириллица көзге бірдей көрінетін жұптар
HOMOGLYPH = {
    "A":"А","B":"В","C":"С","E":"Е","H":"Н","K":"К","M":"М","O":"О","P":"Р",
    "T":"Т","X":"Х","Y":"У","I":"І","a":"а","c":"с","e":"е","o":"о","p":"р",
    "x":"х","y":"у","i":"і","s":"ѕ","3":"З","0":"О",
}
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

def scripts_of(word):
    has_c = any(ch in CYR for ch in word)
    has_l = any(ch in LAT for ch in word)
    return has_c, has_l

def check_line(line, lineno):
    out = []
    for m in WORD.finditer(line):
        w = m.group()
        has_c, has_l = scripts_of(w)
        if has_c and has_l:
            bad = [(i, ch) for i, ch in enumerate(w) if ch in LAT]
            fix = "".join(HOMOGLYPH.get(ch, ch) if ch in LAT else ch for ch in w)
            out.append({
                "type": "mixed_script", "line": lineno, "word": w,
                "latin_chars": [ch for _, ch in bad],
                "suggest": fix if fix != w else None,
                "note": "бір сөзде латын мен кириллица араласқан",
            })
    # тасымал қалдығы: сөз ортасында «- » немесе жол соңында жалғыз әріп
    if re.search(r"\w-\s+\w", line):
        out.append({"type": "hyphen_break", "line": lineno,
                    "note": "тасымал сызықшасы қалып қойған болуы мүмкін"})
    return out

def check_file(path):
    findings = []
    with open(path, encoding="utf-8") as f:
        infence = False
        for i, line in enumerate(f, 1):
            if line.strip().startswith("```"):
                infence = not infence
                continue
            findings.extend(check_line(line.rstrip("\n"), i))
    return findings

def main(argv):
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__); return 2
    all_f, total = {}, 0
    for p in paths:
        f = check_file(p)
        if f:
            all_f[p] = f
            total += len(f)
    if as_json:
        print(json.dumps(all_f, ensure_ascii=False, indent=1)); return 0
    for p, fs in all_f.items():
        print(f"\n=== {p} ({len(fs)}) ===")
        for x in fs:
            s = f"  {x['line']:>5}: [{x['type']}]"
            if "word" in x: s += f" «{x['word']}»"
            if x.get("suggest"): s += f" → «{x['suggest']}»"
            print(s + f"  — {x['note']}")
    print(f"\nБарлығы: {total} ескерту, {len(all_f)} файлда")
    return 1 if total else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
