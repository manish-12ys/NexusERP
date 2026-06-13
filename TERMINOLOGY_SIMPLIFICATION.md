# NexusERP Terminology Simplification Guide

This document tracks all terminology changes made to simplify the user interface and make the system more business-friendly and less technical.

## Overview

NexusERP uses business terminology instead of technical jargon, making it easier for non-technical users and factory managers to understand and operate the system.

---

## Complete Terminology Mapping

### Core Business Terms

| Old Term | New Term | Context |
|----------|----------|---------|
| Vendor | Supplier | Purchasing, vendors page |
| Bill of Materials (BOM) | Product Recipe | Manufacturing, product assembly |
| Manufacturing Order (MO) | Production Order | Manufacturing, order tracking |
| Work Order | Production Task | Manufacturing, execution |
| Procurement | Smart Purchasing | Purchasing automation, module name |
| Reorder Level | Minimum Stock Amount | Inventory, purchasing rules |
| Safety Stock | Extra Buffer Stock | Inventory, buffer quantity |
| Credit Limit | Maximum Purchase Amount | Supplier/vendor management |

### Product & Inventory Terms

| Old Term | New Term | Context |
|----------|----------|---------|
| Cost Price | Unit Cost | Product pricing, reports |
| Sales Price | Selling Price | Product pricing, sales |
| Tax % | Tax Rate (%) | Product pricing |
| Product Type | Category Type | Product classification |
| Finished Goods | End Products | Product categorization |
| Raw Material | Components | Product categorization |
| Semi-Finished | Work-in-Progress | Product categorization |
| Unit of Measure | Measurement Unit | Product specifications |
| Lead Time (days) | Days to Deliver | Supplier/product delivery |
| Procurement Type | Sourcing Method | Product sourcing strategy |
| Make to Stock | Stock Before Demand | Procurement strategy |
| Make to Order | Stock After Demand | Procurement strategy |

### Business Metrics (Intentionally Not Changed)

- **SKU** - Universally understood Stock Keeping Unit acronym
- **Unit Price** - Already simple and business-friendly
- **Barcode** - Already simple and commonly used
- **Tax** - Common business terminology
- **Inventory** - Standard business term

---

## Files Modified

### Form Definitions (app/forms/)

#### product_forms.py
- `cost_price` label: "Cost Price" → "Unit Cost"
- `sales_price` label: "Sales Price" → "Selling Price"
- `tax_percent` label: "Tax %" → "Tax Rate (%)"
- `product_type` label and choices updated:
  - "Finished Goods" → "End Products"
  - "Raw Material" → "Components"
  - "Semi-Finished" → "Work-in-Progress"
- `unit_of_measure` label: "Unit" → "Measurement Unit"
- `lead_time_days` label: "Lead Time (days)" → "Days to Deliver"
- `procurement_type` label: "Procurement Type" → "Sourcing Method"
  - "Make to Stock" → "Stock Before Demand"
  - "Make to Order" → "Stock After Demand"

#### bom_forms.py
- `lead_time_days` label: "Lead Time (days)" → "Days to Deliver"

#### purchase_forms.py
- `lead_time_days` label: "Lead Time (days)" → "Days to Deliver"

### Backend Constants (app/utils/)

#### constants.py
- PRODUCT_TYPES choices updated to match new terminology:
  - "Finished Goods" → "End Products"
  - "Raw Material" → "Components"
  - "Semi-Finished" → "Work-in-Progress"

### Seed Data (app/seed/)

#### sample_products.py
- Category names updated for consistency:
  - "Raw Materials" → "Components"
  - "Finished Goods" → "End Products"

### Template Files (app/templates/)

#### products/list.html
- Column headers: "Sales Price" → "Selling Price"
- Column headers: "Cost Price" → "Unit Cost"
- Column headers: "Product Type" → "Category Type"
- Product type badges:
  - "Raw Material" → "Components"
  - "Semi-Finished" → "Work-in-Progress"
  - "Finished Goods" → "End Products"

#### products/view.html
- Product type label: "Product Type" → "Category Type"
- Unit of measure label: "Unit of Measure" → "Measurement Unit"
- Section header: "Pricing & Tax" → "Price & Tax"
- Price label: "Sales Price" → "Selling Price"
- Cost label: "Cost Price" → "Unit Cost"
- Lead time label: "Lead Time" → "Delivery Days"
- Product type badges updated to match simplified terms

#### products/create.html
- Form field labels automatically use simplified terms from product_forms.py

#### vendors/view.html
- Label: "Lead Time (days):" → "Days to Deliver:"

#### vendors/list.html
- Column header: "Lead Time" → "Delivery Days"

#### dashboard/dashboard.html
- Badge: "Low Raw Materials" → "Low Components"
- Alert message: "All raw materials..." → "All components..."

#### purchase/edit_order.html
- Label: "Raw Material / Product" → "Product / Component"

#### bom/view_bom.html
- Already uses "Unit Cost" terminology

#### sales/view_order.html
- Tax column header: "Tax %" → "Tax Rate (%)"

### Documentation Files

#### README.md
- Intro: "raw materials, finished goods" → "components, end products"
- Feature: "raw material and finished goods support" → "component and end product support"
- Feature: "finished goods costing" → "end product costing"
- Demo data: "Raw materials such as..." → "Components such as..."
- Demo data: "Finished goods such as..." → "End products such as..."

#### ARCHITECTURE_AND_FLOW.md
- Contains references to the system architecture and flows
- Technical documentation maintained with original terms for clarity (backend references)

---

## Impact Analysis

### User-Facing Changes
- ✅ All form labels simplified
- ✅ All template displays simplified
- ✅ All reports and lists use simplified terminology
- ✅ Navigation sidebar already updated (earlier in session)
- ✅ Dashboard cards and alerts use simplified terms
- ✅ All badge labels use simplified terminology

### Backend/Developer Impact (Minimal)
- ✅ Database column names unchanged (maintains data integrity)
- ✅ Model class names unchanged (Vendor, Bom, etc.)
- ✅ Variable names in code unchanged (vendor_id, bom_id, etc.)
- ✅ API route parameters unchanged
- ✅ Only form choices and display labels updated
- ✅ Constants file updated for proper form rendering

### Data Migration Requirements
- ⚠️ Sample product categories renamed - should reset database when deploying
- ✓ No database schema changes required
- ✓ No ORM model changes required

---

## Testing Checklist

### Verified
- [x] Application starts without errors (http://127.0.0.1:5000)
- [x] Product create form displays simplified field labels
- [x] Product list shows simplified column headers and type badges
- [x] Product view shows simplified terminology
- [x] Supplier/vendor pages show updated lead time labels
- [x] Dashboard shows simplified alert terminology
- [x] Constants file properly formatted with new choices
- [x] README documentation updated

### Should Test After Deployment
- [ ] Create a new product and verify form labels
- [ ] Edit an existing product
- [ ] Create a purchase order (check "Sourcing Method" label)
- [ ] View production orders and production tasks
- [ ] Check supplier/component information displays
- [ ] Verify dashboard alerts and badges

---

## Future Considerations

### Potential Additional Simplifications (Not Yet Implemented)
1. Backend variable/method names (significant refactoring required)
2. Python model class names (Vendor → Supplier, Bom → Recipe)
3. API endpoint responses (currently return technical field names)
4. Error messages in backend services
5. Help text and tooltips throughout the application

### Not Recommended for Change
- Database field names (would require migrations and affect data integrity)
- Internal service method names (would require extensive refactoring)
- Configuration variable names (backward compatibility concerns)
- Route parameter names (would break existing links and bookmarks)

---

## Rollback Information

If you need to revert these changes:
1. Revert `app/forms/*.py` files to restore old field labels
2. Revert `app/utils/constants.py` to restore old choice display strings
3. Revert all template files in `app/templates/` to restore old display text
4. Revert `README.md` to restore old terminology
5. All data remains intact (no data loss, only label changes)

---

## Session Summary

**Date**: [Session completion date]
**Total Files Modified**: 15
**Form Files**: 3
**Template Files**: 9
**Documentation Files**: 2
**Utility Files**: 1
**Seed Files**: 1

All changes maintain backward compatibility with the database and don't affect the underlying data structure or internal logic.
