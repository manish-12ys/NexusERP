from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sales_order import SalesOrder
from app.models.sales_order_line import SalesOrderLine
from app.models.customer import Customer
from app.models.product import Product
from app.models.inventory import Inventory
from app.forms.sales_forms import SalesOrderForm, SalesOrderLineForm
from app.services.sales.sales_service import SalesService
from app.services.inventory.stock_service import StockService
from app.utils.decorators import permission_required

sales_bp = Blueprint("sales", __name__, template_folder="../templates/sales")
@sales_bp.route("/")
@login_required
@permission_required("view_sales")
def list_orders():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str)
    status_filter = request.args.get("status", "", type=str)

    query = SalesOrder.query.join(Customer)
    if search:
        query = query.filter(
            SalesOrder.order_number.ilike(f"%{search}%") |
            Customer.name.ilike(f"%{search}%")
        )
    if status_filter:
        query = query.filter(SalesOrder.status == status_filter)

    orders = query.order_by(SalesOrder.created_at.desc()).paginate(
        page=page, per_page=20
    )

    # Compute KPI totals
    total_sales_val = db.session.query(db.func.sum(SalesOrder.total_amount))\
        .filter(SalesOrder.status.in_(["confirmed", "delivered", "closed"])).scalar() or 0.0
    open_orders_cnt = SalesOrder.query.filter(SalesOrder.status.in_(["draft", "confirmed"])).count()
    completed_orders_cnt = SalesOrder.query.filter(SalesOrder.status.in_(["delivered", "closed"])).count()

    return render_template(
        "sales/orders.html",
        orders=orders,
        search=search,
        status_filter=status_filter,
        total_sales_val=total_sales_val,
        open_orders_cnt=open_orders_cnt,
        completed_orders_cnt=completed_orders_cnt
    )


@sales_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("create_sales")
def create_order():
    form = SalesOrderForm()
    form.customer_id.choices = [
        (c.id, f"{c.name} ({c.city or 'N/A'})")
        for c in Customer.query.order_by(Customer.name).all()
    ]
    if form.validate_on_submit():
        sales_service = SalesService()
        order, err = sales_service.create_order(
            customer_id=form.customer_id.data,
            user_id=current_user.id,
            expected_date=form.expected_date.data,
            notes=form.notes.data,
        )
        if err:
            flash(err, "danger")
        else:
            flash(f"Sales Order {order.order_number} created.", "success")
            return redirect(url_for("sales.edit_order", id=order.id))
    return render_template("sales/create_order.html", form=form)


@sales_bp.route("/<int:id>")
@login_required
@permission_required("view_sales")
def view_order(id):
    order = SalesOrder.query.get_or_404(id)
    from app.services.risk_service import RiskService
    risk_service = RiskService()
    risk_info = risk_service.evaluate_order_risk(order.id)
    return render_template("sales/view_order.html", order=order, risk_info=risk_info)


@sales_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("create_sales")
def edit_order(id):
    order = SalesOrder.query.get_or_404(id)
    form = SalesOrderForm(obj=order)
    form.customer_id.choices = [
        (c.id, f"{c.name} ({c.city or 'N/A'})")
        for c in Customer.query.order_by(Customer.name).all()
    ]
    if form.validate_on_submit():
        order.customer_id = form.customer_id.data
        order.expected_date = form.expected_date.data
        order.notes = form.notes.data
        db.session.commit()
        flash("Order updated.", "success")
        return redirect(url_for("sales.view_order", id=order.id))
    products = Product.query.filter_by(is_active=True).all()
    return render_template("sales/edit_order.html", form=form, order=order, products=products)


@sales_bp.route("/<int:id>/add-line", methods=["POST"])
@login_required
@permission_required("create_sales")
def add_line(id):
    order = SalesOrder.query.get_or_404(id)
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", 1, type=float)
    product = Product.query.get_or_404(product_id)
    line = SalesOrderLine(
        sales_order_id=order.id,
        product_id=product_id,
        quantity=quantity,
        unit_price=product.sales_price,
        tax_percent=product.tax_percent,
        line_total=quantity * product.sales_price,
    )
    db.session.add(line)
    order.subtotal = sum(l.line_total for l in order.lines)
    order.tax_amount = sum(l.line_total * l.tax_percent / 100 for l in order.lines)
    order.total_amount = order.subtotal + order.tax_amount - order.discount_amount
    db.session.commit()
    flash("Line added.", "success")
    return redirect(url_for("sales.edit_order", id=order.id))


@sales_bp.route("/<int:id>/confirm", methods=["POST"])
@login_required
@permission_required("confirm_sales")
def confirm_order(id):
    sales_service = SalesService()
    order, err = sales_service.confirm_order(id, user_id=current_user.id)
    if err:
        flash(err, "danger")
    else:
        flash(f"Order {order.order_number} confirmed.", "success")
    return redirect(url_for("sales.view_order", id=id))


@sales_bp.route("/<int:id>/deliver", methods=["POST"])
@login_required
@permission_required("deliver_sales")
def deliver_order(id):
    from app.services.sales.delivery_service import DeliveryService
    delivery_service = DeliveryService()
    order, err = delivery_service.deliver_order(id, user_id=current_user.id)
    if err:
        flash(err, "danger")
    else:
        flash(f"Order {order.order_number} delivered.", "success")
    return redirect(url_for("sales.view_order", id=id))
