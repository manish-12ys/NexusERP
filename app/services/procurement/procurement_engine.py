"""
procurement_engine.py
Smart Procurement Autopilot — execution engine.

Supports three modes:
  manual     → analyze only, no documents created
  semi       → create draft POs/MOs for manager review
  auto       → create and confirm POs automatically

Vendor selection is scored (cost 40%, lead-time 35%, rating 25%).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db
from app.models.inventory import Inventory
from app.models.manufacturing_order import ManufacturingOrder
from app.models.procurement_request import ProcurementRequest
from app.models.procurement_rule import ProcurementRule
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.vendor import Vendor
from app.models.stock_transfer import StockTransfer
from app.services.inventory.inventory_service import InventoryService


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProcurementEngine:
    """
    Run the replenishment engine against all active products.

    mode: 'manual' | 'semi' | 'auto'
      - manual  → log shortages, NO documents created
      - semi    → create draft PO / draft MO (manager approves)
      - auto    → create + confirm PO automatically

    Returns a summary dict with counts per category.
    """

    def run(self, mode: str = "semi") -> dict:
        from app.services.procurement.autopilot_service import AutopilotService

        svc = AutopilotService()
        products = Product.query.filter_by(is_active=True).all()

        counts = {
            "pos_created": 0,
            "mos_created": 0,
            "requests_created": 0,
            "skipped_ok": 0,
            "skipped_existing": 0,
        }

        for product in products:
            inventories = product.inventories
            if not inventories:
                inventories = [None]  # default virtual inventory

            for inv in inventories:
                analysis = svc.analyze_product(product, inv)

                # Skip items with no action needed
                if analysis["tier"] == "ok":
                    counts["skipped_ok"] += 1
                    continue

                needed_qty = analysis["recommended_qty"]
                if needed_qty <= 0:
                    counts["skipped_ok"] += 1
                    continue

                # Apply rule min-order constraint
                rule = ProcurementRule.query.filter_by(
                    product_id=product.id, is_active=True
                ).first()
                if rule and rule.min_order_qty:
                    needed_qty = max(needed_qty, rule.min_order_qty)

                shortage_wh = analysis["warehouse"]
                shortage_loc = analysis["location"]

                # Skip if open request already exists for this specific location
                existing = ProcurementRequest.query.filter_by(
                    product_id=product.id,
                    warehouse=shortage_wh,
                    location=shortage_loc,
                    status="open"
                ).first()
                if existing:
                    counts["skipped_existing"] += 1
                    continue

                # In manual mode: create request record only (no PO/MO)
                if mode == "manual":
                    req = ProcurementRequest(
                        request_number=self._gen_pr_number(),
                        product_id=product.id,
                        quantity=needed_qty,
                        source_type="manual",
                        warehouse=shortage_wh,
                        location=shortage_loc,
                        status="open",
                        notes=(
                            f"[Autopilot / MANUAL] Tier={analysis['tier'].upper()}. "
                            f"Shortage={analysis['shortage']} {analysis['unit']} at {shortage_wh}:{shortage_loc}. "
                            f"No document auto-created — awaiting purchase manager action."
                        ),
                    )
                    db.session.add(req)
                    counts["requests_created"] += 1
                    continue

                # Check for surplus in other warehouses/phases
                surplus_locs = InventoryService.find_surplus_locations(
                    product.id, exclude_warehouse=shortage_wh, exclude_location=shortage_loc
                )

                if surplus_locs:
                    best_source = surplus_locs[0]
                    transfer_qty = min(needed_qty, best_source["surplus_qty"])
                    
                    from app.services.inventory.transfer_service import TransferService
                    transfer_notes = (
                        f"Autopilot suggested transfer to cover shortage of {needed_qty} "
                        f"at {shortage_wh}:{shortage_loc}."
                    )
                    
                    transfer, err = TransferService.create_transfer(
                        product_id=product.id,
                        quantity=transfer_qty,
                        from_wh=best_source["warehouse"],
                        from_loc=best_source["location"],
                        to_wh=shortage_wh,
                        to_loc=shortage_loc,
                        notes=transfer_notes
                    )
                    
                    if transfer:
                        if mode == "auto":
                            success, exec_err = TransferService.execute_transfer(transfer.id)
                            if success:
                                transfer_notes += " [AUTO-EXECUTED]"
                                transfer.notes = transfer_notes
                                db.session.commit()
                        
                        req = ProcurementRequest(
                            request_number=self._gen_pr_number(),
                            product_id=product.id,
                            quantity=transfer_qty,
                            source_type="transfer",
                            stock_transfer_id=transfer.id,
                            warehouse=shortage_wh,
                            location=shortage_loc,
                            status="open",
                            notes=(
                                f"[Autopilot / {mode.upper()}] "
                                f"Tier={analysis['tier'].upper()}. "
                                f"Internal Transfer recommended from {best_source['warehouse']}:{best_source['location']}."
                            ),
                        )
                        db.session.add(req)
                        counts["requests_created"] += 1
                        
                        if transfer_qty >= needed_qty:
                            continue
                        else:
                            needed_qty -= transfer_qty

                # Determine source: manufacture (has BOM) vs purchase
                is_manufacture = (
                    product.bom is not None
                    or (rule and rule.source_type == "manufacture")
                )

                if is_manufacture:
                    bom_id = (
                        product.bom.id if product.bom
                        else (rule.bom_id if rule else None)
                    )
                    mo = ManufacturingOrder(
                        mo_number=self._gen_mo_number(),
                        product_id=product.id,
                        bom_id=bom_id,
                        quantity=needed_qty,
                        warehouse=shortage_wh,
                        location=shortage_loc,
                        status="draft",
                        notes=(
                            f"[Autopilot / {mode.upper()}] "
                            f"Tier={analysis['tier'].upper()}. "
                            f"Shortage={analysis['shortage']} {analysis['unit']} at {shortage_wh}:{shortage_loc}."
                        ),
                    )
                    db.session.add(mo)
                    db.session.flush()

                    req = ProcurementRequest(
                        request_number=self._gen_pr_number(),
                        product_id=product.id,
                        quantity=needed_qty,
                        source_type="manufacture",
                        mo_id=mo.id,
                        warehouse=shortage_wh,
                        location=shortage_loc,
                        status="open",
                        notes=f"[Autopilot / {mode.upper()}] Auto-created manufacturing order.",
                    )
                    db.session.add(req)
                    counts["mos_created"] += 1
                    counts["requests_created"] += 1

                else:
                    # Select best vendor
                    vendor_info = svc.best_vendor_for(product)
                    vendor_id = vendor_info["id"] if vendor_info else None

                    # Fallback: first active vendor
                    if not vendor_id:
                        v = Vendor.query.filter_by(is_active=True).first()
                        vendor_id = v.id if v else None

                    po = None
                    if vendor_id:
                        po_status = "confirmed" if mode == "auto" else "draft"
                        po = PurchaseOrder(
                            order_number=self._gen_po_number(),
                            vendor_id=vendor_id,
                            status=po_status,
                            notes=(
                                f"[Autopilot / {mode.upper()}] "
                                f"Tier={analysis['tier'].upper()}. "
                                f"Vendor selected by scoring algorithm."
                            ),
                        )
                        if mode == "auto":
                            po.user_id = None   # system-generated

                        db.session.add(po)
                        db.session.flush()

                        line = PurchaseOrderLine(
                            purchase_order_id=po.id,
                            product_id=product.id,
                            quantity=needed_qty,
                            unit_cost=product.cost_price or 0.0,
                            line_total=needed_qty * (product.cost_price or 0.0),
                            warehouse=shortage_wh,
                            location=shortage_loc,
                        )
                        db.session.add(line)
                        po.subtotal     = line.line_total
                        po.total_amount = line.line_total

                    req = ProcurementRequest(
                        request_number=self._gen_pr_number(),
                        product_id=product.id,
                        quantity=needed_qty,
                        source_type="purchase",
                        po_id=po.id if po else None,
                        warehouse=shortage_wh,
                        location=shortage_loc,
                        status="open",
                        notes=(
                            f"[Autopilot / {mode.upper()}] "
                            f"Tier={analysis['tier'].upper()}. "
                            f"Recommended vendor: {vendor_info['name'] if vendor_info else 'none'}."
                        ),
                    )
                    db.session.add(req)
                    counts["pos_created"] += 1
                    counts["requests_created"] += 1

        db.session.commit()
        return counts

    # ── Number generators ─────────────────────────────────────────────────────

    def _gen_mo_number(self) -> str:
        from app.models.manufacturing_order import ManufacturingOrder
        last = ManufacturingOrder.query.order_by(ManufacturingOrder.id.desc()).first()
        seq  = (last.id + 1) if last else 1
        return f"MO-{_now().strftime('%Y%m')}-{seq:04d}"

    def _gen_po_number(self) -> str:
        last = PurchaseOrder.query.order_by(PurchaseOrder.id.desc()).first()
        seq  = (last.id + 1) if last else 1
        return f"PO-{_now().strftime('%Y%m')}-{seq:04d}"

    def _gen_pr_number(self) -> str:
        last = ProcurementRequest.query.order_by(ProcurementRequest.id.desc()).first()
        seq  = (last.id + 1) if last else 1
        return f"PR-{_now().strftime('%Y%m')}-{seq:04d}"
