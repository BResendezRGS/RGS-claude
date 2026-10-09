"""Standing RGS listing rules. Applied to every collection config before a run.
A collection config may override a default only by stating the value explicitly; every default applied is written to the run log.

1. Listing structure (operator rule 2026-10-09, global, replaces the 2026-10-07 single-parent rule):
   six rotating parents <COLLECTION>-P01..P06 on Etsy and Shopify. Parent N leads with design N (title, tags, SEO,
   primary image) and every parent carries all 7 designs DESIGN A-G as variants. All six parents share the same
   apod vendor SKU per design. No parent is built for the ready-made design (no -P07). Amazon stays 1 parent + 7 children.
   Letter mapping is fixed (DESIGN A = design 01 ... DESIGN G = design 07 on every parent). SOR-26-050 was built with
   rotated letters (parent N's DESIGN A = design N) and keeps that by stating "letter_mapping": "rotated".
   "listing_structure": "single_parent" is still accepted when a config states it explicitly.
2. Production partner: ICP (InnerCircle Prints) for SOR and ORN unless the operator names a different partner in the config.
3. Ready-made design: Design 07 = DESIGN G on every product (no personalization, always the last variant).
"""

PARTNERS = {"ICP": {"name": "InnerCircle Prints"}}

DEFAULTS = {
    "listing_structure": "rotating_parents",   # or "single_parent" (explicit opt-in only)
    "letter_mapping": "fixed",                 # or "rotated" (legacy, SOR-26-050)
    "production_partner": "ICP",
    "ready_made_design": 7,
    "design_letters": "ABCDEFG",
    "design_count_rotating": 6,
}
DEFAULT_PARTNER_PRODUCTS = {"SOR", "ORN"}
STRUCTURES = ("rotating_parents", "single_parent")
MAPPINGS = ("fixed", "rotated")


def rotating_parents(cfg):
    return ["%s-P%02d" % (cfg["collection"], n) for n in range(1, cfg["design_count_rotating"] + 1)]


def apply(cfg, log):
    coll = cfg.get("collection", "")
    for k, v in DEFAULTS.items():
        if k == "production_partner" and cfg.get("product_code") not in DEFAULT_PARTNER_PRODUCTS:
            continue
        if k not in cfg:
            cfg[k] = v
            log.append(("INFO", "Rules", coll, "default %s = %s (rgs/rules.py)" % (k, v)))
    if cfg["listing_structure"] not in STRUCTURES:
        log.append(("BLOCKER", "Rules", coll, "unknown listing_structure %r" % cfg["listing_structure"]))
    if cfg["letter_mapping"] not in MAPPINGS:
        log.append(("BLOCKER", "Rules", coll, "unknown letter_mapping %r" % cfg["letter_mapping"]))
    if "parents" not in cfg:
        cfg["parents"] = [coll] if cfg["listing_structure"] == "single_parent" else rotating_parents(cfg)
        log.append(("INFO", "Rules", coll, "default parents = %s (rgs/rules.py)" % ", ".join(cfg["parents"])))
    p = PARTNERS.get(cfg.get("production_partner"))
    if p and "shopify" in cfg and "production_partner" not in cfg["shopify"]:
        cfg["shopify"]["production_partner"] = p["name"]
    if cfg["ready_made_design"] != 7 or cfg["design_letters"][cfg["ready_made_design"] - 1] != "G":
        log.append(("BLOCKER", "Rules", coll, "ready-made design must be Design 07 = DESIGN G"))
    if cfg["listing_structure"] == "single_parent" and cfg["parents"] != [coll]:
        log.append(("BLOCKER", "Rules", coll, "single_parent structure requires parents == [collection code]"))
    if cfg["listing_structure"] == "rotating_parents" and cfg["parents"] != rotating_parents(cfg):
        log.append(("BLOCKER", "Rules", coll, "rotating_parents requires parents == %s (no parent for the ready-made design)" % ", ".join(rotating_parents(cfg))))
    return cfg


def variant_order(cfg, lead):
    """[(letter, design)] for a parent whose lead design is `lead`. DESIGN G (ready-made) is always last."""
    n, letters = cfg["design_count_rotating"], cfg["design_letters"]
    if cfg["letter_mapping"] == "rotated":
        seq = [((lead - 1 + k) % n) + 1 for k in range(n)]
    else:
        seq = list(range(1, n + 1))
    seq.append(cfg["ready_made_design"])
    return [(letters[k], d) for k, d in enumerate(seq)]
