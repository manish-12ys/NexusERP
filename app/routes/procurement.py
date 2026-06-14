"""
routes/procurement.py
Smart Procurement Autopilot — Flask routes.

Endpoints
---------
GET  /              → Command Center dashboard
GET  /analyze       → JSON live-refresh payload (AJAX polling)
POST /mode          → Switch autopilot mode (stored in session)
POST /run           → Trigger one engine run
POST /approve/<id>  → Approve a draft PO (semi-auto workflow)
POST /dismiss/<id>  → Close a procurement request without action
GET  /rules/create  → (unchanged)
POST /rules/create  → (unchanged)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models.procurement_rule import ProcurementRule
from app.models.procurement_request import ProcurementRequest
from app.models.stock_transfer import StockTransfer
from app.models.purchase_order import PurchaseOrder
from app.models.product import Product
from app.models.vendor import Vendor
from app.forms.bom_forms import ProcurementRuleForm
from app.utils.decorators import permission_required

procurement_bp = Blueprint(
    "procurement", __name__, template_folder="../templates/procurement"
)

VALID_MODES = ("manual", "semi", "auto")


def _get_mode() -> str:
    return session.get("autopilot_mode", "semi")


# ──────────────────────────────────────────────────────────────────────────────
# Command Center Dashboard
# ──────────────────────────────────────────────────────────────────────────────
@procurement_bp.route("/")
@login_required
@permission_required("run_procurement")
def dashboard():
    from app.services.procurement.autopilot_service import AutopilotService
    svc   = AutopilotService()
    stats = svc.get_command_center_stats()
    ai    = svc.generate_ai_advice(stats)
    mode  = _get_mode()
    return render_template(
        "procurement/command_center.html",
        stats=stats,
        ai=ai,
        mode=mode,
    )


# ──────────────────────────────────────────────────────────────────────────────
# JSON live-refresh (AJAX polling every 30 s)
# ──────────────────────────────────────────────────────────────────────────────
@procurement_bp.route("/analyze")
@login_required
@permission_required("run_procurement")
def analyze():
    from app.services.procurement.autopilot_service import AutopilotService
    svc   = AutopilotService()
    stats = svc.get_command_center_stats()
    return jsonify({
        "kpi":         stats["kpi"],
        "action_items": stats["action_items"],
        "timestamp":   stats["timestamp"],
        "mode":        _get_mode(),
    })


# ──────────────────────────────────────────────────────────────────────────────
# Switch autopilot mode
# ──────────────────────────────────────────────────────────────────────────────
@procurement_bp.route("/mode", methods=["POST"])
@login_required
@permission_required("run_procurement")
def set_mode():
    new_mode = request.form.get("mode", "semi")
    if new_mode not in VALID_MODES:
        flash("Invalid mode.", "danger")
    else:
        session["autopilot_mode"] = new_mode
        labels = {"manual": "Manual", "semi": "Semi-Automatic", "auto": "Fully Automatic"}
        flash(f"Autopilot mode set to: {labels[new_mode]}.", "success")
    return redirect(url_for("procurement.dashboard"))


# ──────────────────────────────────────────────────────────────────────────────
# Run engine
# ──────────────────────────────────────────────────────────────────────────────
@procurement_bp.route("/run", methods=["POST"])
@login_required
@permission_required("run_procurement")
def run_procurement():
    from app.services.procurement.procurement_engine import ProcurementEngine
    mode   = _get_mode()
    engine = ProcurementEngine()
    counts = engine.run(mode=mode)
    mode_labels = {"manual": "Manual", "semi": "Semi-Automatic", "auto": "Fully Automatic"}
    flash(
        f"Autopilot run complete ({mode_labels.get(mode, mode)} mode). "
        f"{counts['requests_created']} request(s) created — "
        f"{counts['pos_created']} PO(s), {counts['mos_created']} MO(s). "
        f"{counts['skipped_existing']} already had open requests.",
        "success",
    )
    return redirect(url_for("procurement.dashboard"))


# ──────────────────────────────────────────────────────────────────────────────
# Approve a draft PO or suggested Stock Transfer (semi-auto workflow)
# ──────────────────────────────────────────────────────────────────────────────
@procurement_bp.route("/approve/<int:req_id>", methods=["POST"])
@login_required
@permission_required("run_procurement")
def approve_request(req_id):
    req = ProcurementRequest.query.get_or_404(req_id)
    if req.po_id:
        po = PurchaseOrder.query.get(req.po_id)
        if po and po.status == "draft":
            po.status  = "confirmed"
            po.user_id = current_user.id
            flash(f"Purchase Order {po.order_number} approved and confirmed.", "success")
        else:
            flash("PO is not in draft state or not found.", "warning")
    elif req.stock_transfer_id:
        from app.services.inventory.transfer_service import TransferService
        success, err = TransferService.execute_transfer(req.stock_transfer_id, user_id=current_user.id)
        if success:
            req.status = "closed"
            from datetime import datetime, timezone
            req.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            flash(f"Warehouse transfer {req.stock_transfer.transfer_number} approved and executed successfully.", "success")
        else:
            flash(f"Failed to execute transfer: {err}", "danger")
    else:
        flash("No PO or Stock Transfer linked to this request.", "warning")
    db.session.commit()
    return redirect(url_for("procurement.dashboard"))


# ──────────────────────────────────────────────────────────────────────────────
# Dismiss a procurement request
# ──────────────────────────────────────────────────────────────────────────────
@procurement_bp.route("/dismiss/<int:req_id>", methods=["POST"])
@login_required
@permission_required("run_procurement")
def dismiss_request(req_id):
    from datetime import datetime, timezone
    req = ProcurementRequest.query.get_or_404(req_id)
    req.status    = "closed"
    req.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    req.notes     = (req.notes or "") + " [Dismissed by manager]"
    # Also cancel linked draft PO if it exists
    if req.po_id:
        po = PurchaseOrder.query.get(req.po_id)
        if po and po.status == "draft":
            po.status = "cancelled"
    elif req.stock_transfer_id:
        from app.services.inventory.transfer_service import TransferService
        TransferService.cancel_transfer(req.stock_transfer_id, user_id=current_user.id)
    db.session.commit()
    flash("Procurement request dismissed.", "info")
    return redirect(url_for("procurement.dashboard"))


# ──────────────────────────────────────────────────────────────────────────────
# Sourcing Rule CRUD (unchanged)
# ──────────────────────────────────────────────────────────────────────────────
@procurement_bp.route("/rules/create", methods=["GET", "POST"])
@login_required
@permission_required("run_procurement")
def create_rule():
    form = ProcurementRuleForm()
    form.product_id.choices = [
        (p.id, f"{p.name} ({p.sku})")
        for p in Product.query.filter_by(is_active=True).order_by(Product.name).all()
    ]
    form.vendor_id.choices = [(0, "-- No Preferred Supplier (Optional) --")] + [
        (v.id, v.name) for v in Vendor.query.order_by(Vendor.name).all()
    ]
    if form.validate_on_submit():
        vendor_id = form.vendor_id.data or None
        if vendor_id == 0:
            vendor_id = None
        rule = ProcurementRule(
            product_id=form.product_id.data,
            procurement_type=form.procurement_type.data,
            source_type=form.source_type.data,
            vendor_id=vendor_id,
            lead_time_days=form.lead_time_days.data,
            min_order_qty=form.min_order_qty.data,
            max_order_qty=form.max_order_qty.data,
            multiple_qty=form.multiple_qty.data,
        )
        db.session.add(rule)
        db.session.commit()
        flash("Procurement rule created.", "success")
        return redirect(url_for("procurement.dashboard"))
    return render_template("procurement/create_rule.html", form=form)
