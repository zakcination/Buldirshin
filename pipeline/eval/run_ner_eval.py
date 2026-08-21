#!/usr/bin/env python3
"""
KazNERD моделін біздің жыр корпусында сынау.

Гипотеза: KazNERD ТЕЛЕДИДАР ЖАҢАЛЫҚТАРЫ мәтінінде оқытылған (F1 97,22%).
Ал біздің материал — XVIII ғасыр жыры. Домен айырмасы қаншалық зиян тигізеді?

Есептеу ЖИЫН деңгейінде: модель эталондағы есімдерді тапты ма?
Себебі нақты қажеттілігіміз де сол — тексерілетін тұжырым тізбесін алу,
жол-жол разметка емес.

Сәйкестендіру ережесі: қазақ тілі жалғамалы болғандықтан («Бөгенбайдай»,
«Абылайға»), эталон мен болжам бір-бірінің басы болса, сәйкес деп саналады
(кемінде 4 таңба ортақ).
"""
import json, sys, re, os
from collections import defaultdict

MODEL = "yeshpanovrustem/xlm-roberta-large-kaznerd"
# МАҢЫЗДЫ: "simple" тәсілі бұл модельде жарамайды — токенизатор word_ids бермейді
# («Tokenizer does not support real words» ескертуі), нәтижесінде сөз бөлшектеніп,
# Recall 79% орнына 18% болып шығады. Қараңыз README.md, «Агрегация тұзағы».
AGG = "first"
GOLD_DIR = os.path.join(os.path.dirname(__file__), "gold")

def norm(s):
    return re.sub(r"[^\w]", "", s.lower())

def matches(gold, pred):
    g, p = norm(gold), norm(pred)
    if not g or not p: return False
    n = min(len(g), len(p))
    if n < 4: return g == p
    return g[:n] == p[:n]

def main():
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    print(f"Модель жүктелуде: {MODEL} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL)
    mdl = AutoModelForTokenClassification.from_pretrained(MODEL)
    print("Кластар:", sorted(set(l.split("-")[-1] for l in mdl.config.id2label.values())), flush=True)
    ner = pipeline("ner", model=mdl, tokenizer=tok, aggregation_strategy=AGG)

    gold = json.load(open(os.path.join(GOLD_DIR, "annotations.json")))
    results = {}
    for tid, ann in gold.items():
        if tid.startswith("_"): continue
        text = open(os.path.join(GOLD_DIR, tid + ".txt")).read()
        preds = defaultdict(set)
        for line in text.splitlines():
            line = line.strip()
            if not line: continue
            for e in ner(line):
                preds[e["entity_group"]].add(e["word"].strip())
        results[tid] = {k: sorted(v) for k, v in preds.items()}

        print(f"\n{'='*62}\n{tid}\n{'='*62}")
        for typ in ("PER", "LOC"):
            g = ann.get(typ, [])
            # KazNERD класс атауларын біздің типке жинау
            cand = set()
            for k, v in preds.items():
                ku = k.upper()
                if typ == "PER" and ("PERSON" in ku or ku == "PER"): cand |= set(v)
                if typ == "LOC" and any(x in ku for x in ("LOCATION", "GPE", "LOC")): cand |= set(v)
            found  = [x for x in g if any(matches(x, c) for c in cand)]
            missed = [x for x in g if x not in found]
            spur   = [c for c in cand if not any(matches(x, c) for x in g)]
            rec  = len(found)/len(g) if g else float("nan")
            prec = len(found)/len(cand) if cand else 0.0
            print(f"\n  [{typ}]  эталон={len(g)}  тапты={len(found)}  "
                  f"Recall={rec:.0%}  Precision≈{prec:.0%}")
            if found:  print(f"    ✓ тапқаны : {', '.join(found)}")
            if missed: print(f"    ✗ ЖІБЕРГЕНІ: {', '.join(missed)}")
            if spur:   print(f"    ? артығы  : {', '.join(sorted(spur)[:15])}")
    json.dump(results, open(os.path.join(GOLD_DIR, "_predictions.json"), "w"),
              ensure_ascii=False, indent=1)
    print("\nБолжамдар сақталды: gold/_predictions.json")

if __name__ == "__main__":
    main()
