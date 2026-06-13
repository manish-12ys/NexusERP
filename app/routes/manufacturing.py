from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.manufacturing_order import ManufacturingOrder
from app.models.product import Product
from app.models.bom import Bom
from app.forms.manufacturing_forms import ManufacturingOrderForm
from app.services.manufacturing.manufacturing_service import ManufacturingService
from app.utils.decorators import permission_required

manufacturing_bp = Blueprint(
    "manufacturing", __name__, template_folder="../templates/manufacturing"
)


@manufacturing_bp.route("/")
@login_required
@permission_required("view_manufacturing")
def list_mos():
    page = request.args.get("page", 1, type=int)
    mos = ManufacturingOrder.query.order_by(
        ManufacturingOrder.created_at.desc()
    ).paginate(page=page, per_page=20)
    return render_template("manufacturing/mo_list.html", mos=mos)


@manufacturing_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("create_manufacturing")
def create_mo():
    form = ManufacturingOrderForm()
    form.product_id.choices = [
        (p.id, f"{p.name} ({p.sku})")
        for p in Product.query.filter_by(is_active=True, product_type="finished_goods")
        .order_by(Product.name)
        .all()
    ]
    if form.validate_on_submit():
        bom = Bom.query.filter_by(
            product_id=form.product_id.data, is_active=True
        ).first()
        mo = ManufacturingOrder(
            mo_number=f"MO-{ManufacturingOrder.query.count() + 1:05d}",
            product_id=form.product_id.data,
            bom_id=bom.id if bom else None,
            quantity=form.quantity.data,
            notes=form.notes.data,
        )
        db.session.add(mo)
        db.session.commit()
        flash(f"Manufacturing Order {mo.mo_number} created.", "success")
        return redirect(url_for("manufacturing.view_mo", id=mo.id))
    return render_template("manufacturing/create_mo.html", form=form)


@manufacturing_bp.route("/<int:id>")
@login_required
@permission_required("view_manufacturing")
def view_mo(id):
    mo = ManufacturingOrder.query.get_or_404(id)
    return render_template("manufacturing/view_mo.html", mo=mo)


@manufacturing_bp.route("/<int:id>/start", methods=["POST"])
@login_required
@permission_required("create_manufacturing")
def start_mo(id):
    mo = ManufacturingOrder.query.get_or_404(id)
    manufacturing_service = ManufacturingService()
    manufacturing_service.start_mo(mo.id)
    flash(f"MO {mo.mo_number} started.", "success")
    return redirect(url_for("manufacturing.view_mo", id=mo.id))


@manufacturing_bp.route("/<int:id>/confirm", methods=["POST"])
@login_required
@permission_required("create_manufacturing")
def confirm_mo(id):
    mo = ManufacturingOrder.query.get_or_404(id)
    manufacturing_service = ManufacturingService()
    manufacturing_service.confirm_mo(mo.id)
    flash(f"MO {mo.mo_number} confirmed.", "success")
    return redirect(url_for("manufacturing.view_mo", id=mo.id))


@manufacturing_bp.route("/<int:id>/complete", methods=["POST"])
@login_required
@permission_required("create_manufacturing")
def complete_mo(id):
    mo = ManufacturingOrder.query.get_or_404(id)
    mo.status = "completed"
    mo.produced_qty = mo.quantity
    from datetime import datetime
    mo.end_date = datetime.utcnow()
    from app.services.manufacturing.production_service import ProductionService
    production_service = ProductionService()
    production_service.finish_production(mo.id, current_user.id)
    flash(f"MO {mo.mo_number} completed.", "success")
    return redirect(url_for("manufacturing.view_mo", id=mo.id))
