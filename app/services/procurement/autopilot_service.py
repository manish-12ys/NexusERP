"""
autopilot_service.py
Smart Procurement Autopilot — analysis engine.

Reads live data from: Inventory, StockLedger, Product, Vendor,
PurchaseOrder, ManufacturingOrder, SalesOrderLine.
Returns structured dicts that the route and template consume.
No external API calls — fully rule-based.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypedDict

from sqlalchemy import func

from app.extensions import db
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.procurement_request import ProcurementRequest
from app.models.purchase_order import PurchaseOrder
from app.models.stock_ledger import StockLedger
from app.models.vendor import Vendor


# ──────────────────────────────────────────────────────────────────────────────
# Tier constants
# ──────────────────────────────────────────────────────────────────────────────
TIER_CRITICAL = "critical"   # free ≤ 0  (or below safety_stock with 0 incoming)
TIER_WARNING  = "warning"    # free ≤ safety_stock
TIER_REORDER  = "reorder"    # free ≤ reorder_level
TIER_OK       = "ok"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ──────────────────────────────────────────────────────────────────────────────
class AutopilotService:
    """
    Central intelligence layer for the Procurement Command Center.
    All methods return plain Python dicts / lists — no ORM objects escape.
    """

    # ── Vendor Scoring ────────────────────────────────────────────────────────

    def score_vendor(self, vendor: Vendor, base_cost: float) -> float:
        """
        Lower score = better vendor.
        Weights: cost 40%, lead-time 35%, rating 25%.
        """
        max_cost = base_cost * 2 if base_cost else 1.0
        cost_norm    = min((base_cost / max_cost) if max_cost else 0, 1.0)
        lead_norm    = min((vendor.lead_time_days or 0) / 30.0, 1.0)
        rating       = vendor.rating or 3.0          # default mid-rating
        rating_norm  = 1.0 - (rating / 5.0)          # higher rating → lower penalty
        return cost_norm * 0.40 + lead_norm * 0.35 + rating_norm * 0.25

    def best_vendor_for(self, product: Product) -> dict | None:
        """
        Returns the best-scored vendor for a product.
        Searches: ProcurementRule → Vendors with recent POs → all active vendors.
        """
        from app.models.procurement_rule import ProcurementRule

        # 1. Check if there's a preferred vendor in a rule
        rule = ProcurementRule.query.filter_by(
            product_id=product.id, is_active=True
        ).first()
        if rule and rule.vendor_id:
            v = Vendor.query.get(rule.vendor_id)
            if v:
                return {
                    "id": v.id, "name": v.name,
                    "lead_time": v.lead_time_days or 0,
                    "rating": v.rating or 0,
                    "source": "preferred",
                }

        # 2. Find vendors who have supplied this product before
        past_vendors_ids = (
            db.session.query(PurchaseOrder.vendor_id)
            .join(PurchaseOrder.lines)
            .filter_by(product_id=product.id)
            .distinct()
            .all()
        )
        candidate_ids = [r[0] for r in past_vendors_ids]
        candidates = Vendor.query.filter(
            Vendor.id.in_(candidate_ids), Vendor.is_active == True
        ).all() if candidate_ids else []

        # 3. Fall back to all active vendors
        if not candidates:
            candidates = Vendor.query.filter_by(is_active=True).all()

        if not candidates:
            return None

        scored = sorted(
            candidates,
            key=lambda v: self.score_vendor(v, product.cost_price or 0)
        )
        best = scored[0]
        return {
            "id": best.id, "name": best.name,
            "lead_time": best.lead_time_days or 0,
            "rating": best.rating or 0,
            "source": "scored",
        }

    # ── Per-product analysis ──────────────────────────────────────────────────

    def avg_daily_consumption(self, product_id: int, days: int = 30) -> float:
        """Average daily stock-out movements over the last N days."""
        since = _now() - timedelta(days=days)
        total = (
            db.session.query(func.sum(StockLedger.quantity))
            .filter(
                StockLedger.product_id == product_id,
                StockLedger.movement_type.in_([
                    "sale", "mo_consume", "adjustment_out", "delivery"
                ]),
                StockLedger.quantity < 0,
                StockLedger.created_at >= since,
            )
            .scalar()
        ) or 0.0
        return abs(total) / days

    def analyze_product(self, product: Product, inventory: Inventory | None = None) -> dict:
        """Full analysis for a single product at a specific location."""
        inv = inventory if inventory is not None else product.inventory
        on_hand   = inv.on_hand_qty  if inv else 0.0
        reserved  = inv.reserved_qty if inv else 0.0
        incoming  = inv.incoming_qty if inv else 0.0
        warehouse = inv.warehouse    if inv else "Main"
        location  = inv.location     if inv else "Default"
        free      = max(on_hand - reserved, 0.0)
        safety    = product.safety_stock  or 0.0
        reorder   = product.reorder_level or 0.0
        lead_days = product.lead_time_days or 7

        # Tier classification
        if free <= 0 and on_hand <= 0:
            tier     = TIER_CRITICAL
            priority = 1
        elif free <= 0:
            tier     = TIER_CRITICAL
            priority = 1
        elif safety > 0 and free <= safety:
            tier     = TIER_WARNING
            priority = 2
        elif reorder > 0 and free <= reorder:
            tier     = TIER_REORDER
            priority = 3
        else:
            tier     = TIER_OK
            priority = 4

        # Shortage quantity
        shortage = max(reorder - free, 0.0) if reorder else max(-free, 0.0)

        # Recommended order qty = enough to cover reorder_level + safety buffer
        recommended_qty = max(reorder + safety - free, 0.0) if (reorder or safety) else shortage

        # Predictive: days until stockout
        avg_daily = self.avg_daily_consumption(product.id)
        if avg_daily > 0:
            days_left = free / avg_daily
        else:
            days_left = 9999  # unknown

        stockout_predicted = days_left <= (lead_days + 7) and days_left < 9999
        stockout_date = (
            (_now() + timedelta(days=days_left)).strftime("%d %b")
            if days_left < 365 else None
        )

        # Best vendor
        vendor_info = self.best_vendor_for(product) if tier != TIER_OK else None

        # Open procurement request for this specific location
        open_req = ProcurementRequest.query.filter_by(
            product_id=product.id,
            warehouse=warehouse,
            location=location,
            status="open"
        ).first()

        return {
            "id":                product.id,
            "name":              product.name,
            "sku":               product.sku,
            "product_type":      product.product_type,
            "warehouse":         warehouse,
            "location":          location,
            "on_hand":           round(on_hand, 1),
            "reserved":          round(reserved, 1),
            "free":              round(free, 1),
            "incoming":          round(incoming, 1),
            "safety_stock":      round(safety, 1),
            "reorder_level":     round(reorder, 1),
            "shortage":          round(shortage, 1),
            "recommended_qty":   round(recommended_qty, 1),
            "avg_daily":         round(avg_daily, 2),
            "days_left":         round(days_left, 1) if days_left < 9999 else None,
            "stockout_predicted":stockout_predicted,
            "stockout_date":     stockout_date,
            "lead_days":         lead_days,
            "tier":              tier,
            "priority":          priority,
            "vendor":            vendor_info,
            "open_request":      open_req.request_number if open_req else None,
            "unit":              product.unit_of_measure or "pcs",
            "cost_price":        product.cost_price or 0.0,
        }

    # ── Command Center Stats ──────────────────────────────────────────────────

    def get_command_center_stats(self) -> dict:
        """
        Single call that returns everything needed to render the dashboard:
        KPI counts, per-product analysis, pending approvals, AI advice.
        """
        products = Product.query.filter_by(is_active=True).all()
        
        analyzed = []
        for p in products:
            if p.inventories:
                for inv in p.inventories:
                    analyzed.append(self.analyze_product(p, inv))
            else:
                analyzed.append(self.analyze_product(p, None))

        # Sort by priority then shortage size
        analyzed.sort(key=lambda x: (x["priority"], -x["shortage"]))

        critical_items   = [a for a in analyzed if a["tier"] == TIER_CRITICAL]
        low_stock_items  = [a for a in analyzed if a["tier"] == TIER_WARNING]
        reorder_items    = [a for a in analyzed if a["tier"] == TIER_REORDER]
        predicted        = [a for a in analyzed if a["stockout_predicted"]]
        action_items     = [a for a in analyzed if a["tier"] != TIER_OK]

        # Today's auto-created POs
        today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
        auto_today = ProcurementRequest.query.filter(
            ProcurementRequest.created_at >= today_start,
            ProcurementRequest.notes.like("%Autopilot%"),
        ).count()

        # Pending approvals: draft POs and pending stock transfers linked to open requests
        pending_reqs = ProcurementRequest.query.filter(
            ProcurementRequest.status == "open",
            ProcurementRequest.source_type.in_(["purchase", "transfer"])
        ).order_by(ProcurementRequest.created_at.desc()).limit(50).all()

        pending_approvals = []
        for req in pending_reqs:
            if req.source_type == "purchase" and req.po_id:
                po = PurchaseOrder.query.get(req.po_id)
                if po and po.status == "draft":
                    pending_approvals.append({
                        "req_id":      req.id,
                        "req_number":  req.request_number,
                        "product":     req.product.name,
                        "sku":         req.product.sku,
                        "quantity":    req.quantity,
                        "unit":        req.product.unit_of_measure or "pcs",
                        "type":        "purchase",
                        "po_id":       po.id,
                        "po_number":   po.order_number,
                        "vendor":      po.vendor.name if po.vendor else "—",
                        "amount":      po.total_amount,
                        "created_at":  req.created_at.strftime("%d %b, %H:%M"),
                        "notes":       req.notes or "",
                        "warehouse":   req.warehouse or "Main",
                        "location":    req.location or "Default",
                    })
            elif req.source_type == "transfer" and req.stock_transfer_id:
                st = req.stock_transfer
                if st and st.status == "pending":
                    pending_approvals.append({
                        "req_id":      req.id,
                        "req_number":  req.request_number,
                        "product":     req.product.name,
                        "sku":         req.product.sku,
                        "quantity":    req.quantity,
                        "unit":        req.product.unit_of_measure or "pcs",
                        "type":        "transfer",
                        "po_id":       None,
                        "po_number":   st.transfer_number,
                        "vendor":      f"Transfer from {st.from_warehouse} ({st.from_location}) to {st.to_warehouse} ({st.to_location})",
                        "amount":      0.0,
                        "created_at":  req.created_at.strftime("%d %b, %H:%M"),
                        "notes":       req.notes or "",
                        "warehouse":   st.to_warehouse,
                        "location":    st.to_location,
                    })

        # Recent activity log (last 30 requests)
        recent_requests = ProcurementRequest.query.order_by(
            ProcurementRequest.created_at.desc()
        ).limit(30).all()

        return {
            "analyzed":          analyzed,
            "action_items":      action_items,
            "critical_items":    critical_items,
            "low_stock_items":   low_stock_items,
            "reorder_items":     reorder_items,
            "predicted_stockouts": predicted,
            "pending_approvals": pending_approvals,
            "recent_requests":   recent_requests,
            "kpi": {
                "critical":          len(critical_items),
                "low_stock":         len(low_stock_items),
                "predicted_stockouts": len(predicted),
                "pending_pos":       len(pending_approvals),
                "auto_today":        auto_today,
                "total_monitored":   len(analyzed),
            },
            "top_priority": action_items[:5],
            "timestamp":    _now().strftime("%H:%M:%S"),
        }

    # ── AI Advisor (rule-based) ───────────────────────────────────────────────

    def generate_ai_advice(self, stats: dict) -> dict:
        """
        Produce structured natural-language procurement advice purely from
        the analyzed data — no external API needed.
        """
        critical  = stats["critical_items"]
        low       = stats["low_stock_items"]
        predicted = stats["predicted_stockouts"]
        pending   = stats["pending_approvals"]

        recommendations = []

        # Immediate buys for critical items
        for item in critical[:5]:
            vendor_name = item["vendor"]["name"] if item["vendor"] else "any available vendor"
            recommendations.append({
                "rank":     len(recommendations) + 1,
                "product":  item["name"],
                "shortage": item["shortage"],
                "unit":     item["unit"],
                "vendor":   vendor_name,
                "urgency":  "CRITICAL",
                "reason":   (
                    f"Free stock is {item['free']} {item['unit']} against "
                    f"reorder level of {item['reorder_level']} {item['unit']}. "
                    f"Immediate purchase required to prevent production stoppage."
                ),
            })

        # Predicted stockouts
        for item in predicted[:3]:
            if item["tier"] == TIER_OK:   # skip already shown
                vendor_name = item["vendor"]["name"] if item["vendor"] else "any vendor"
                recommendations.append({
                    "rank":     len(recommendations) + 1,
                    "product":  item["name"],
                    "shortage": item["recommended_qty"],
                    "unit":     item["unit"],
                    "vendor":   vendor_name,
                    "urgency":  "PREDICTED",
                    "reason":   (
                        f"At current consumption rate of {item['avg_daily']} "
                        f"{item['unit']}/day, stock will run out around "
                        f"{item['stockout_date']}. Order now to cover lead time "
                        f"of {item['lead_days']} days."
                    ),
                })

        # Low stock items
        for item in low[:3]:
            vendor_name = item["vendor"]["name"] if item["vendor"] else "any vendor"
            recommendations.append({
                "rank":     len(recommendations) + 1,
                "product":  item["name"],
                "shortage": item["shortage"],
                "unit":     item["unit"],
                "vendor":   vendor_name,
                "urgency":  "WARNING",
                "reason":   (
                    f"Stock of {item['free']} {item['unit']} is below safety "
                    f"buffer of {item['safety_stock']} {item['unit']}."
                ),
            })

        # Summary sentence
        if not recommendations:
            summary = "All inventory levels are healthy. No purchases recommended at this time."
            what_today = "Nothing urgent. Consider reviewing reorder levels if you expect increased demand."
        else:
            critical_count = len([r for r in recommendations if r["urgency"] == "CRITICAL"])
            summary = (
                f"Immediate action required for {critical_count} critical item(s). "
                f"{len(recommendations)} total purchase(s) recommended."
            )
            top = recommendations[0]
            what_today = (
                f"Priority purchase: {top['product']} — "
                f"{top['shortage']} {top['unit']} from {top['vendor']}. {top['reason']}"
            )

        which_week = []
        for item in predicted[:5]:
            which_week.append(
                f"{item['name']} (stockout ~{item['stockout_date']})"
            )

        return {
            "recommendations": recommendations,
            "summary":         summary,
            "what_today":      what_today,
            "which_this_week": which_week,
            "pending_count":   len(pending),
            "generated_at":    _now().strftime("%d %b %Y, %H:%M"),
        }
