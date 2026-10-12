#!/usr/bin/env python3
"""Тізілім тексергіші — zertteu/tizilim/data/*.yaml.

Схема: zertteu/tizilim/00-shema.md
Мақсаты: схемадағы ережелерді ҚАҒАЗДАН КОДҚА көшіру. Әсіресе §4 —
мінез-қасиет ешқашан факт ретінде жазылмайды.

Қолданысы:  python3 -I pipeline/normalize/tizilim_check.py
Қайтарады:  0 — таза, 1 — қате бар
"""
import sys, pathlib, yaml

DATA = pathlib.Path(__file__).resolve().parents[2] / "zertteu" / "tizilim" / "data"

LEVELS = set("ABCDE")
LINK_TYPES = set("ЗКЭЖД")
TRAIT_KINDS = {"мақтау", "сын", "бейтарап"}
STATUSES = {"тізімде ғана", "ішінара", "зерттелген"}

errors, warnings = [], []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


def check_level(where, field, node):
    """Деңгейі бар өріс — деңгейсіз дерек жарамсыз."""
    if not isinstance(node, dict):
        return
    if node.get("value") is None and node.get("raw") is None \
            and node.get("birth") is None and node.get("death") is None:
        return
    lv = node.get("level")
    if lv is None:
        err(where, f"«{field}» өрісінде level жоқ — деңгейсіз дерек жарамсыз")
    elif lv not in LEVELS:
        err(where, f"«{field}» деңгейі жарамсыз: {lv!r} (A–E болуы керек)")


def load(name):
    p = DATA / name
    if not p.exists():
        err(str(p), "файл жоқ")
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def main():
    zh = load("zhyraular.yaml").get("zhyraular", [])
    ba = load("batyrlar.yaml").get("batyrlar", [])
    zh_ids = {z.get("id") for z in zh}
    ba_ids = {b.get("id") for b in ba}

    def status_of(coll, it):
        # схема §3: батырда status — documentation ішінде; §5: жырауда — түбірде
        if coll == "батыр":
            return (it.get("documentation") or {}).get("status")
        return it.get("status")

    for coll, items in (("жырау", zh), ("батыр", ba)):
        seen = set()
        for it in items:
            w = f"{coll} «{it.get('id') or '?'}»"
            if not it.get("id"):
                err(w, "id жоқ")
            elif it["id"] in seen:
                err(w, "id қайталанған")
            else:
                seen.add(it["id"])
            st = status_of(coll, it)
            if st not in STATUSES:
                err(w, f"status жарамсыз: {st!r}")

    # --- жыраулар ---
    for z in zh:
        w = f"жырау «{z.get('id')}»"
        check_level(w, "dates", z.get("dates") or {})
        check_level(w, "clan", z.get("clan") or {})
        for bid in z.get("sang_about") or []:
            if bid not in ba_ids:
                warn(w, f"sang_about → «{bid}» батырлар тізілімінде жоқ")

    # --- батырлар ---
    for b in ba:
        w = f"батыр «{b.get('id')}»"
        if not (b.get("name") or {}).get("canonical"):
            err(w, "name.canonical жоқ")
        check_level(w, "dates", b.get("dates") or {})
        check_level(w, "clan", b.get("clan") or {})

        link = b.get("zhyrau_link") or {}
        t = link.get("type")
        if t not in LINK_TYPES:
            err(w, f"zhyrau_link.type жарамсыз: {t!r} (З/К/Э/Ж/Д)")
        for zid in link.get("zhyrau_ids") or []:
            if zid not in zh_ids:
                warn(w, f"zhyrau_link → «{zid}» жыраулар тізілімінде жоқ")
        if t == "З" and not (link.get("zhyrau_ids")):
            err(w, "тип З, бірақ жырау көрсетілмеген")
        if t in {"Ж", "Э"} and link.get("zhyrau_ids"):
            err(w, f"тип {t}, бірақ жырау көрсетілген — қайшылық")

        # --- §4: мінез-қасиет ережесі ---
        for i, tr in enumerate(b.get("traits") or []):
            tw = f"{w}, traits[{i}]"
            if not tr.get("text"):
                err(tw, "text жоқ")
            if not tr.get("attributed_in"):
                err(tw, "attributed_in жоқ — §4 бойынша қасиет факт ретінде жазылмайды")
            k = tr.get("kind")
            if k not in TRAIT_KINDS:
                err(tw, f"kind жарамсыз: {k!r} (мақтау/сын/бейтарап)")
            if tr.get("level") not in LEVELS:
                err(tw, f"level жарамсыз: {tr.get('level')!r}")

        doc = b.get("documentation") or {}
        if (doc.get("status")) == "зерттелген":
            if not doc.get("primary_sources"):
                err(w, "status «зерттелген», бірақ primary_sources бос")
            if not (doc.get("has_level_I") or doc.get("has_level_III")):
                err(w, "status «зерттелген», бірақ I де, III де деңгей дерегі жоқ")
        if t == "З" and not doc.get("has_level_I"):
            warn(w, "тип З (заманхат), бірақ has_level_I false — тексеріңіз")

        kinds = {tr.get("kind") for tr in (b.get("traits") or [])}
        if kinds and kinds == {"мақтау"}:
            warn(w, "тек мақтау сипаттамалары бар — сын қабаты ізделді ме?")

        for cid in b.get("companions") or []:
            if cid in ba_ids:
                continue
            if cid in zh_ids:
                # §2а — қос рөл: батыр әрі жырау (Ақтамберді, Махамбет)
                warn(w, f"companions → «{cid}» жыраулар тізілімінде бар — "
                        f"қос рөл ме? §2а бойынша екі жазба керек")
            else:
                warn(w, f"companions → «{cid}» ешбір тізілімде жоқ")

    print(f"Жыраулар: {len(zh)} · Батырлар: {len(ba)}")
    for x in warnings:
        print("  ЕСКЕРТУ  " + x)
    for x in errors:
        print("  ҚАТЕ     " + x)
    print(f"\nБарлығы: {len(errors)} қате, {len(warnings)} ескерту")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
