# -*- coding: utf-8 -*-
"""book-anthology бандлінен дерек массивтерін суырып алу (eval-сіз, тек парсинг)."""
import re, io, json, sys

SRC = sys.argv[1]
s = io.open(SRC, encoding="utf-8", errors="replace").read()

def find_array(id_prefix):
    """id:"<prefix>..." деген бірінші элементі бар массивтің шекарасын табу."""
    m = re.search(r'=\[\{id:"%s' % re.escape(id_prefix), s)
    if not m:
        return None
    start = s.index("[", m.start())
    i, depth, instr, q, esc = start, 0, False, "", False
    while i < len(s):
        c = s[i]
        if instr:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == q: instr = False
        else:
            if c in "\"'`": instr, q = True, c
            elif c in "[{": depth += 1
            elif c in "]}":
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
        i += 1
    return None

def js_to_json(js):
    """JS объект литералын JSON-ға айналдыру."""
    out, i, instr, q, esc = [], 0, False, "", False
    while i < len(js):
        c = js[i]
        if instr:
            if esc:
                out.append(c); esc = False
            elif c == "\\":
                out.append(c); esc = True
            elif c == q:
                instr = False
                out.append('"')
            elif c == '"' and q != '"':
                out.append('\\"')          # айналдырылған жолдың ішіндегі тырнақшаны қорғау
            else:
                out.append(c)
            i += 1
            continue
        if c in "\"'`":
            instr, q = True, c
            out.append('"' if c != '"' else c)
            i += 1
            continue
        # !1 / !0 → false / true
        if c == "!" and i + 1 < len(js) and js[i+1] in "01":
            out.append("false" if js[i+1] == "1" else "true")
            i += 2
            continue
        # void 0 → null
        if js.startswith("void 0", i):
            out.append("null"); i += 6; continue
        # тырнақсыз кілт
        m = re.match(r'([A-Za-z_$][A-Za-z0-9_$]*)\s*:', js[i:])
        if m and (not out or out[-1] in "{,"):
            out.append('"%s":' % m.group(1)); i += m.end(); continue
        out.append(c); i += 1
    txt = "".join(out)
    txt = re.sub(r",(\s*[}\]])", r"\1", txt)   # trailing comma
    return txt

result = {}
for name, prefix in [("eras", "era_"), ("domains", "dom_"), ("techs", "tech_"),
                     ("books", "b01"), ("regions", "reg_")]:
    raw = find_array(prefix)
    if raw is None:
        print("  [жоқ] %s (prefix %s)" % (name, prefix)); continue
    try:
        result[name] = json.loads(js_to_json(raw))
        print("  [ok] %-9s %4d жазба, %7d таңба" % (name, len(result[name]), len(raw)))
    except Exception as e:
        print("  [қате] %s: %s" % (name, e))
        io.open("/tmp/claude-0/-home-user-Buldirshin/881ce800-46cf-53ba-84b3-c1ac9ccbdc46/scratchpad/fail_%s.json" % name, "w", encoding="utf-8").write(js_to_json(raw))

out = "/tmp/claude-0/-home-user-Buldirshin/881ce800-46cf-53ba-84b3-c1ac9ccbdc46/scratchpad/atlas_data.json"
io.open(out, "w", encoding="utf-8").write(json.dumps(result, ensure_ascii=False, indent=1))
print("жазылды:", out)
