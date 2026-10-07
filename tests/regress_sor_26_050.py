"""Regression: rebuild SOR-26-050 from Airtable snapshot (registry parent-SKU mode) and diff against the delivered dry-run workbooks.
Expected differences: Production and Please Note text only (Library wording), nothing else."""
import sys, openpyxl, difflib
D = "/tmp/claude-0/-home-claude/433e5365-a398-59b7-87cb-cf8dd3054a5e/scratchpad/"
def cells(path, sheet):
    ws = openpyxl.load_workbook(path)[sheet]
    return {(c.row, ws.cell(1, c.column).value): c.value for row in ws.iter_rows(min_row=2) for c in row if c.value not in (None, "")}
tot = {}
for name, old, new, sheet in (("Etsy", D + "SOR-26-050_Etsy_Bulk_Load_DRYRUN.xlsx", "out_reg/SOR-26-050_Etsy_Bulk_Load.xlsx", "Template"),
                              ("Shopify", D + "SOR-26-050_Shopify_Matrixify_DRYRUN.xlsx", "out_reg/SOR-26-050_Shopify_Matrixify.xlsx", "Products")):
    a, b = cells(old, sheet), cells(new, sheet)
    diffs = [(k, a.get(k), b.get(k)) for k in sorted(set(a) | set(b), key=str) if a.get(k) != b.get(k)]
    cols = {}
    for k, x, y in diffs: cols.setdefault(k[1], []).append((k[0], x, y))
    print("\n==", name, "cells compared", len(set(a) | set(b)), "differing", len(diffs), "columns", list(cols))
    for col, lst in cols.items():
        print(" column", col, "rows", [r for r, _, _ in lst])
        r, x, y = lst[0]
        for l in difflib.unified_diff(str(x).replace("<h3>", "\n<h3>").splitlines(), str(y).replace("<h3>", "\n<h3>").splitlines(), lineterm="", n=0):
            if l[:1] in "+-" and l[:3] not in ("+++", "---"): print("   ", l[:230])
