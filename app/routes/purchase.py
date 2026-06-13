from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.vendor import Vendor
from app.models.product import Product
from app.forms.purchase_forms import PurchaseOrderForm
from app.services.purchase.purchase_service import PurchaseService
from app.utils.decorators import permission_required

purchase_bp = Blueprint("purchase", __name__, template_folder="../templates/purchase")


@purchase_bp.route("/")
@login_required
@permission_required("view_purchases")
def list_orders():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str)
    status_filter = request.args.get("status", "", type=str)

    query = PurchaseOrder.query.join(Vendor)
    if search:
        query = query.filter(
            PurchaseOrder.order_number.ilike(f"%{search}%") |
            Vendor.name.ilike(f"%{search}%")
        )
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)

    orders = query.order_by(PurchaseOrder.created_at.desc()).paginate(
        page=page, per_page=20
    )

    # Compute KPI totals
    total_purchase_val = db.session.query(db.func.sum(PurchaseOrder.total_amount))\
        .filter(PurchaseOrder.status.in_(["confirmed", "received", "closed"])).scalar() or 0.0
    open_orders_cnt = PurchaseOrder.query.filter(PurchaseOrder.status.in_(["draft", "confirmed"])).count()
    completed_orders_cnt = PurchaseOrder.query.filter(PurchaseOrder.status.in_(["received", "closed"])).count()

    return render_template(
        "purchase/orders.html",
        orders=orders,
        search=search,
        status_filter=status_filter,
        total_purchase_val=total_purchase_val,
        open_orders_cnt=open_orders_cnt,
        completed_orders_cnt=completed_orders_cnt
    )


@purchase_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("create_purchases")
def create_order():
    form = PurchaseOrderForm()
    form.vendor_id.choices = [
        (v.id, f"{v.name} ({v.city or 'N/A'})")
        for v in Vendor.query.order_by(Vendor.name).all()
    ]
    if form.validate_on_submit():
        purchase_service = PurchaseService()
        order, err = purchase_service.create_order(
            vendor_id=form.vendor_id.data,
            user_id=current_user.id,
            expected_date=form.expected_date.data,
            notes=form.notes.data,
        )
        if err:
            flash(err, "danger")
        else:
            flash(f"Purchase Order {order.order_number} created.", "success")
            return redirect(url_for("purchase.edit_order", id=order.id))
    return render_template("purchase/create_order.html", form=form)


@purchase_bp.route("/<int:id>")
@login_required
@permission_required("view_purchases")
def view_order(id):
    order = PurchaseOrder.query.get_or_404(id)
    return render_template("purchase/view_order.html", order=order)


@purchase_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("create_purchases")
def edit_order(id):
    order = PurchaseOrder.query.get_or_404(id)
    form = PurchaseOrderForm(obj=order)
    form.vendor_id.choices = [
        (v.id, f"{v.name} ({v.city or 'N/A'})")
        for v in Vendor.query.order_by(Vendor.name).all()
    ]
    if form.validate_on_submit():
        order.vendor_id = form.vendor_id.data
        order.expected_date = form.expected_date.data
        order.notes = form.notes.data
        db.session.commit()
        flash("Order updated.", "success")
        return redirect(url_for("purchase.view_order", id=order.id))
    products = Product.query.filter_by(is_active=True).all()
    return render_template("purchase/edit_order.html", form=form, order=order, products=products)


@purchase_bp.route("/<int:id>/add-line", methods=["POST"])
@login_required
@permission_required("create_purchases")
def add_line(id):
    order = PurchaseOrder.query.get_or_404(id)
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", 1, type=float)
    unit_cost = request.form.get("unit_cost", 0, type=float)
    product = Product.query.get_or_404(product_id)
    line = PurchaseOrderLine(
        purchase_order_id=order.id,
        product_id=product_id,
        quantity=quantity,
        unit_cost=unit_cost or product.cost_price,
        line_total=(unit_cost or product.cost_price) * quantity,
    )
    db.session.add(line)
    lines = order.lines.all()
    order.subtotal = sum(l.line_total for l in lines)
    order.tax_amount = sum(l.line_total * l.tax_percent / 100 for l in lines)
    order.total_amount = order.subtotal + order.tax_amount
    db.session.commit()
    flash("Line added.", "success")
    return redirect(url_for("purchase.edit_order", id=order.id))


@purchase_bp.route("/<int:id>/confirm", methods=["POST"])
@login_required
@permission_required("confirm_purchases")
def confirm_order(id):
    purchase_service = PurchaseService()
    order, err = purchase_service.confirm_order(id)
    if err:
        flash(err, "danger")
    else:
        flash(f"Order {order.order_number} confirmed.", "success")
    return redirect(url_for("purchase.view_order", id=id))


@purchase_bp.route("/<int:id>/receive", methods=["GET", "POST"])
@login_required
@permission_required("receive_purchases")
def receive_order(id):
    order = PurchaseOrder.query.get_or_404(id)
    if request.method == "POST":
        from app.services.purchase.receiving_service import ReceivingService
        receiving_service = ReceivingService()
        order, err = receiving_service.receive_order(id, current_user.id)
        if err:
            flash(err, "danger")
        else:
            flash(f"Order {order.order_number} received.", "success")
        return redirect(url_for("purchase.view_order", id=order.id))
    return render_template("purchase/receive.html", order=order)
