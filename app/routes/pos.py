from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.services.pos.pos_service import PosService
from app.models.product import Product
from app.models.customer import Customer
from app.utils.decorators import permission_required

pos_bp = Blueprint("pos", __name__, template_folder="../templates/pos")
pos_service = PosService()


@pos_bp.route("/")
@login_required
@permission_required("view_pos")
def terminal():
    session = pos_service.get_open_session(current_user.id)
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    customers = Customer.query.order_by(Customer.name).all()
    return render_template(
        "pos/terminal.html",
        session=session,
        products=products,
        customers=customers,
    )


@pos_bp.route("/session/open", methods=["POST"])
@login_required
@permission_required("create_pos")
def open_session():
    existing = pos_service.get_open_session(current_user.id)
    if existing:
        flash("You already have an open session.", "warning")
        return redirect(url_for("pos.terminal"))
    opening_balance = request.form.get("opening_balance", 0, type=float)
    pos_service.open_session(current_user.id, opening_balance)
    flash("POS session opened.", "success")
    return redirect(url_for("pos.terminal"))


@pos_bp.route("/session/close", methods=["POST"])
@login_required
@permission_required("create_pos")
def close_session():
    session = pos_service.get_open_session(current_user.id)
    if not session:
        flash("No open session found.", "danger")
        return redirect(url_for("pos.terminal"))
    closing_balance = request.form.get("closing_balance", 0, type=float)
    pos_service.close_session(session.id, closing_balance)
    flash("POS session closed.", "success")
    return redirect(url_for("pos.terminal"))


@pos_bp.route("/sessions")
@login_required
@permission_required("view_pos")
def sessions():
    sessions = pos_service.list_sessions()
    return render_template("pos/sessions.html", sessions=sessions)


@pos_bp.route("/checkout", methods=["POST"])
@login_required
@permission_required("create_pos")
def checkout():
    session = pos_service.get_open_session(current_user.id)
    if not session:
        flash("No open session.", "danger")
        return redirect(url_for("pos.terminal"))

    customer_id = request.form.get("customer_id", type=int)
    payment_method = request.form.get("payment_method", "cash")
    product_ids = request.form.getlist("product_id[]")
    quantities = request.form.getlist("quantity[]")

    if not product_ids:
        flash("No items in cart.", "warning")
        return redirect(url_for("pos.terminal"))

    items = []
    for pid, qty in zip(product_ids, quantities):
        try:
            quantity = float(qty)
        except ValueError:
            quantity = 0
        if quantity <= 0:
            flash("Please add a positive quantity for each item.", "danger")
            return redirect(url_for("pos.terminal"))
        product = Product.query.get(int(pid))
        if not product:
            flash("One of the selected products could not be found.", "danger")
            return redirect(url_for("pos.terminal"))
        items.append({"product_id": product.id, "quantity": quantity})

    order, error = pos_service.create_order(
        session.id,
        items,
        current_user.id,
        customer_id=customer_id,
        payment_method=payment_method,
    )

    if not order:
        flash(error, "danger")
        return redirect(url_for("pos.terminal"))

    return redirect(url_for("pos.receipt", id=order.id))


@pos_bp.route("/receipt/<int:id>")
@login_required
@permission_required("view_pos")
def receipt(id):
    order = pos_service.get_order(id)
    return render_template("pos/receipt.html", order=order)
