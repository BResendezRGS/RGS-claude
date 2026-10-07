"""Resolve description sections from Listing Content Library records.
A renderable block is a record that has an icon + heading. 'Authority' records (instruction text, no icon) are not rendered."""
import re, html as _html
OK_STATUS = {"Active", "Approved", "Testing"}

def norm(s): return re.sub(r"\s+", " ", _html.unescape(s or "")).strip().lower()

def heading_of(rec):
    first = (rec.get("plain") or "").split("\n", 1)[0]
    icon = (rec.get("icon") or "").strip()
    if not icon and not re.match(r"^[^\w\s]", first): return None
    return norm(re.sub(r"^[^\w]+", "", first)) if first else None

def codes_of(rec):
    return {c.strip() for c in re.split(r"[;,]", rec.get("codes") or "") if c.strip()}

def fix_amp(h):
    return re.sub(r"&(?!(?:[a-zA-Z]+|#\d+);)", "&amp;", h)

def body_html(rec):
    if rec.get("html"): return fix_amp(rec["html"])
    lines = (rec.get("plain") or "").split("\n")
    head, body = lines[0], [l for l in lines[1:] if l.strip()]
    return "<h3>%s</h3>%s" % (_html.escape(head, quote=False), "".join("<p>%s</p>" % _html.escape(l, quote=False) for l in body))

class Resolver:
    def __init__(self, library, collection, product, log):
        self.lib, self.coll, self.prod, self.log = library, collection, product, log

    def pick(self, title, market, lead=None):
        best, trace = [], []
        for r in self.lib:
            if r.get("status") not in OK_STATUS: continue
            if market not in (r.get("mk") or []): continue
            if heading_of(r) != norm(title): continue
            cs = codes_of(r)
            if self.coll in cs: spec = 3
            elif self.prod in cs: spec = 2
            elif "ALL" in cs or r.get("scope") == "Global": spec = 1
            else: continue
            m = re.search(r"lead design D0(\d)", r.get("vars") or "")
            if m and lead is not None and int(m.group(1)) != lead: continue
            if m and lead is None: continue
            best.append((spec, r))
        if not best: return None
        top = max(s for s, _ in best)
        win = [r for s, r in best if s == top]
        if len(win) > 1:
            self.log.append(("CONFLICT", title, market, "multiple records at same specificity: " + ", ".join(r["id"] for r in win)))
            return None
        r = win[0]
        if r["status"] != "Active": self.log.append(("REVIEW", title, market, "%s is status %s" % (r["id"], r["status"])))
        return r

    def build(self, manifest, market, lead):
        recs, missing = [], []
        for t in manifest:
            r = self.pick(t, market, lead)
            if r is None: missing.append(t)
            recs.append((t, r))
        return recs, missing

def plain_block(r):
    p = r["plain"].strip("\n"); icon = (r.get("icon") or "").strip()
    first = p.split("\n", 1)[0]
    if icon and not first.startswith(icon):      # some records keep the icon in its own field (e.g. ORN)
        p = icon + " " + p
    return p

def etsy_text(recs):
    return "\n\n".join(plain_block(r) for t, r in recs if r)

def shop_html(recs):
    return "".join(body_html(r) for t, r in recs if r)
