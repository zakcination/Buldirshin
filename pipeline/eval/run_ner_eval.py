#!/usr/bin/env python3
"""
KazNERD моделін біздің жыр корпусында сынау.

Гипотеза: KazNERD ТЕЛЕДИДАР ЖАҢАЛЫҚТАРЫ мәтінінде оқытылған (F1 97,22%).
Ал біздің материал — XVIII ғасыр жыры. Домен айырмасы қаншалық зиян тигізеді?

МАҢЫЗДЫ ТЕХНИКАЛЫҚ ШЕШІМ
------------------------
Бұл скрипт transformers-тің `pipeline` функциясын ӘДЕЙІ пайдаланбайды. Себебі екеу:

1. `pipeline` импорты torchvision тізбегін тартады. Colab-та torch мен torchvision
   нұсқалары сәйкес келмесе, «RuntimeError: operator torchvision::nms does not exist»
   қатесі шығады — мәтін тапсырмасына ешқандай қатысы жоқ болса да.
2. `aggregation_strategy` баптауы нәтижені 18%-дан 79%-ға дейін өзгертеді. Оны
   кітапханаға қалдырмай, өзіміз бақылаған дұрыс.

Сондықтан біріктіру қолмен жасалады, екі сатыда:
  1) әр сөзге бір таңба — оның БІРІНШІ субсөзінікі (pipeline-дағы "first" баламасы);
  2) BIO схемасы бойынша көрші сөздерді біріктіру, әйтпесе «Қозы Маңрақ» екі бөлек
     нысан болып қалады да, көп сөзді атаулар жоғалады.

Есептеу ЖИЫН деңгейінде: модель эталондағы есімдерді тапты ма? Себебі нақты
қажеттілігіміз де сол — тексерілетін тұжырым тізбесін алу, жол-жол разметка емес.
"""
import json, sys, re, os
from collections import defaultdict

MODEL = "yeshpanovrustem/xlm-roberta-large-kaznerd"
GOLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gold")

def norm(s):
    return re.sub(r"[^\w]", "", s.lower())

def matches(gold, pred):
    """Қазақ тілі жалғамалы («Бөгенбайдай»), әрі модель ру атауын есіммен қосып
    беруі мүмкін («ҚанжығалыБөгенбай»). Сондықтан екі ереже: бастапқы сәйкестік
    НЕМЕСЕ ішкі жол."""
    g, p = norm(gold), norm(pred)
    if not g or not p:
        return False
    if len(g) >= 4 and g in p:
        return True
    n = min(len(g), len(p))
    return (g == p) if n < 4 else g[:n] == p[:n]

def tag_line(line, tok, mdl, torch):
    """Бір жолды белгілеу. Қайтарады: [(сөз, класс), ...] — тек нысандар."""
    words = line.split()
    if not words:
        return []
    ids, word_of_tok = [], []
    for wi, w in enumerate(words):
        sub = tok.encode(w, add_special_tokens=False)
        if not sub:
            sub = [tok.unk_token_id]
        ids.extend(sub)
        word_of_tok.extend([wi] * len(sub))
    # модельдің шектеуіне сыйғызу
    limit = min(getattr(tok, "model_max_length", 512), 512) - 2
    ids, word_of_tok = ids[:limit], word_of_tok[:limit]
    input_ids = [tok.cls_token_id] + ids + [tok.sep_token_id]
    with torch.no_grad():
        logits = mdl(torch.tensor([input_ids])).logits[0]
    pred = logits.argmax(-1).tolist()[1:-1]          # арнайы таңбаларды алып тастау
    id2label = mdl.config.id2label

    # 1) әр сөзге бір таңба: БІРІНШІ субсөздікі
    per_word, seen = [], set()
    for tok_i, wi in enumerate(word_of_tok):
        if wi in seen:
            continue
        seen.add(wi)
        per_word.append((words[wi], id2label[pred[tok_i]]))

    # 2) BIO бойынша көрші сөздерді біріктіру: «Қозы Маңрақ» бір нысан болып қалады
    out, cur, cur_lab = [], [], None
    for w, lab in per_word:
        if lab == "O":
            if cur: out.append((" ".join(cur), cur_lab)); cur, cur_lab = [], None
            continue
        pref, typ = (lab.split("-", 1) + [""])[:2] if "-" in lab else ("B", lab)
        typ = typ or lab
        if cur and pref == "I" and typ == cur_lab:
            cur.append(w)
        else:
            if cur: out.append((" ".join(cur), cur_lab))
            cur, cur_lab = [w], typ
    if cur:
        out.append((" ".join(cur), cur_lab))
    return out

def main():
    import torch
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    print(f"Модель жүктелуде: {MODEL} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL)
    mdl = AutoModelForTokenClassification.from_pretrained(MODEL).eval()
    print("Кластар:", sorted({l.split("-")[-1] for l in mdl.config.id2label.values()}), flush=True)

    gold = json.load(open(os.path.join(GOLD_DIR, "annotations.json")))
    preds_dump, totals = {}, defaultdict(lambda: [0, 0, 0])   # тапты, эталон, болжам
    for tid, ann in gold.items():
        if tid.startswith("_"):
            continue
        text = open(os.path.join(GOLD_DIR, tid + ".txt")).read()
        by_type = defaultdict(set)
        for line in text.splitlines():
            for word, lab in tag_line(line.strip(), tok, mdl, torch):
                by_type[lab].add(word.strip(" ,.!?;:—-«»"))
        preds_dump[tid] = {k: sorted(v) for k, v in by_type.items()}

        print(f"\n{'='*62}\n{tid}\n{'='*62}")
        for typ, keys in (("PER", ("PERSON",)),
                          ("LOC", ("LOCATION", "GPE")),
                          ("NUM", ("CARDINAL", "DATE"))):
            g = ann.get(typ, [])
            if typ == "NUM" and not g:      # мәтінде сан дерегі жоқ болса, өткіземіз
                continue
            cand = set()
            for k, v in by_type.items():
                if any(x in k.upper() for x in keys):
                    cand |= v
            found  = [x for x in g if any(matches(x, c) for c in cand)]
            missed = [x for x in g if x not in found]
            spur   = [c for c in cand if not any(matches(x, c) for x in g)]
            t = totals[typ]
            t[0] += len(found); t[1] += len(g); t[2] += len(cand)
            rec  = len(found) / len(g) if g else float("nan")
            prec = len(found) / len(cand) if cand else 0.0
            print(f"\n  [{typ}]  эталон={len(g)}  тапты={len(found)}  "
                  f"Recall={rec:.0%}  Precision≈{prec:.0%}")
            if found:  print(f"    ✓ тапқаны  : {', '.join(found)}")
            if missed: print(f"    ✗ ЖІБЕРГЕНІ: {', '.join(missed)}")
            if spur:   print(f"    ? артығы   : {', '.join(sorted(spur)[:12])}")

    print(f"\n{'='*62}\nЖИЫНТЫҚ\n{'='*62}")
    for typ, (f, g, c) in totals.items():
        print(f"  {typ}: Recall={f/g:.0%} ({f}/{g})   Precision≈{f/c:.0%} ({f}/{c})")
    json.dump(preds_dump, open(os.path.join(GOLD_DIR, "_predictions.json"), "w"),
              ensure_ascii=False, indent=1)
    print("\nБолжамдар сақталды: gold/_predictions.json")

if __name__ == "__main__":
    main()
