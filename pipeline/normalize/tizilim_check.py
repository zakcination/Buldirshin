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
    qa = load("qaharmandar.yaml").get("qaharmandar", [])
    zh_ids = {z.get("id") for z in zh}
    ba_ids = {b.get("id") for b in ba}
    qa_ids = {x.get("id") for x in qa}

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

    # ── ТІЗІМ ҚАБАТЫ: qaharmandar.yaml (06-tolyq-tizilim.md) ──
    TIERS = {"эпос-қырық-батыр", "эпос-жеке", "эпос-ортақ-түркі", "тарихи-жыр",
             "XVIII", "XIX", "XIX-қатар", "шетел", "XX"}
    seen_q = set()
    for it in qa:
        w = f"қаһарман «{it.get('id') or '?'}»"
        if not it.get("id"):
            err(w, "id жоқ")
            continue
        if it["id"] in seen_q:
            err(w, "id қайталанған")
        seen_q.add(it["id"])
        if not it.get("name"):
            err(w, "name жоқ")
        if it.get("tier") not in TIERS:
            err(w, f"tier жарамсыз: {it.get('tier')!r}")
        if it.get("level") not in ("A", "B", "C", "D", "E"):
            err(w, f"level жарамсыз: {it.get('level')!r}")
        if not it.get("source_doc"):
            err(w, "source_doc жоқ — жазба қай құжаттан алынғанын көрсетуі керек")
        p, st = it.get("passport"), it.get("status")
        if p:
            if p not in ba_ids:
                err(w, f"passport → «{p}» batyrlar.yaml-да жоқ")
            if st != "зерттелген":
                err(w, "passport бар, бірақ status «зерттелген» емес")
        elif st != "тізімде":
            err(w, "passport жоқ, сондықтан status «тізімде» болуы керек")
        if str(it.get("tier", "")).startswith("эпос") and not it.get("corpus"):
            warn(w, "эпос қабатындағы жазбада corpus көрсетілмеген")
        if it.get("tier") == "XX" and not it.get("award"):
            err(w, "XX қабатындағы жазбада award жоқ — атақ атауы міндетті")
        sa = it.get("same_as")
        if sa:
            if sa not in qa_ids:
                err(w, f"same_as → «{sa}» тізімде жоқ")
            else:
                other = next(o for o in qa if o.get("id") == sa)
                if other.get("same_as") != it["id"]:
                    warn(w, f"same_as → «{sa}» кері сілтеме жасамайды")

    linked = {it.get("passport") for it in qa if it.get("passport")}
    for bid in sorted(ba_ids - linked):
        warn(f"батыр «{bid}»", "qaharmandar.yaml тізімінде жазбасы жоқ")

    # ── ШИКІ ҚАБАТ: qaharmandar-ko-tizimi.yaml ──
    ko = load("qaharmandar-ko-tizimi.yaml").get("ko_tizimi", [])
    seen_k = set()
    for it in ko:
        w = f"КО тізімі «{it.get('id') or '?'}»"
        if not it.get("id"):
            err(w, "id жоқ")
            continue
        if it["id"] in seen_k:
            err(w, "id қайталанған")
        seen_k.add(it["id"])
        if not it.get("name_source"):
            err(w, "name_source жоқ — бастапқы жазудағы есім міндетті")
        if it.get("level") != "C":
            err(w, "шикі қабаттың деңгейі C болуы керек (тасымалы — вики айнасы)")
        if it.get("status") != "тізімде":
            err(w, "шикі қабаттың status-ы «тізімде» болуы керек")
        if "name_kk" not in it:
            warn(w, "name_kk өрісі жоқ — бос болса да тұруы керек")

    print(f"Жыраулар: {len(zh)} · Батырлар: {len(ba)} · "
          f"Қаһармандар тізімі: {len(qa)} · КО шикі тізімі: {len(ko)}")
    for x in warnings:
        print("  ЕСКЕРТУ  " + x)
    for x in errors:
        print("  ҚАТЕ     " + x)
    print(f"\nБарлығы: {len(errors)} қате, {len(warnings)} ескерту")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
