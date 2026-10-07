"""Standing RGS listing rules (operator decision 2026-10-07). Applied to every collection config before a run.
A collection config may override a default only by stating the value explicitly; every default applied is written to the run log.

1. Listing structure: one parent per collection carrying all 7 designs (A-G). The parent identifier is the collection code
   (registry row RGS SKU == RGS Parent SKU == collection code, children <COLLECTION>-01..07). SOR-26-050 was built before
   this rule with six rotating -P0N parents and keeps that structure by stating "listing_structure": "rotating_parents".
2. Production partner: ICP (InnerCircle Prints) for SOR and ORN unless the operator names a different partner in the config.
3. Ready-made design: Design 07 = DESIGN G on every product (no personalization, always the last variant).
"""

PARTNERS = {"ICP": {"name": "InnerCircle Prints"}}

DEFAULTS = {
    "listing_structure": "single_parent",   # or "rotating_parents" (legacy, SOR-26-050)
    "production_partner": "ICP",
    "ready_made_design": 7,
    "design_letters": "ABCDEFG",
    "design_count_rotating": 6,
}
DEFAULT_PARTNER_PRODUCTS = {"SOR", "ORN"}


def apply(cfg, log):
    for k, v in DEFAULTS.items():
        if k == "production_partner" and cfg.get("product_code") not in DEFAULT_PARTNER_PRODUCTS:
            continue
        if k not in cfg:
            cfg[k] = v
            log.append(("INFO", "Rules", cfg.get("collection", ""), "default %s = %s (rgs/rules.py)" % (k, v)))
    if cfg["listing_structure"] == "single_parent" and "parents" not in cfg:
        cfg["parents"] = [cfg["collection"]]
    p = PARTNERS.get(cfg.get("production_partner"))
    if p and "shopify" in cfg and "production_partner" not in cfg["shopify"]:
        cfg["shopify"]["production_partner"] = p["name"]
    if cfg["ready_made_design"] != 7 or cfg["design_letters"][cfg["ready_made_design"] - 1] != "G":
        log.append(("BLOCKER", "Rules", cfg.get("collection", ""), "ready-made design must be Design 07 = DESIGN G"))
    if cfg["listing_structure"] == "single_parent" and cfg["parents"] != [cfg["collection"]]:
        log.append(("BLOCKER", "Rules", cfg.get("collection", ""), "single_parent structure requires parents == [collection code]"))
    return cfg
