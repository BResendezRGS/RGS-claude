"""Amazon flat-file builder: 1 non-buyable parent + one child per design, all content resolved from Airtable snapshot.
Output is injected directly into the multi-category .xlsm template XML (openpyxl cannot round-trip this template)."""
import re, os, copy, zipfile, collections
from lxml import etree
from openpyxl.utils import get_column_letter as L, column_index_from_string as CI
from . import content as C

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"; q = lambda t: "{%s}%s" % (NS, t)
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
KEYS = ["TITLE", "HIGHLIGHT", "MODEL NAME", "BACKEND", "BULLET 1", "BULLET 2", "BULLET 3", "BULLET 4", "BULLET 5", "DESCRIPTION"]

def parse_block(rec):
    d = {}
    for line in (rec["plain"] or "").split("\n")[1:]:
        k, _, v = line.partition(": ")
        if k in KEYS: d[k] = v.strip()
    return d

def collect(run):
    """Return rows [(level, design_no, data)] and log blockers."""
    cfg, a = run.cfg, run.cfg["amazon"]; lib = {r["id"]: r for r in run.lib}
    out = []
    for tag in ["PARENT"] + ["D%02d" % i for i in range(1, cfg["design_count_rotating"] + 2)]:
        rid = a["content_prefix"] + tag; rec = lib.get(rid)
        if not rec or rec.get("status") not in C.OK_STATUS or "Amazon" not in (rec.get("mk") or []):
            run.log.append(("BLOCKER", "Content Library", tag, "no usable Amazon content record %s" % rid)); continue
        if rec["status"] != "Active": run.log.append(("REVIEW", "Amazon " + tag, "Amazon", "%s is status %s" % (rid, rec["status"])))
        d = parse_block(rec); miss = [k for k in KEYS if not d.get(k)]
        if miss: run.log.append(("BLOCKER", "Content Library", tag, "%s missing %s" % (rid, ", ".join(miss)))); continue
        out.append((tag, d, rid))
    return out

def handling_days(run):
    rec = {r["id"]: r for r in run.lib}.get(run.cfg["amazon"]["production_record"])
    if not rec or rec.get("status") not in C.OK_STATUS:
        run.log.append(("BLOCKER", "Content Library", "Amazon", "production record %s not usable" % run.cfg["amazon"]["production_record"])); return None
    nums = re.findall(r"(\d+)\s+business", rec["plain"])
    if not nums: run.log.append(("BLOCKER", "Content Library", "Amazon", "no 'N business days' in production record")); return None
    if rec["status"] != "Active": run.log.append(("REVIEW", "Production", "Amazon", "%s is status %s" % (rec["id"], rec["status"])))
    return int(nums[-1])

def gate(run, rows):
    a = run.cfg["amazon"]
    for tag, d, rid in rows:
        t = d["TITLE"]
        if len(t) > a["title_max"]: run.log.append(("BLOCKER", "Amazon title", tag, "%d chars > %d" % (len(t), a["title_max"])))
        if "resendez" in t.lower(): run.log.append(("BLOCKER", "Amazon title", tag, "brand name in title"))
        if len(d["HIGHLIGHT"]) > a["highlight_max"]: run.log.append(("BLOCKER", "Amazon highlight", tag, "%d chars > %d" % (len(d["HIGHLIGHT"]), a["highlight_max"])))
        if len(d["BACKEND"].encode()) > a["backend_max_bytes"]: run.log.append(("BLOCKER", "Amazon backend", tag, "%d bytes > %d" % (len(d["BACKEND"].encode()), a["backend_max_bytes"])))
        for k in ("TITLE", "HIGHLIGHT", "DESCRIPTION", *["BULLET %d" % i for i in range(1, 6)]):
            if re.search(r"AI-generated|created with the assistance of AI|AI disclosure", d[k], re.I): run.log.append(("BLOCKER", "Amazon copy", tag, "AI disclosure text in %s (Amazon excluded)" % k))
        w = collections.Counter(re.findall(r"[a-z0-9']+", t.lower())); mx = max(w.items(), key=lambda x: x[1])
        if mx[1] > 2: run.log.append(("WARN", "Amazon title", tag, "word '%s' appears %d times" % mx))
        run.checks.append(("Amazon", "title<=%d, no brand, highlight<=%d, backend<=%dB, no AI text" % (a["title_max"], a["highlight_max"], a["backend_max_bytes"]), tag,
                           "FAIL" if any(l[0] == "BLOCKER" and l[2] == tag for l in run.log) else "PASS", "title %d chars, highlight %d, backend %dB" % (len(t), len(d["HIGHLIGHT"]), len(d["BACKEND"].encode()))))
    titles = [d["TITLE"] for _, d, _ in rows]
    run.checks.append(("Amazon", "titles distinct", "all", "PASS" if len(set(titles)) == len(titles) else "FAIL", ""))
    run.log.append(("HOLD", "Amazon images", run.cfg["collection"], a["main_images_source"]))

def values(run, rows, days):
    cfg, a = run.cfg, run.cfg["amazon"]; coll = cfg["collection"]; V = {}
    for i, (tag, d, rid) in enumerate(rows):
        r = a["first_row"] + i; put = lambda col, v: V.__setitem__((r, CI(col)), v)
        if tag == "PARENT":
            for k, v in a["parent_constants"].items(): put(k, v)
            put("A", coll)
        else:
            n = int(tag[1:]); dn = "%02d" % n
            first = run.cfg["parents"][0]; sku = run.sku[(first, n)]["Vendor SKU"] if (first, n) in run.sku else None
            if sku is None: sku = next(s["Vendor SKU"] for (p, dd), s in run.sku.items() if dd == n)
            for k, v in a["child_constants"].items(): put(k, v)
            put("A", sku); put("E", coll)
            put("U", "%s-%s" % (coll, dn)); put("BR", "%s-%s" % (coll, dn))
            put("ES", cfg["relationship_names"][str(n)].replace(a["design_name_strip"], ""))
            ready = n == cfg["ready_made_design"]
            price = run.price("Amazon", n)
            put("JU", price); put("KX", price); put("KU", days); put("Z", a["main_images"][dn])
        put("G", d["TITLE"]); put("H", d["HIGHLIGHT"]); put("V", d["MODEL NAME"]); put("AQ", d["BACKEND"]); put("AK", d["DESCRIPTION"])
        for j, c in enumerate(["AL", "AM", "AN", "AO", "AP"], 1): put(c, d["BULLET %d" % j])
    return V

def inject(template, out, V, first, nrows, proto, max_col):
    z = zipfile.ZipFile(template)
    wbx = etree.fromstring(z.read("xl/workbook.xml")); rels = etree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid = [s.get("{%s}id" % RNS) for s in wbx.iter(q("sheet")) if s.get("name") == "Template"][0]
    tgt = [r.get("Target") for r in rels if r.get("Id") == rid][0]
    path = tgt.lstrip("/") if tgt.startswith("/") else "xl/" + tgt
    sx = etree.fromstring(z.read(path)); ss = etree.fromstring(z.read("xl/sharedStrings.xml")); sd = sx.find(q("sheetData"))
    rows = {int(r.get("r")): r for r in sd}; tmpl = copy.deepcopy(rows[proto])
    def blank(r):
        n = copy.deepcopy(tmpl)
        for c in n:
            for ch in list(c): c.remove(ch)
            if "t" in c.attrib: del c.attrib["t"]
            c.set("r", "%s%d" % (re.match(r"[A-Z]+", c.get("r")).group(0), r))
        n.set("r", str(r)); return n
    last = first + nrows - 1
    for r in range(first, last + 1):
        n = blank(r)
        if r in rows: sd.replace(rows[r], n)
        else: sd.append(n)
        rows[r] = n
    for e in sorted(list(sd), key=lambda e: int(e.get("r"))): sd.remove(e); sd.append(e)
    for e in list(sd):
        if int(e.get("r")) > last: sd.remove(e)
    u0 = len(ss.findall(q("si"))); cnt0 = int(ss.get("count", "0")); sidx = {}; ns = 0
    def sstr(s):
        if s not in sidx:
            si = etree.SubElement(ss, q("si")); t = etree.SubElement(si, q("t")); t.text = s
            if s != s.strip() or "  " in s: t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            sidx[s] = u0 + len(sidx)
        return sidx[s]
    for (r, c), v in V.items():
        cell = next((e for e in rows[r] if e.get("r") == "%s%d" % (L(c), r)), None)
        if cell is None:
            cell = etree.SubElement(rows[r], q("c")); cell.set("r", "%s%d" % (L(c), r))
            cs = sorted(rows[r], key=lambda e: CI(re.match(r"[A-Z]+", e.get("r")).group(0)))
            for e in list(rows[r]): rows[r].remove(e)
            for e in cs: rows[r].append(e)
        vv = etree.SubElement(cell, q("v"))
        if isinstance(v, str): cell.set("t", "s"); vv.text = str(sstr(v)); ns += 1
        else: vv.text = repr(v)
    ss.set("count", str(cnt0 + ns)); ss.set("uniqueCount", str(u0 + len(sidx)))
    dim = sx.find(q("dimension"))
    if dim is not None: dim.set("ref", "A1:%s%d" % (L(max_col), last))
    zo = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    for it in z.infolist():
        data = z.read(it.filename)
        if it.filename == path: data = etree.tostring(sx, xml_declaration=True, encoding="UTF-8", standalone=True)
        elif it.filename == "xl/sharedStrings.xml": data = etree.tostring(ss, xml_declaration=True, encoding="UTF-8", standalone=True)
        zo.writestr(it, data)
    zo.close()

def build(run, out):
    a = run.cfg["amazon"]; rows = collect(run); days = handling_days(run)
    gate(run, rows)
    if any(l[0] == "BLOCKER" for l in run.log) and not getattr(run, "force", False): return False
    V = values(run, rows, days)
    inject(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), a["template"]), out, V, a["first_row"], len(rows), a["proto_row"], a["max_col"])
    run.amz_rows = rows; return True
