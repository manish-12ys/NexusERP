from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.pos_session import PosSession
from app.models.pos_order import PosOrder
from app.models.pos_order_line import PosOrderLine
from app.models.product import Product
from app.models.customer import Customer
from datetime import datetime
from app.utils.decorators import permission_required

pos_bp = Blueprint("pos", __name__, template_folder="../templates/pos")


@pos_bp.route("/")
@login_required
@permission_required("view_pos")
def terminal():
    session = PosSession.query.filter_by(
        user_id=current_user.id, status="open"
    ).first()
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
    existing = PosSession.query.filter_by(
        user_id=current_user.id, status="open"
    ).first()
    if existing:
        flash("You already have an open session.", "warning")
        return redirect(url_for("pos.terminal"))
    session = PosSession(
        session_number=f"POS-{PosSession.query.count() + 1:05d}",
        user_id=current_user.id,
        opening_balance=request.form.get("opening_balance", 0, type=float),
    )
    db.session.add(session)
    db.session.commit()
    flash("POS session opened.", "success")
    return redirect(url_for("pos.terminal"))


@pos_bp.route("/session/close", methods=["POST"])
@login_required
@permission_required("create_pos")
def close_session():
    session = PosSession.query.filter_by(
        user_id=current_user.id, status="open"
    ).first()
    if not session:
        flash("No open session found.", "danger")
        return redirect(url_for("pos.terminal"))
    session.status = "closed"
    session.closed_at = datetime.utcnow()
    session.closing_balance = request.form.get("closing_balance", 0, type=float)
    db.session.commit()
    flash("POS session closed.", "success")
    return redirect(url_for("pos.terminal"))


@pos_bp.route("/sessions")
@login_required
@permission_required("view_pos")
def sessions():
    sessions = PosSession.query.order_by(PosSession.opened_at.desc()).all()
    return render_template("pos/sessions.html", sessions=sessions)


@pos_bp.route("/checkout", methods=["POST"])
@login_required
@permission_required("create_pos")
def checkout():
    from app.services.inventory.stock_service import StockService

    session = PosSession.query.filter_by(
        user_id=current_user.id, status="open"
    ).first()
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

    # Validate stock before creating the order
    for pid, qty in zip(product_ids, quantities):
        product = Product.query.get(int(pid))
        qty = float(qty)
        if not product or not product.inventory or product.inventory.free_to_use_qty < qty:
            flash(
                f"Insufficient stock for {product.name if product else 'unknown product'}. Please check inventory or create a procurement request.",
                "danger",
            )
            return redirect(url_for("pos.terminal"))

    order = PosOrder(
        order_number=f"POS-ORD-{PosOrder.query.count() + 1:05d}",
        session_id=session.id,
        customer_id=customer_id,
        payment_method=payment_method,
    )
    db.session.add(order)
    db.session.flush()
    subtotal = 0
    total_tax = 0
    for pid, qty in zip(product_ids, quantities):
        product = Product.query.get(int(pid))
        qty = float(qty)
        line_total = qty * product.sales_price
        line_tax = line_total * product.tax_percent / 100
        line = PosOrderLine(
            pos_order_id=order.id,
            product_id=product.id,
            quantity=qty,
            unit_price=product.sales_price,
            tax_percent=product.tax_percent,
            line_total=line_total,
        )
        db.session.add(line)
        subtotal += line_total
        total_tax += line_tax

    order.subtotal = subtotal
    order.tax_amount = total_tax
    order.total_amount = subtotal + total_tax
    session.total_sales += order.total_amount

    for pid, qty in zip(product_ids, quantities):
        success, result = StockService.consume_stock(int(pid), float(qty), user_id=current_user.id)
        if not success:
            db.session.rollback()
            flash(result, "danger")
            return redirect(url_for("pos.terminal"))

    db.session.commit()
    return redirect(url_for("pos.receipt", id=order.id))


@pos_bp.route("/receipt/<int:id>")
@login_required
@permission_required("view_pos")
def receipt(id):
    order = PosOrder.query.get_or_404(id)
    return render_template("pos/receipt.html", order=order)
