# RGS Listing Pipeline (Airtable-driven)

Builds Etsy bulk-load and Shopify Matrixify files for one collection at a time. Copy comes from the **Listing Content Library**
(`tblIpSTghIByDJ4Kx`), identity from **SKU Registries**, titles/tags/SEO from **Listing Build Staging**, images from **Image URL Console**.
Nothing is typed into scripts. Airtable (base `app3KgtSsu3GbgPQQ`) stays the source of truth.

## Standing rules (operator decision 2026-10-07, enforced in `rgs/rules.py`)
1. **Listing structure: one parent per collection, carrying all 7 designs (DESIGN A-G).** Parent identifier = collection code (registry parent row `RGS SKU` = collection code; children `<COLLECTION>-01..07`). Child SKU keys for staging and Image URL Console rows are `<COLLECTION>-0N`. Configs no longer need `parents`. SOR-26-050 keeps its six rotating `-P0N` parents (`"listing_structure": "rotating_parents"` in its config).
2. **Production partner defaults to ICP (InnerCircle Prints) for SOR and ORN.** Set `production_partner` in the config only when the operator names a different partner.
3. **Design 07 = DESIGN G is the ready-made, non-personalized design on every product**, always the last variant. The gate blocks any config that says otherwise.
Each default that gets applied is written to the Run_Log as INFO. Test: `python3 tests/test_single_parent.py` (14 checks). Verified 2026-10-07: SOR-26-050 output unchanged after the change (47,330 cells, both parent-SKU modes, 0 differences).

## Run order
1. **Pull a snapshot** (Claude does this through the Airtable connector) -> `snapshots/<COLLECTION>.json` with four tables:
   `Listing Build Staging`, `SKU Registries`, `Image URL Console`, `Listing Content Library` (filter by collection / product code, plus global records).
2. **Gate + build**: `python3 run.py --collection SOR-26-050 --out out`
   - Readiness gate stops the run (exit 2) on any BLOCKER: missing Library section, no vendor `apod-*` SKU, missing handle, missing lead-design images, ambiguous staging text, same-rank Library conflicts.
   - REVIEW = Library record is status Testing (usable, but not yet approved). HOLD = built, but a flag is forced (e.g. `overwrite_images` FALSE).
3. **Read `<COLLECTION>_Run_Report.xlsx`**: Run_Log, Checks, Sources (every section traced to its Library record ID/status/version).
4. Upload Etsy file (test one listing first when `parent_sku_mode = collection`), then Shopify file.

## How copy is chosen
Each manifest section (e.g. "Key Features") is matched by heading to Library records that are status Active/Approved/Testing, include the marketplace, and apply to the collection.
Specificity wins: collection code (Niche Specific) > product code (Product Specific) > Global. Records whose `Variables Used` says `lead design D0N` apply only to the parent with that lead design.
Same-rank duplicates are a CONFLICT (blocker). Authority records without an icon/heading (e.g. `LCL-SOR-26-050-DESC-001`) are instructions, not rendered blocks.

## Adding a collection
1. Make sure the Library has records for the product (`<PRD>`) and, where copy varies by design, collection records.
2. Copy `collections/SOR-26-050.json`, delete `listing_structure`, `listing_structure_note` and `parents` (single parent is now the default), then change codes, relationship names, manifest, Pricing Registry IDs (ICP records), shipping profile and dimensions.
3. Pull the snapshot, run, fix BLOCKERs in Airtable (not in this folder), re-pull, re-run.

## Regression
`python3 run.py --collection SOR-26-050 --parent-sku-mode registry --out out_reg` then `python3 tests/regress_sor_26_050.py`
Result 2026-10-07: 918 Etsy / 774 Shopify cells compared; only the six `description` / `Body HTML` cells differ, and only in Production and Please Note
(Library wording replaces the dry-run's unsupported "made to order" line).

## Still hardcoded in `collections/*.json` (source noted in the file) - next to move into Airtable
shipping profile, dimensions, section manifests (Listing Assembly Rules `LAR-*-DESC-MANIFEST-001`), relationship names (Design Registry), Shopify D07 price (gap G13).
## Amazon (added 2026-10-07)
`rgs/amazon.py` builds the multi-category .xlsm (1 non-buyable parent keyed to the collection code + one child per design, theme COLLECTION_ITEM, design name in the variant column).
Copy comes from Library records `LCL-<COLLECTION>-AMZ-PARENT` / `-D01..D07` (TITLE, HIGHLIGHT, MODEL NAME, BACKEND, 5 bullets, DESCRIPTION); handling time is parsed from `LCL-SOR-DESC-011-AMZ` (4 business days).
Gate blocks on: title >75, brand in title, highlight >125, backend >250 bytes, AI-disclosure text, missing record/field. Writes into the template XML directly (openpyxl cannot round-trip this template). Image columns beyond main image are never written, so existing images are preserved on refresh.
Regression `tests/regress_amazon_sor_26_050.py`: 513 cells, 1 difference (Design 07 description opening fixed from "The Bestie (ready-made) ornament").
Still HOLD: main images (placeholder URLs from the submitted file) until corrected in Airtable.

## Pricing
All three builders read the Pricing Registry: `Launch Price` if set, else `Target Price` (records per marketplace for rotating designs and the ready-made design, mapped in `collections/*.json -> pricing`). SOR launch prices set 2026-10-07: 14.98 (Designs A-F), 9.99 (DESIGN G) on Etsy, Shopify and Amazon. The Phase 1 refresh (existing listings, Category Listings Report, rule changes) is a separate, tabled workstream.
