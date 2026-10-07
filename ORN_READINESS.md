# ORN readiness (2026-10-07)

| Area | Status | Detail |
|---|---|---|
| Library copy | READY | All 13 Etsy / 12 Shopify manifest sections resolve to Active ORN records (LCL-ORN-DESC-001..013). Please Note is `LCL-ORN-DESC-012`. AI Disclosure is ORN-specific `LCL-ORN-DESC-013` and outranks the global record, so wording differs from SOR. |
| Pipeline | READY after config | Needs `collections/ORN-*.json` (collection codes, parent/lead rule, relationship names, prices, profile). Uses the same resolver. |
| Product facts | CHECK | ORN specs differ from SOR (shape, size, packaging). Library records carry ORN facts; do not reuse SOR config values. |
| Image mapping | GAP | No ORN image mapping rule in Airtable (SOR has one). Image URL Console rows must exist per collection/lead design. |
| SKU registry | GAP | ~1,770 registry SKUs carry the `-P##` suffix; parent SKU must be re-keyed to the collection code before `parent_sku_mode = collection` is trustworthy. |
| Vendor SKUs | GAP | Some ORN registry rows have incomplete Vendor SKU (`apod-*`); the readiness gate will block those parents. |
| Staging text | UNKNOWN | Titles/tags/SEO must exist in Listing Build Staging per parent; check after first snapshot. |
| Open decisions | | Production wording ("1-3 business days") vs shipping-promise exclusion rule; Etsy parent_sku merge test. |
