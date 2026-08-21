#!/usr/bin/env python3
"""
Топоним сөздігі арқылы жер-су атауларын табу.

Неге керек: KazNERD теледидар жаңалығында оқытылған, көне топонимде әлсіз
(LOC Recall 65%). Ал біздің корпустағы жер атаулары шектеулі әрі белгілі —
сондықтан сөздік іздеу дәлірек жұмыс істейді.

Шектеуі АЙҚЫН: сөздік тек БЕЛГІЛІ атауды табады, жаңасын аша алмайды.
Сондықтан ол NER-ді алмастырмайды, толықтырады:
    сөздік  → белгілі топонимді сенімді табу
    NER     → сөздікте жоқ жаңа атауды ашу

Қазақ тілі жалғамалы («Ақшәуліге», «Ертістен»), сондықтан сәйкестендіру
түбір бойынша жүреді.
"""
import re, os, sys, json

YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toponyms.yaml")

def load(path=YAML):
    """Қарапайым талдағыш — сыртқы кітапханасыз (Colab-та да, offline де жүреді)."""
    entries, cur = [], None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if re.match(r"\s*#", line) or not line.strip():
            continue
        m = re.match(r"\s*-\s+id:\s*(.+)", line)
        if m:
            if cur: entries.append(cur)
            cur = {"id": m.group(1).strip(), "variants": []}
            continue
        if cur is None:
            continue
        m = re.match(r"\s+(\w+):\s*(.*)", line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if k == "variants":
                cur["variants"] = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
            elif v:
                cur[k] = v
    if cur: entries.append(cur)
    return entries

def _stem(w):
    return re.sub(r"[^\w]", "", w.lower())

def build_index(entries):
    """{түбір: жазба} — көп сөзді атаулар бөлек сақталады."""
    single, multi = {}, []
    for e in entries:
        forms = [e.get("canon", "")] + e.get("variants", [])
        for f in forms:
            if not f: continue
            parts = f.split()
            if len(parts) == 1:
                single.setdefault(_stem(f), e)
            else:
                multi.append(([_stem(p) for p in parts], e))
    multi.sort(key=lambda x: -len(x[0]))       # ұзынын бірінші сынау
    return single, multi

def find(text, entries=None, max_suffix=6):
    """Мәтіннен топоним табу. Қайтарады: [(табылған тіркес, жазба), ...]

    Сәйкестендіру ережесі: сөз сөздіктегі тұлғаның ТОЛЫҚ түбірінен басталуы керек,
    жалғауы ғана артық болады (max_suffix таңбадан аспайды).

    Неге толық түбір: алғашқы 4 әріпті ғана салыстырғанда «Қаратау» түбірі
    «Қаракерей», «Қарақалпақ», тіпті «қараң» сөзіне жабысып, жалған дабыл берді.
    Толық түбір талабы оны түбегейлі жояды."""
    entries = entries or load()
    single, multi = build_index(entries)
    out, seen = [], set()
    for line in text.splitlines():
        toks = line.split()
        stems = [_stem(t) for t in toks]
        used = set()
        # 1) көп сөзді атаулар
        for parts, e in multi:
            n = len(parts)
            for i in range(len(stems) - n + 1):
                if any(j in used for j in range(i, i + n)):
                    continue
                ok = all(stems[i + k].startswith(parts[k]) and
                         len(stems[i + k]) - len(parts[k]) <= max_suffix
                         for k in range(n))
                if ok:
                    used |= set(range(i, i + n))
                    key = (e["id"], " ".join(toks[i:i + n]))
                    if key not in seen:
                        seen.add(key); out.append((" ".join(toks[i:i + n]), e))
        # 2) бір сөзді
        for i, st in enumerate(stems):
            if i in used or len(st) < 4:
                continue
            for stem_key, e in sorted(single.items(), key=lambda x: -len(x[0])):
                if len(stem_key) < 4:
                    continue
                if st.startswith(stem_key) and len(st) - len(stem_key) <= max_suffix:
                    key = (e["id"], toks[i])
                    if key not in seen:
                        seen.add(key); out.append((toks[i], e))
                    break
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2:
        ents = load()
        print(f"Сөздікте {len(ents)} жазба.")
        print("Қолданылуы: python3 gazetteer.py FILE")
        sys.exit(0)
    for path in sys.argv[1:]:
        hits = find(open(path, encoding="utf-8").read())
        print(f"\n=== {path} ({len(hits)}) ===")
        for surf, e in hits:
            st = e.get("status", "?")
            mark = {"расталған": "✓", "болжам": "~", "анықталмаған": "?"}.get(st, " ")
            print(f"  {mark} «{surf}» → {e.get('canon')}  [{e.get('type','?')}] {st}"
                  + (f"  ({e['t']})" if e.get("t") else ""))
